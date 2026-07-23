"""対戦（ネットワーク）用の共有ゲーム状態ストア。

Flask セッション（＝ブラウザ Cookie 単位）ではなく、**サーバー側のインメモリ**に
部屋（room）を保持する。2人が同じ 1 つの秘密の数字を、手番を交代しながら解き合う。

- プレイヤー識別は `pid`（サーバー発行トークン）で行う。
  クライアントは sessionStorage に持ち、毎リクエストで送る（＝同一ブラウザの
  別タブでも別プレイヤーになれる）。
- 判定・出題は core.judge / core.make_secret を再利用する。

仕様:
  - 名前を入れて 2 人揃うまで待機（自動マッチング）
  - 2 人目が入った時点で 1 つの秘密を生成し開始
  - 手番 A→B→A→B。先制は先に登録したユーザー（players[0]）
  - ライフ・時間は使わない
  - アイテム（High/Low ヒント）は 1 ユーザー 1 回、自分にのみ表示
  - 先に 3 HIT（全桁一致）を出したユーザーが勝利
  - 片方のユーザーが退出（タブを閉じる/通信途絶）したら、残ったユーザーの
    不戦勝としてゲームを終了する
"""

import threading
import uuid
import time

from hitblow.core import judge, make_secret

DIGITS = 3

# ポーリングがこの秒数途絶えたプレイヤーは「退出した」とみなす。
# クライアントは 1 秒ごとに /vs/state を叩くので、通常はこれより十分短い。
# タブを閉じたときは beacon（/vs/leave）で即座に検知するため、この値は
# クラッシュ・通信断など beacon が飛ばなかった場合のフォールバック。
DISCONNECT_TIMEOUT = 6.0

_lock = threading.RLock()
_rooms: dict[str, dict] = {}     # room_id -> room
_waiting_room_id: str | None = None  # 相手待ちの部屋


# ── 内部ヘルパ ────────────────────────────────────────────

def _new_room() -> dict:
    rid = uuid.uuid4().hex[:8]
    room = {
        "id": rid,
        "digits": DIGITS,
        "secret": None,        # 2 人目参加時に生成
        "players": [],         # 参加順。players[0] が先制
        "turn": 0,             # 手番のインデックス
        "status": "waiting",   # waiting / playing / finished
        "winner": None,        # 勝者インデックス
        "win_reason": None,    # "solved"（3HIT）/ "opponent_left"（相手退出）
        "created": time.time(),
    }
    _rooms[rid] = room
    return room


def _find(pid: str):
    """pid から (room, index, player) を返す。無ければ (None, None, None)。"""
    for room in _rooms.values():
        for i, p in enumerate(room["players"]):
            if p["pid"] == pid:
                return room, i, p
    return None, None, None


def _finish_forfeit(room: dict, winner_idx: int):
    """相手退出による決着。winner_idx を残ったユーザーの不戦勝にする。"""
    room["status"] = "finished"
    room["winner"] = winner_idx
    room["win_reason"] = "opponent_left"


def _check_disconnect(room: dict):
    """対戦中に一定時間ポーリングが途絶えたプレイヤーがいれば、相手の勝ちにする。

    呼び出し側（生きているプレイヤー）は直前に last_seen を更新しているため、
    ここで古くなっているのは退出した側だけになる。
    """
    if room["status"] != "playing" or len(room["players"]) < 2:
        return
    now = time.time()
    for i, p in enumerate(room["players"]):
        if now - p["last_seen"] > DISCONNECT_TIMEOUT:
            _finish_forfeit(room, 1 - i)
            return


def _public_state(room: dict, my_idx: int, me: dict) -> dict:
    """リクエストしたプレイヤー視点の状態。

    ヒント（High/Low）は自分の分だけ含める（相手には見せない）。
    """
    players_public = [
        {"name": p["name"], "guesses": p["guesses"], "solved": p["solved"]}
        for p in room["players"]
    ]
    winner = room["winner"]
    return {
        "status": room["status"],
        "digits": room["digits"],
        "your_index": my_idx,
        "your_turn": room["status"] == "playing" and room["turn"] == my_idx,
        "turn": room["turn"],
        "players": players_public,
        "you": {
            "name": me["name"],
            "item_used": me["item_used"],
            "hint": me["hint"],          # 自分にのみ表示される High/Low
        },
        "winner": winner,
        "winner_name": room["players"][winner]["name"] if winner is not None else None,
        "win_reason": room["win_reason"],
        # 秘密は決着後のみ開示
        "secret": room["secret"] if room["status"] == "finished" else None,
    }


# ── 公開 API ──────────────────────────────────────────────

def join(name: str):
    """待機中の部屋に参加（無ければ新規作成）。(pid, room_id, index) を返す。"""
    global _waiting_room_id
    name = (name or "").strip() or "名無し"
    with _lock:
        room = _rooms.get(_waiting_room_id) if _waiting_room_id else None
        if room is None or room["status"] != "waiting" or len(room["players"]) >= 2:
            room = _new_room()
            _waiting_room_id = room["id"]

        pid = uuid.uuid4().hex
        room["players"].append({
            "pid": pid,
            "name": name,
            "item_used": False,
            "hint": None,
            "guesses": [],
            "solved": False,
            "last_seen": time.time(),   # 退出検知（DISCONNECT_TIMEOUT）用
        })
        index = len(room["players"]) - 1

        # 2 人揃ったら秘密を生成して開始
        if len(room["players"]) == 2:
            room["secret"] = make_secret(room["digits"])
            room["status"] = "playing"
            room["turn"] = 0          # 先制は先に登録したユーザー
            _waiting_room_id = None

        return pid, room["id"], index


def state(pid: str) -> dict:
    with _lock:
        room, idx, me = _find(pid)
        if room is None:
            return {"error": "not_found"}
        me["last_seen"] = time.time()   # 自分は生きている
        _check_disconnect(room)         # 相手が途絶えていれば決着させる
        return _public_state(room, idx, me)


def leave(pid: str) -> dict:
    """プレイヤーが退出（タブを閉じる等）したときに呼ぶ。

    対戦中なら残ったユーザーの不戦勝でゲームを終了する。
    相手が来る前（waiting）の退出なら部屋を破棄してマッチング枠を空ける。
    """
    global _waiting_room_id
    with _lock:
        room, idx, me = _find(pid)
        if room is None:
            return {"ok": True}
        if room["status"] == "playing":
            _finish_forfeit(room, 1 - idx)
        elif room["status"] == "waiting":
            # まだ相手がいない → 部屋を閉じ、待機枠から外す
            room["status"] = "finished"
            if _waiting_room_id == room["id"]:
                _waiting_room_id = None
        return {"ok": True}


def guess(pid: str, g: str) -> dict:
    """予想を判定。3 HIT なら勝利、外れなら手番を相手へ渡す。"""
    with _lock:
        room, idx, me = _find(pid)
        if room is None:
            return {"error": "not_found"}
        if room["status"] != "playing":
            return {"error": "対戦はまだ始まっていません"}
        if room["turn"] != idx:
            return {"error": "あなたの番ではありません"}

        me["last_seen"] = time.time()

        digits = room["digits"]
        if len(g) != digits or not g.isdigit() or len(set(g)) != len(g):
            return {"error": f"{digits} 桁・重複なしの数字で入力してね"}

        hit, blow = judge(room["secret"], g)
        me["guesses"].append({"guess": g, "hit": hit, "blow": blow})

        if hit == digits:
            # 先に 3 HIT を出した → 勝利
            me["solved"] = True
            room["status"] = "finished"
            room["winner"] = idx
            room["win_reason"] = "solved"
        else:
            room["turn"] = 1 - idx    # 手番交代（A→B→A→B）

        return _public_state(room, idx, me)


def use_item(pid: str, kind: str = "highlow") -> dict:
    """アイテムを使う（1 ユーザー 1 回）。手番は消費しない。

    kind:
      "shuffle" … 秘密の数字をリセット（両者の履歴もクリア）
      "highlow" … 各桁の大小ヒント（自分にのみ表示）
    """
    with _lock:
        room, idx, me = _find(pid)
        if room is None:
            return {"error": "not_found"}
        if room["status"] != "playing":
            return {"error": "対戦はまだ始まっていません"}
        if me["item_used"]:
            return {"error": "アイテムは使用済みです"}

        me["last_seen"] = time.time()
        me["item_used"] = True

        if kind == "shuffle":
            # 秘密の数字を再生成し、両プレイヤーの履歴をリセット
            room["secret"] = make_secret(room["digits"])
            for p in room["players"]:
                p["guesses"] = []
                p["hint"] = None        # ヒントも無効化（新しい秘密に対応しない）
            return _public_state(room, idx, me)

        # デフォルト: High/Low ヒント
        me["hint"] = ["low" if int(d) <= 4 else "high" for d in room["secret"]]
        return _public_state(room, idx, me)
