def calc_score(tries: int, lives: int, item_amount: int, elapsed_time: float) -> int:
    """スコアを計算する。

    1. まず、残りライフ・アイテム・経過時間に応じたボーナス点を計算する。
    2. その後、トライ回数に応じた減点を行う。
    """
    # ボーナス点
    bonus = (lives * 100) + (item_amount * 50) - int(elapsed_time)
    # 減点
    penalty = tries * 10
    # 最終スコア
    score = max(bonus - penalty, 0)
    return score