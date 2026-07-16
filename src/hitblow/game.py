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
        # ① 開始時（play() の① と同じ）: ライフ・アイテム・タイマー
        self.lives = 15
        self.item_amount = 1
        self._start_time = time.time()  # 初回入力前から計測開始
        self._end_time = None
        self._won = False
        self._over = False  # ライフ切れによるゲームオーバー

    # ── セッション保存/復元 ──

    def to_dict(self) -> dict:
        """Flask セッションに保存できる辞書に変換する。"""
        return {
            "digits": self.digits,
            "secret": self.secret,
            "tries": self.tries,
            "lives": self.lives,
            "item_amount": self.item_amount,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "won": self._won,
            "over": self._over,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HitBlowGame":
        """辞書からゲーム状態を復元する。"""
        game = cls.__new__(cls)
        game.digits = data["digits"]
        game.secret = data["secret"]
        game.tries = data["tries"]
        game.lives = data.get("lives", 15)
        game.item_amount = data.get("item_amount", 1)
        game._start_time = data.get("start_time")
        game._end_time = data.get("end_time")
        game._won = data.get("won", False)
        game._over = data.get("over", False)
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
        if self._won or self._over:
            return {"error": "すでにゲームは終了しています"}

        err = self.validate(guess)
        if err:
            return {"error": err}

        # tries += 1 / ライフを1減らす: play() L53-54
        self.tries += 1
        self.lives -= 1

        # 判定: play() L56
        hit, blow = judge(self.secret, guess)

        # 勝利判定: play() L59
        win = hit == self.digits

        result = {
            "hit": hit,
            "blow": blow,
            "tries": self.tries,
            "lives": self.lives,
            "item_amount": self.item_amount,
            "win": win,
            "gameover": False,
            "elapsed": None,
            "score": None,
            "message": None,
        }

        if win:
            # ③ 勝利時（play() の③ と同じ）: スコア計算
            self._won = True
            self._end_time = time.time()
            base_time = self._end_time - self._start_time
            result["elapsed"] = round(base_time, 2)
            # スコア = 基本時間 -（残りライフ × 10秒）-（アイテム未使用なら × 30秒）
            result["score"] = round(
                base_time - (self.lives * 10) - (self.item_amount * 30), 2
            )
            result["message"] = (
                f"正解！ {self.tries} 回で当たり（答え {self.secret}）"
            )
        elif self.lives <= 0:
            # ライフ切れ → ゲームオーバー: play() L75-76
            self._over = True
            result["gameover"] = True
            result["message"] = (
                f"ゲームオーバー... ライフが0になりました。"
                f"（答えは {self.secret} でした）"
            )

        return result

    # ── アイテム使用 (play() の② と同じ挙動) ──

    def use_item(self, kind: str) -> dict:
        """アイテムを使う（1ゲーム中1回のみ）。

        kind:
          "shuffle" / "item1" … 正解の数字をリセット
          "highlow" / "item2" … 各桁の大小（high/low）ヒント
        """
        if self._won or self._over:
            return {"error": "すでにゲームは終了しています"}
        if self.item_amount <= 0:
            return {"error": "アイテムはすでに使用済みです。"}

        # アイテム1: 数字のリセット（shuffle）
        if kind in ("shuffle", "item1"):
            self.secret = make_secret(self.digits)
            self.item_amount = 0
            return {
                "used": True,
                "kind": "shuffle",
                "item_amount": self.item_amount,
                "message": "正解の数字が新しくリセットされました！",
            }

        # アイテム2: High/Low ヒント
        if kind in ("highlow", "item2"):
            hints = ["low" if int(d) <= 4 else "high" for d in self.secret]
            self.item_amount = 0
            return {
                "used": True,
                "kind": "highlow",
                "item_amount": self.item_amount,
                "hint": hints,
                "message": f"各桁の大小: {', '.join(hints)}",
            }

        return {"error": "不明なアイテムです"}

    @property
    def is_won(self) -> bool:
        return self._won

    @property
    def is_over(self) -> bool:
        """勝利またはライフ切れでゲームが終了しているか。"""
        return self._won or self._over


# ── CLI 版（従来どおり） ─────────────────────────────────

def play(digits=3):
    secret = make_secret(digits)
    print(f"Hit & Blow（{digits} 桁・重複なし）")

    # ===== ① 開始時に足す（難易度・あいさつ など）: ここに書く =====
    lives = 15
    item_amount = 1
    start = time.time()  # 初回入力前から時間計測をスタートするように修正
    print(f"初期ライフ: {lives} （アイテムは1ゲーム中1回のみ使用可能）")

    tries = 0
    while True:
        guess = input("予想 > ").strip()

        # ===== ② 入力コマンドに足す（ヒント など）: ここに書く（import もここに） =====
        # アイテム1: 数字のリセット（shuffle）
        if guess in ("shuffle", "item1"):
            if item_amount > 0:
                secret = make_secret(digits)
                item_amount = 0
                print("【アイテム使用】正解の数字が新しくリセットされました！")
            else:
                print("アイテムはすでに使用済みです。")
            continue

        # アイテム2: High/Low ヒント
        if guess in ("highlow", "item2"):
            if item_amount > 0:
                hints = ["low" if int(d) <= 4 else "high" for d in secret]
                item_amount = 0
                print(f"【アイテム使用】各桁の大小: {', '.join(hints)}")
            else:
                print("アイテムはすでに使用済みです。")
            continue

        # ※タイマーは①で開始済み（元の if tries == 1: start = time.time() は不要）

        if len(guess) != digits or not guess.isdigit():
            print(f"{digits} 桁の数字で入力してね")
            continue

        tries += 1
        lives -= 1  # 予想するたびにライフを1減らす

        hit, blow = judge(secret, guess)
        print(f"  Hit={hit}  Blow={blow} （残りライフ: {lives}）")

        if hit == digits:
            end = time.time()
            # ===== ③ 勝利時に足す（スコア・履歴 など）: ここに書く =====
            base_time = end - start
            # スコア計算: 基本時間 -（残りライフ × 10秒）-（アイテム未使用なら × 30秒）
            final_score = base_time - (lives * 10) - (item_amount * 30)

            print(f"\n正解！ {tries} 回で当たり（答え {secret}）")
            print(f"基本所要時間: {base_time:.2f} 秒")
            print(f"【ボーナス】残りライフ({lives}) × -10秒: -{lives * 10} 秒")
            if item_amount > 0:
                print("【ボーナス】アイテム未使用: -30 秒")
            print(f"★ 最終スコア: {final_score:.2f}")
            break

        # ゲームオーバー判定（正解できなかった場合）
        if lives <= 0:
            print(f"\nゲームオーバー... ライフが0になりました。（答えは {secret} でした）")
            break
