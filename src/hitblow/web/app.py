"""Hit & Blow GUI — Flask アプリケーションファクトリ。

このファイルは「アプリの組み立て」だけを担当する（＝create_app）。
サーバーの起動（ポート・実行）は server.py が担当する。

  起動:  uv run hitblow_server

サブパス配下での公開（リバースプロキシ）:
  BASE_PATH（例 "/hitblow"）を指定すると、その配下で動くようになる。
  url_for / 静的ファイル / JS の通信先すべてがプレフィックス付きになるため、
  Nginx 側は /hitblow/ を「そのまま」127.0.0.1:PORT へ横流しするだけでよい
  （プレフィックスを剥がす設定や X-Forwarded-Prefix ヘッダは不要）。

元の game.py / core.py のロジックをそのまま再利用:
  - core.judge(secret, guess) → (hit, blow) の判定
  - core.make_secret(digits)  → 重複なし digits 桁の答え生成
"""

import os

from flask import Flask

from .routes import bp


class _PrefixMiddleware:
    """サブパス（例 /hitblow）配下で動かすための WSGI ミドルウェア。

    リバースプロキシが /hitblow/ を「そのまま」転送してくる前提で:
      - PATH_INFO からプレフィックスを取り除いて Flask のルートに合わせる
      - SCRIPT_NAME にプレフィックスを設定する
    これにより url_for / request.script_root がプレフィックス付きの URL を返し、
    静的ファイルや各 API の通信先が自動的に /hitblow/... になる。

    prefix が空なら何もしない（＝通常の直接公開と同じ挙動）。
    """

    def __init__(self, app, prefix=""):
        self.app = app
        p = "/" + prefix.strip("/") if prefix.strip("/") else ""
        self.prefix = p

    def __call__(self, environ, start_response):
        if self.prefix:
            path = environ.get("PATH_INFO", "")
            if path == self.prefix or path.startswith(self.prefix + "/"):
                environ["PATH_INFO"] = path[len(self.prefix):] or "/"
            environ["SCRIPT_NAME"] = self.prefix
        return self.app(environ, start_response)


def create_app(base_path=None):
    """Flask アプリケーションファクトリ。

    base_path を省略すると環境変数 BASE_PATH を参照する（無ければ直接公開）。
    """
    application = Flask(__name__)
    application.secret_key = "hitblow-secret-key-2026"
    application.register_blueprint(bp)

    if base_path is None:
        base_path = os.environ.get("BASE_PATH", "")
    if base_path.strip("/"):
        application.wsgi_app = _PrefixMiddleware(application.wsgi_app, base_path)

    return application
