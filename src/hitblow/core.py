"""ゲームの中心ロジック（純粋関数＝テストしやすい）。

ここは責務「判定と出題」。画面・入力には触らない（それは game.py）。
"""

import random


# 判定する関数
def judge(secret, guess):
    """secret と guess（同じ桁数の文字列）を比べて (hit, blow) を返す。

    hit  … 数字も位置も合っている個数
    blow … 数字は含まれるが位置が違う個数
    """
    hits = sum(s == g for s, g in zip(secret, guess))
    common = sum(min(secret.count(d), guess.count(d)) for d in set(guess))
    return hits, common - hits


# 回答を作る関数
def make_secret(digits=3):
    """重複なしの digits 桁の答えを作る。"""
    return "".join(random.sample("0123456789", digits))

def make_secret2(digits=3):
    """重複ありの digits 桁の答えを作る。"""
    return "".join(random.choices("0123456789", k=digits))
