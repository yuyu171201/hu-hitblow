"""Hit & Blow GUI（Flask）パッケージ。

`create_app()` でアプリを組み立て、`server.run()` で起動する。
コンソールスクリプト:  uv run hitblow_server
"""

from .app import create_app

__all__ = ["create_app"]
