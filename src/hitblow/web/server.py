"""Hit & Blow GUI — サーバー起動を司るエントリーポイント。

アプリの組み立ては app.create_app() が担当し、このファイルは
「どう起動するか」（ホスト・ポート・デバッグ・サブパス・起動時の案内表示）を担当する。

使い方:
    uv run hitblow_server

    # ポートを変えたいとき（環境変数 PORT）
    PORT=8000 uv run hitblow_server

    # 別の端末から接続したいとき（例: Linux サーバーでネットワーク対戦）
    #   HOST=0.0.0.0 で全アドレスを待ち受ける。debug は本番では 0 推奨。
    HOST=0.0.0.0 PORT=8000 DEBUG=0 uv run hitblow_server

    # リバースプロキシで /hitblow/ 配下に置くとき（内部ポートは外に出さない）
    #   BASE_PATH でサブパスを指定。Nginx はそのまま横流しするだけでよい。
    HOST=127.0.0.1 PORT=8001 DEBUG=0 BASE_PATH=/hitblow uv run hitblow_server

ブラウザで http://<サーバーのIP>:<PORT>/ もしくは
http://<ドメイン>/<BASE_PATH>/ を開くとモード選択（1人 / 対戦）が表示される。
"""

import os

from .app import create_app
from .routes import DIGITS

# 既定の待ち受け設定
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


def _env_bool(name: str, default: bool) -> bool:
    """環境変数を真偽値として読む（"0"/"false"/"no" を False とみなす）。"""
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() not in ("0", "false", "no", "off", "")


def run(
    host: str | None = None,
    port: int | None = None,
    debug: bool | None = None,
    base_path: str | None = None,
) -> None:
    """Flask 開発サーバーを起動する。

    引数を省略した場合は環境変数を見る:
      HOST      … 待ち受けアドレス（既定 127.0.0.1。外部公開は 0.0.0.0）
      PORT      … ポート番号（既定 5000）
      DEBUG     … デバッグ/自動リロード（既定 有効。本番は DEBUG=0 推奨）
      BASE_PATH … サブパス公開時のプレフィックス（例 /hitblow。既定は無し）
    """
    if host is None:
        host = os.environ.get("HOST", DEFAULT_HOST)
    if port is None:
        port = int(os.environ.get("PORT", DEFAULT_PORT))
    if debug is None:
        debug = _env_bool("DEBUG", True)
    if base_path is None:
        base_path = os.environ.get("BASE_PATH", "")

    app = create_app(base_path=base_path)

    # 起動時の案内表示（game.py L16 と同じ桁数表示）
    where = f"http://{host}:{port}{base_path}/" if base_path.strip("/") else f"http://{host}:{port}"
    print("=" * 50)
    print(f"  Hit & Blow GUI（{DIGITS} 桁・重複なし）")
    print(f"  {where} でモード選択（1人 / 対戦）")
    if base_path.strip("/"):
        print(f"  （サブパス公開: BASE_PATH={base_path}）")
    print("=" * 50)

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run()
