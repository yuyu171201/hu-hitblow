"""Hit & Blow GUI — Web アプリで遊べる GUI 版。

使い方:
    pip install flask
    python app.py

ブラウザで http://127.0.0.1:5000 を開いてプレイ。

元の game.py / core.py のロジックをそのまま再利用:
  - core.judge(secret, guess) → (hit, blow) の判定
  - core.make_secret(digits)  → 重複なし digits 桁の答え生成
  - game.py と同じタイマー挙動（tries==1 で開始）
"""

import sys
import os

# src/ を import パスに追加して既存の core.py を再利用
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from flask import Flask

from routes import bp, DIGITS


def create_app():
    """Flask アプリケーションファクトリ。"""
    application = Flask(__name__)
    application.secret_key = "hitblow-secret-key-2026"
    application.register_blueprint(bp)
    return application


# ──────────────────────────────────────────────
# エントリーポイント
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = create_app()
    # PORT 環境変数があればそれを使う（無ければ 5000）
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print(f"  Hit & Blow GUI（{DIGITS} 桁・重複なし）")  # game.py L16 と同じ表示
    print(f"  http://127.0.0.1:{port} でプレイ！")
    print("=" * 50)
    app.run(host="127.0.0.1", port=port, debug=True)
