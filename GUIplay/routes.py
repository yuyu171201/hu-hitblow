"""Flask ルーティング — Hit & Blow API エンドポイント。

game.py の play() に対応する処理を Web 向けに再構成。
判定・出題は core.py をそのまま呼ぶ。
タイマーも game.py と同じ挙動（tries==1 で start = time.time()）。
"""

import time  # game.py と同様にサーバー側で所要時間を計測

from flask import Blueprint, render_template, request, jsonify, session

from hitblow.core import judge, make_secret

# game.py の play(digits=3) と同じデフォルト桁数
DIGITS = 3

bp = Blueprint("game", __name__)


@bp.route("/")
def index():
    """ゲーム画面を表示。

    game.py の play() 冒頭に対応:
      secret = make_secret(digits)
      tries = 0
    """
    if "secret" not in session:
        # --- core.make_secret(digits) で答えを生成 (game.py L15) ---
        session["secret"] = make_secret(DIGITS)
        session["tries"] = 0
        session["start_time"] = None  # game.py: start は tries==1 でセット
    return render_template("index.html")


@bp.route("/guess", methods=["POST"])
def guess():
    """ユーザーの予想を判定して JSON で返す。

    game.py の while ループ内のロジックをそのまま再現:
      1. バリデーション (game.py L32)
      2. タイマー開始   (game.py L29-30: if tries == 1: start = time.time())
      3. tries += 1     (game.py L35)
      4. judge()        (game.py L36: hit, blow = judge(secret, guess))
      5. 勝利判定       (game.py L38: if hit == digits)
      6. 所要時間       (game.py L40: end = time.time())
    """
    data = request.get_json()
    g = data.get("guess", "")

    # --- バリデーション: game.py L32 と同じ条件 ---
    # if len(guess) != digits or not guess.isdigit():
    if len(g) != DIGITS or not g.isdigit():
        return jsonify({"error": f"{DIGITS} 桁の数字で入力してね"})

    # 重複チェック（make_secret が重複なしなので GUI 側でも制約）
    if len(set(g)) != len(g):
        return jsonify({"error": "数字が重複しています"})

    secret = session.get("secret")
    if not secret:
        # セッション切れ時のフォールバック
        session["secret"] = make_secret(DIGITS)
        secret = session["secret"]
        session["tries"] = 0
        session["start_time"] = None

    # --- タイマー: game.py L29-30 ---
    # if tries == 1:
    #     start = time.time()
    if session.get("tries", 0) == 1:
        session["start_time"] = time.time()

    # --- tries += 1: game.py L35 ---
    session["tries"] = session.get("tries", 0) + 1

    # --- 判定: core.judge(secret, guess) → game.py L36 ---
    hit, blow = judge(secret, g)

    # --- 勝利判定: game.py L38 (if hit == digits) ---
    win = (hit == DIGITS)

    result = {
        "hit": hit,
        "blow": blow,
        "tries": session["tries"],
        "win": win,
    }

    if win:
        # --- 所要時間: game.py L40 (end = time.time()) ---
        end = time.time()
        start = session.get("start_time")
        if start is not None:
            elapsed = end - start
            result["elapsed"] = round(elapsed, 2)
        # game.py L43: 正解！ {tries} 回で当たり（答え {secret}）
        result["message"] = f"正解！ {session['tries']} 回で当たり（答え {secret}）"

    return jsonify(result)


@bp.route("/new_game", methods=["POST"])
def new_game():
    """新しいゲームを開始。game.py の play() 冒頭と同じ初期化。"""
    session["secret"] = make_secret(DIGITS)
    session["tries"] = 0
    session["start_time"] = None
    return jsonify({"ok": True})
