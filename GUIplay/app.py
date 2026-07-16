"""Hit & Blow GUI — Flask アプリケーションファクトリ。

このファイルは「アプリの組み立て」だけを担当する（＝create_app）。
サーバーの起動（ポート・実行）は server.py が担当する。

  起動:  python server.py

元の game.py / core.py のロジックをそのまま再利用:
  - core.judge(secret, guess) → (hit, blow) の判定
  - core.make_secret(digits)  → 重複なし digits 桁の答え生成
"""

import sys
import os

# src/ を import パスに追加して既存の core.py を再利用
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from flask import Flask

from routes import bp


def create_app():
    """Flask アプリケーションファクトリ。"""
    application = Flask(__name__)
    application.secret_key = "hitblow-secret-key-2026"
    application.register_blueprint(bp)
    return application
