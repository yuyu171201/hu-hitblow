"""Flask ルーティング — Hit & Blow API エンドポイント。

game.py の HitBlowGame クラスを使ってゲームロジックを実行する。
routes.py 自体には判定・出題ロジックを持たない。
"""

from flask import Blueprint, render_template, request, jsonify, session

from hitblow.game import HitBlowGame

# game.py の play(digits=3) と同じデフォルト桁数
DIGITS = 3

bp = Blueprint("game", __name__)


def _get_game() -> HitBlowGame:
    """セッションから HitBlowGame を取得（なければ新規作成）。"""
    if "game" not in session:
        game = HitBlowGame(digits=DIGITS)
        session["game"] = game.to_dict()
        return game
    return HitBlowGame.from_dict(session["game"])


def _save_game(game: HitBlowGame):
    """ゲーム状態をセッションに保存。"""
    session["game"] = game.to_dict()


@bp.route("/")
def index():
    """ゲーム画面を表示。初回アクセス時にゲームを初期化。"""
    _get_game()  # セッションになければ新規作成される
    return render_template("index.html")


@bp.route("/guess", methods=["POST"])
def guess():
    """ユーザーの予想を HitBlowGame.guess() で判定して JSON で返す。"""
    data = request.get_json()
    g = data.get("guess", "")

    game = _get_game()
    result = game.guess(g)
    _save_game(game)

    return jsonify(result)


@bp.route("/new_game", methods=["POST"])
def new_game():
    """新しいゲームを開始。"""
    game = HitBlowGame(digits=DIGITS)
    _save_game(game)
    return jsonify({"ok": True})
