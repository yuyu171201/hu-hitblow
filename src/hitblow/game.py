"""ゲームの進行（入力・表示・ループ）。

★ チームで足す機能は **自分の担当の場所**に書く（1機能=1ファイル）。
   下の「ここに足す」場所は3か所（① 開始時 ② 入力コマンド ③ 勝利時）。
   ペアごとに**別の場所**を直すので、並行作業でも衝突しない。
   import も自分の場所の近くに書くこと（ファイル先頭にまとめない＝衝突回避）。
"""

from .core import judge, make_secret

import time


def play(digits=3):
    item_amount = 1

    secret = make_secret(digits)
    print(f"Hit & Blow（{digits} 桁・重複なし）")

    # ===== ① 開始時に足す（難易度・あいさつ など）: ここに書く =====

    tries = 0
    while True:
        guess = input("予想 > ").strip()

        # ===== ② 入力コマンドに足す（ヒント など）: ここに書く（import もここに） =====
        # アイテム1: 数字のリセット（shuffle または item1）
        if guess in ("shuffle", "item1") and item_amount > 0  :
            item_amount -= 1
            secret = make_secret(digits)
            print("【アイテム使用】正解の数字が新しくリセットされました！")
            continue

        # アイテム2: High/Lowヒント（highlow または item2）
        if guess in ("highlow", "item2") and item_amount > 0:
            item_amount -= 1
            # 0~4をlow、5~9をhighとしてリスト化し、カンマ区切りの文字列にする
            hints = ["low" if int(d) <= 4 else "high" for d in secret]
            print(f"【アイテム使用】各桁の大小: {', '.join(hints)}")
            continue

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