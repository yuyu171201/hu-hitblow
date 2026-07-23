"""core.judge のテスト（最初から緑）。機能を足しても緑を保とう＝回帰テスト。"""

from hitblow.core import judge
from hitblow.game import HitBlowGame
from hitblow.score import calc_score


def test_all_hit():
    assert judge("123", "123") == (3, 0)


def test_all_blow():
    assert judge("123", "231") == (0, 3)


def test_mix():
    assert judge("123", "132") == (1, 2)


def test_none():
    assert judge("123", "456") == (0, 0)


def test_calc_score_uses_bonus_and_penalty():
    assert calc_score(3, 5, 1, 12.0) == 500 + 50 - 12 - 30


def test_guess_uses_calc_score_for_win_result():
    game = HitBlowGame(secret="123")
    result = game.guess("123")

    assert result["win"] is True
    assert result["score"] == calc_score(1, 14, 1, result["elapsed"])
