"""Hit & Blow GUI — サーバー起動を司るエントリーポイント。

アプリの組み立ては app.create_app() が担当し、このファイルは
「どう起動するか」（ホスト・ポート・デバッグ・起動時の案内表示）だけを担当する。

使い方:
    python server.py

    # ポートを変えたいとき（環境変数 PORT）
    PORT=8000 python server.py

ブラウザで http://127.0.0.1:<PORT> を開くとモード選択（1人 / 対戦）が表示される。
"""

import os

from app import create_app
from routes import DIGITS

# 既定の待ち受け設定
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


def run(host: str = DEFAULT_HOST, port: int | None = None, debug: bool = True) -> None:
    """Flask 開発サーバーを起動する。

    port を省略した場合は環境変数 PORT を見る（無ければ DEFAULT_PORT）。
    """
    if port is None:
        port = int(os.environ.get("PORT", DEFAULT_PORT))

    app = create_app()

    # 起動時の案内表示（game.py L16 と同じ桁数表示）
    print("=" * 50)
    print(f"  Hit & Blow GUI（{DIGITS} 桁・重複なし）")
    print(f"  http://{host}:{port} でモード選択（1人 / 対戦）")
    print("=" * 50)

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run()
