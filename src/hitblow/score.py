def calc_score(tries: int, lives: int, item_amount: int, elapsed_time: float, difficulty: str = "normal") -> int:
    """スコアを計算する。

    1. まず、残りライフ・アイテム・経過時間に応じたボーナス点を計算する。
    2. その後、トライ回数に応じた減点を行う。
    """
    # ボーナス点
    match difficulty:
        case "easy":
            bonus_multiplier = 0.3
        case "normal":
            bonus_multiplier = 1.0
        case "hard":
            bonus_multiplier = 3.0

    bonus = (lives * 100 * bonus_multiplier) + (item_amount * 50) - int(elapsed_time)
    # 減点
    penalty = tries * 10
    # 最終スコア
    score = max(bonus - penalty, 0)
    return score