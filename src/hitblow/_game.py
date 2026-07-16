"""game.py に追加する HitBlowGame クラスのプロトタイプ。

既存の play() 関数はそのまま残し、このクラスを追加することで
GUIplay/routes.py から game.py を import してロジックを再利用できる。

使い方 (routes.py 側):
    from hitblow.game import HitBlowGame

    game = HitBlowGame(digits=3)
    result = game.guess("123")
    # result = {"hit": 1, "blow": 1, "tries": 1, "win": False}
"""

import time

from .core import judge, make_secret


class HitBlowGame:
    """Hit & Blow のゲーム状態を管理するクラス。

    game.py の play() と同じロジックを、
    input()/print() に依存しない形で提供する。
    """

    def __init__(self, digits=3):
        self.digits = digits
        self.secret = make_secret(digits)
        self.tries = 0
        self._start_time = None  # tries==1 で開始 (game.py L29-30)
        self._end_time = None
        self._won = False
        # ===== ① 開始時に足す（難易度・あいさつ など）: ここに書く =====

    # ── バリデーション (game.py L32) ──

    def validate(self, guess: str) -> str | None:
        """入力チェック。問題なければ None、エラーなら理由の文字列を返す。"""
        if len(guess) != self.digits or not guess.isdigit():
            return f"{self.digits} 桁の数字で入力してね"
        if len(set(guess)) != len(guess):
            return "数字が重複しています"
        return None

    # ── 予想を受け付ける (game.py L35-44) ──

    def guess(self, guess: str) -> dict:
        """予想を判定して結果を辞書で返す。

        Returns:
            {
                "hit":     int,
                "blow":    int,
                "tries":   int,
                "win":     bool,
                "elapsed": float | None,   # 勝利時のみ (秒)
                "message": str  | None,    # 勝利時のみ
            }
        """
        if self._won:
            return {"error": "すでにゲームは終了しています"}

        # ===== ② 入力コマンドに足す（ヒント など）: ここに書く（import もここに） =====
        # 例:  from .hint import hint
        #      if guess == "h":
        #          print(hint(secret)); continue

        # バリデーション
        err = self.validate(guess)
        if err:
            return {"error": err}

        # タイマー開始: game.py L29-30 (if tries == 1: start = time.time())
        if self.tries == 1:
            self._start_time = time.time()

        # tries += 1: game.py L35
        self.tries += 1

        # 判定: game.py L36
        hit, blow = judge(self.secret, guess)

        # 勝利判定: game.py L38
        win = hit == self.digits

        result = {
            "hit": hit,
            "blow": blow,
            "tries": self.tries,
            "win": win,
            "elapsed": None,
            "message": None,
        }

        if win:
            self._won = True
            # ===== ③ 勝利時に足す（スコア・履歴 など）: ここに書く =====

            # 所要時間: game.py L40 (end = time.time())
            self._end_time = time.time()
            if self._start_time is not None:
                result["elapsed"] = round(self._end_time - self._start_time, 2)
            # game.py L43
            result["message"] = (
                f"正解！ {self.tries} 回で当たり（答え {self.secret}）"
            )

        return result

    # ── 状態参照 ──

    @property
    def is_won(self) -> bool:
        return self._won


# ============================================================
# 既存の play() をこのクラスで書き直した例（参考）
# 実際には game.py の play() をこのように書き換えることも可能
# ============================================================

def play(digits=3):
    """CLI 版 Hit & Blow（HitBlowGame を使ったバージョン）。"""
    game = HitBlowGame(digits)
    print(f"Hit & Blow（{digits} 桁・重複なし）")

    while True:
        raw = input("予想 > ").strip()

        result = game.guess(raw)

        if "error" in result:
            print(result["error"])
            continue

        print(f"  Hit={result['hit']}  Blow={result['blow']}")

        if result["win"]:
            print(result["message"])
            if result["elapsed"] is not None:
                print(f"所要時間: {result['elapsed']:.2f} 秒")
            break
