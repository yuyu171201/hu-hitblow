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
"""

import threading
import uuid
import time

from hitblow.core import judge, make_secret

DIGITS = 3

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
        return _public_state(room, idx, me)


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
        else:
            room["turn"] = 1 - idx    # 手番交代（A→B→A→B）

        return _public_state(room, idx, me)


def use_item(pid: str) -> dict:
    """High/Low ヒントを使う（1 ユーザー 1 回、自分にのみ表示）。手番は消費しない。"""
    with _lock:
        room, idx, me = _find(pid)
        if room is None:
            return {"error": "not_found"}
        if room["status"] != "playing":
            return {"error": "対戦はまだ始まっていません"}
        if me["item_used"]:
            return {"error": "アイテムは使用済みです"}

        me["hint"] = ["low" if int(d) <= 4 else "high" for d in room["secret"]]
        me["item_used"] = True
        return _public_state(room, idx, me)
