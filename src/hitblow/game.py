"""ゲームの進行（入力・表示・ループ）。

★ チームで足す機能は **自分の担当の場所**に書く（1機能=1ファイル）。
   下の「ここに足す」場所は3か所（① 開始時 ② 入力コマンド ③ 勝利時）。
   ペアごとに**別の場所**を直すので、並行作業でも衝突しない。
   import も自分の場所の近くに書くこと（ファイル先頭にまとめない＝衝突回避）。
"""

from .core import judge, make_secret
import time

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
        # アイテム1: 数字のリセット
        if guess in ("shuffle", "item1"):
            if item_amount > 0:
                secret = make_secret(digits)
                item_amount = 0
                print("【アイテム使用】正解の数字が新しくリセットされました！")
            else:
                print("アイテムはすでに使用済みです。")
            continue

        # アイテム2: High/Lowヒント
        if guess in ("highlow", "item2"):
            if item_amount > 0:
                hints = ["low" if int(d) <= 4 else "high" for d in secret]
                item_amount = 0
                print(f"【アイテム使用】各桁の大小: {', '.join(hints)}")
            else:
                print("アイテムはすでに使用済みです。")
            continue

        # ※元の if tries == 1: start = time.time() は①に移動したため削除

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
            # スコア計算: 基本時間 - (残りライフ * 10秒) - (アイテム未使用なら * 30秒)
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