# タスク1: GUIの実装

worksheetの補足: 「Django使う？」

## 結論

**すでにFlaskで実装済み。** Djangoは使わない（Flaskの方が軽量で、この規模には十分）。
→ 新規実装は不要。現状の理解と、対戦モード追加(タスク2)に向けた整理だけ行う。

## 現状の構成

```
GUIplay/
├── app.py              … Flaskアプリ本体
├── routes.py           … ルーティング（/, /guess, /new_game）
├── templates/index.html… ゲーム画面
└── static/
    ├── css/style.css
    └── js/game.js      … fetchで/guessを叩いて結果表示
```

ロジックは `src/hitblow/core.py`（`judge` / `make_secret`）を再利用している。

## 段階的にやること

- [ ] **1-1. 動作確認**
  - `uv run flask --app GUIplay.app run` などでサーバ起動し、ブラウザで1人プレイが動くか確認
  - `/`（出題）→ `/guess`（判定）→ `/new_game`（リセット）の流れを目視
- [ ] **1-2. コードを読んで把握**
  - `routes.py` … セッションで secret/tries/start_time を保持している構造
  - `game.js` … どうやってサーバと通信し、画面更新しているか
  - タスク2で同じパターンを流用するので、通信の型（fetch → JSON）を頭に入れる
- [ ] **1-3. Django不採用の理由を一言メモ**（第2回の報告用）
  - 「Flaskで既に動いており、規模的にDjangoは過剰なのでFlaskを継続」と言えるようにしておく

## 完了条件

- 1人プレイのGUIがローカルで動くことを自分の目で確認できた
- routes.py / game.js の通信パターンを説明できる
