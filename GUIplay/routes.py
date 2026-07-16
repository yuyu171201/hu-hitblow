"""Flask ルーティング — Hit & Blow API エンドポイント。

game.py の HitBlowGame クラスを使ってゲームロジックを実行する。
routes.py 自体には判定・出題ロジックを持たない。

画面構成:
  /            … モード選択メニュー
  /solo        … 1人プレイ（PCが出題）
  /vs, /vs/... … 2人対戦（ネットワーク対戦。共有した1つの秘密を交代で解き合う）
"""

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
)

from hitblow.game import HitBlowGame

import vs_store

# game.py の play(digits=3) と同じデフォルト桁数
DIGITS = 3

bp = Blueprint("game", __name__)


# ══════════════════════════════════════════════════════════
# モード選択メニュー
# ══════════════════════════════════════════════════════════

@bp.route("/")
def menu():
    """トップ：1人プレイ / 対戦 を選ぶ入口。"""
    return render_template("menu.html")


# ══════════════════════════════════════════════════════════
# 1人プレイ（従来の / 相当。セッションキーは "game"）
# ══════════════════════════════════════════════════════════

def _get_game() -> HitBlowGame:
    """セッションから 1人プレイ用 HitBlowGame を取得（なければ新規作成）。"""
    if "game" not in session:
        game = HitBlowGame(digits=DIGITS)
        session["game"] = game.to_dict()
        return game
    return HitBlowGame.from_dict(session["game"])


def _save_game(game: HitBlowGame):
    """1人プレイのゲーム状態をセッションに保存。"""
    session["game"] = game.to_dict()


@bp.route("/solo")
def solo():
    """1人プレイ画面。初回アクセス時にゲームを初期化。"""
    _get_game()  # セッションになければ新規作成される
    return render_template(
        "index.html",
        mode="solo",
        subtitle="3 桁の数字を当てよう（重複なし）",
    )


@bp.route("/guess", methods=["POST"])
def guess():
    """ユーザーの予想を HitBlowGame.guess() で判定して JSON で返す。"""
    data = request.get_json()
    g = data.get("guess", "")

    game = _get_game()
    result = game.guess(g)
    _save_game(game)

    return jsonify(result)


@bp.route("/item", methods=["POST"])
def item():
    """アイテムを使用（HitBlowGame.use_item()）して結果を JSON で返す。"""
    data = request.get_json()
    kind = data.get("kind", "")

    game = _get_game()
    result = game.use_item(kind)
    _save_game(game)

    return jsonify(result)


@bp.route("/new_game", methods=["POST"])
def new_game():
    """新しい 1人プレイを開始。"""
    game = HitBlowGame(digits=DIGITS)
    _save_game(game)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════
# 2人対戦（ネットワーク対戦）
#
#   ・ロビーで名前を入れて 2 人揃うまで待機（自動マッチング）
#   ・2 人揃うと 1 つの秘密を生成して開始
#   ・手番 A→B→A→B。先制は先に登録したユーザー
#   ・ライフ・時間は使わない
#   ・アイテム（High/Low ヒント）は 1 ユーザー 1 回・自分にのみ表示
#   ・先に 3 HIT を出したユーザーが勝利
#
# 状態はサーバー側 vs_store に保持し、各クライアントは pid（sessionStorage）で
# 自分を識別してポーリングで手番を待つ。
# ══════════════════════════════════════════════════════════

@bp.route("/vs")
def vs_lobby():
    """対戦ロビー：ユーザー名を入力する画面。"""
    return render_template("vs_lobby.html")


@bp.route("/vs/join", methods=["POST"])
def vs_join():
    """名前で参加。待機中の部屋に入る（無ければ作る）。pid を返す。"""
    name = (request.get_json() or {}).get("name", "")
    pid, room_id, index = vs_store.join(name)
    return jsonify({"pid": pid, "room": room_id, "index": index})


@bp.route("/vs/play")
def vs_play():
    """対戦画面。状態はクライアントが /vs/state をポーリングして描画する。"""
    return render_template("vs_game.html")


@bp.route("/vs/state")
def vs_state():
    """pid の視点での現在状態を返す（ポーリング用）。"""
    pid = request.args.get("pid", "")
    return jsonify(vs_store.state(pid))


@bp.route("/vs/guess", methods=["POST"])
def vs_guess():
    """対戦の予想を判定して最新状態を返す。"""
    data = request.get_json() or {}
    pid = data.get("pid", "")
    g = (data.get("guess", "") or "").strip()
    return jsonify(vs_store.guess(pid, g))


@bp.route("/vs/item", methods=["POST"])
def vs_item():
    """アイテムを使用（シャッフル or High/Low ヒント）。1 ユーザー 1 回。"""
    data = request.get_json() or {}
    pid = data.get("pid", "")
    kind = data.get("kind", "highlow")
    return jsonify(vs_store.use_item(pid, kind))


@bp.route("/vs/leave", methods=["POST"])
def vs_leave():
    """退出通知（タブを閉じる/離脱）。残ったユーザーの不戦勝で終了させる。

    クライアントは navigator.sendBeacon で呼ぶため、JSON の解析失敗でも
    500 にせず silent=True で受ける。
    """
    data = request.get_json(silent=True) or {}
    pid = data.get("pid", "")
    return jsonify(vs_store.leave(pid))
