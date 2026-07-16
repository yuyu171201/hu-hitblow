"""ゲームの進行（入力・表示・ループ）。

★ チームで足す機能は **自分の担当の場所**に書く（1機能=1ファイル）。
   下の「ここに足す」場所は3か所（① 開始時 ② 入力コマンド ③ 勝利時）。
   ペアごとに**別の場所**を直すので、並行作業でも衝突しない。
   import も自分の場所の近くに書くこと（ファイル先頭にまとめない＝衝突回避）。
"""

from .core import judge, make_secret

import time


# ── GUI / Web から使うためのクラス ──────────────────────────

class HitBlowGame:
    """Hit & Blow のゲーム状態を管理するクラス。

    play() と同じロジックを、input()/print() に依存しない形で提供する。
    GUIplay/routes.py から import して使う。
    """

    def __init__(self, digits=3):
        self.digits = digits
        self.secret = make_secret(digits)
        self.tries = 0
        self._start_time = None  # tries==1 で開始 (play() L29-30)
        self._end_time = None
        self._won = False

    # ── セッション保存/復元 ──

    def to_dict(self) -> dict:
        """Flask セッションに保存できる辞書に変換する。"""
        return {
            "digits": self.digits,
            "secret": self.secret,
            "tries": self.tries,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "won": self._won,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HitBlowGame":
        """辞書からゲーム状態を復元する。"""
        game = cls.__new__(cls)
        game.digits = data["digits"]
        game.secret = data["secret"]
        game.tries = data["tries"]
        game._start_time = data.get("start_time")
        game._end_time = data.get("end_time")
        game._won = data.get("won", False)
        return game

    # ── バリデーション (play() L32) ──

    def validate(self, guess: str) -> str | None:
        """入力チェック。問題なければ None、エラーなら理由の文字列を返す。"""
        if len(guess) != self.digits or not guess.isdigit():
            return f"{self.digits} 桁の数字で入力してね"
        if len(set(guess)) != len(guess):
            return "数字が重複しています"
        return None

    # ── 予想を受け付ける (play() L35-44) ──

    def guess(self, guess: str) -> dict:
        """予想を判定して結果を辞書で返す。"""
        if self._won:
            return {"error": "すでにゲームは終了しています"}

        err = self.validate(guess)
        if err:
            return {"error": err}

        # タイマー開始: play() L29-30
        if self.tries == 1:
            self._start_time = time.time()

        # tries += 1: play() L35
        self.tries += 1

        # 判定: play() L36
        hit, blow = judge(self.secret, guess)

        # 勝利判定: play() L38
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
            self._end_time = time.time()
            if self._start_time is not None:
                result["elapsed"] = round(self._end_time - self._start_time, 2)
            # play() L43
            result["message"] = (
                f"正解！ {self.tries} 回で当たり（答え {self.secret}）"
            )

        return result

    @property
    def is_won(self) -> bool:
        return self._won


# ── CLI 版（従来どおり） ─────────────────────────────────

def play(digits=3):
    secret = make_secret(digits)
    print(f"Hit & Blow（{digits} 桁・重複なし）")

    # ===== ① 開始時に足す（難易度・あいさつ など）: ここに書く =====

    tries = 0
    while True:
        guess = input("予想 > ").strip()

        # ===== ② 入力コマンドに足す（ヒント など）: ここに書く（import もここに） =====
        # 例:  from .hint import hint
        #      if guess == "h":
        #          print(hint(secret)); continue

        if tries == 1:
            start = time.time()

        if len(guess) != digits or not guess.isdigit():
            print(f"{digits} 桁の数字で入力してね")
            continue
        tries += 1
        hit, blow = judge(secret, guess)
        print(f"  Hit={hit}  Blow={blow}")
        if hit == digits:

            end = time.time()
            # ===== ③ 勝利時に足す（スコア・履歴 など）: ここに書く =====

            print(f"正解！ {tries} 回で当たり（答え {secret}）")
            print(f"所要時間: {end - start:.2f} 秒")
            break
