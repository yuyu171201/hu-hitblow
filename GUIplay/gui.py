"""Hit & Blow GUI — Web アプリで遊べる GUI 版。

使い方:
    pip install flask
    python gui.py

ブラウザで http://127.0.0.1:5000 を開いてプレイ。

元の game.py / core.py のロジックをそのまま再利用:
  - core.judge(secret, guess) → (hit, blow) の判定
  - core.make_secret(digits)  → 重複なし digits 桁の答え生成
  - game.py と同じタイマー挙動（tries==1 で開始）
"""

import sys
import os
import time  # game.py と同様にサーバー側で所要時間を計測

# src/ を import パスに追加して既存の core.py を再利用
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from flask import Flask, render_template_string, request, jsonify, session

# --- 元の core.py から判定・出題ロジックをそのまま利用 ---
# (game.py の `from .core import judge, make_secret` と同じ)
from hitblow.core import judge, make_secret

app = Flask(__name__)
app.secret_key = "hitblow-secret-key-2026"

# game.py の play(digits=3) と同じデフォルト桁数
DIGITS = 3

# ──────────────────────────────────────────────
# HTML テンプレート（全部 1 ファイルに収める）
# ──────────────────────────────────────────────

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hit &amp; Blow — GUI</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
/* ===== Reset & Base ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg-dark: #0a0e1a;
  --bg-card: rgba(255, 255, 255, 0.04);
  --bg-card-hover: rgba(255, 255, 255, 0.08);
  --glass-border: rgba(255, 255, 255, 0.08);
  --accent: #6c63ff;
  --accent-glow: rgba(108, 99, 255, 0.4);
  --hit-color: #ff6b9d;
  --blow-color: #51cf66;
  --text-primary: #e8e6f0;
  --text-secondary: rgba(232, 230, 240, 0.55);
  --digit-active: rgba(108, 99, 255, 0.25);
  --digit-filled: rgba(108, 99, 255, 0.12);
  --slot-selected: #6c63ff;
  --slot-default: rgba(255, 255, 255, 0.12);
  --success-bg: rgba(81, 207, 102, 0.1);
  --success-border: rgba(81, 207, 102, 0.3);
  --font-main: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

body {
  font-family: var(--font-main);
  background: var(--bg-dark);
  color: var(--text-primary);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow-x: hidden;
}

/* Animated background gradient */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 600px 400px at 20% 20%, rgba(108,99,255,0.12), transparent),
    radial-gradient(ellipse 500px 500px at 80% 80%, rgba(255,107,157,0.08), transparent),
    radial-gradient(ellipse 400px 300px at 50% 50%, rgba(81,207,102,0.05), transparent);
  z-index: -1;
  animation: bgShift 20s ease-in-out infinite alternate;
}
@keyframes bgShift {
  0%   { transform: scale(1) translate(0, 0); }
  100% { transform: scale(1.1) translate(-20px, 10px); }
}

/* ===== Header ===== */
.header {
  text-align: center;
  padding: 2.5rem 1rem 1rem;
}
.header h1 {
  font-size: 2.4rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #6c63ff 0%, #ff6b9d 50%, #51cf66 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: titleGlow 3s ease-in-out infinite alternate;
}
@keyframes titleGlow {
  0%   { filter: brightness(1); }
  100% { filter: brightness(1.3); }
}
.header p {
  color: var(--text-secondary);
  margin-top: 0.4rem;
  font-size: 0.95rem;
}

/* ===== Game Container ===== */
.game-container {
  width: 100%;
  max-width: 480px;
  padding: 0 1rem 2rem;
}

/* ===== Glass Card ===== */
.card {
  background: var(--bg-card);
  border: 1px solid var(--glass-border);
  border-radius: 20px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  transition: background 0.3s;
}

/* ===== Status Bar ===== */
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
.status-bar .label {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
}
.status-bar .value {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.1rem;
}

/* ===== Digit Slots ===== */
.slots-wrapper {
  display: flex;
  justify-content: center;
  gap: 14px;
  margin: 1.4rem 0;
}
.slot {
  width: 72px;
  height: 88px;
  border-radius: 16px;
  border: 2.5px solid var(--slot-default);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 2.2rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(.4,0,.2,1);
  position: relative;
  background: transparent;
  user-select: none;
}
.slot:hover {
  border-color: rgba(108, 99, 255, 0.5);
  background: rgba(108, 99, 255, 0.06);
}
.slot.selected {
  border-color: var(--slot-selected);
  background: var(--digit-active);
  box-shadow: 0 0 20px var(--accent-glow), inset 0 0 20px rgba(108,99,255,0.08);
  transform: translateY(-3px);
}
.slot.filled {
  background: var(--digit-filled);
  color: var(--text-primary);
}
.slot.selected.filled {
  background: var(--digit-active);
}

/* Cursor blink for selected empty slot */
.slot.selected:not(.filled)::after {
  content: '|';
  font-size: 2rem;
  color: var(--accent);
  animation: blink 1s step-end infinite;
}
@keyframes blink {
  50% { opacity: 0; }
}

/* ===== Number Pad ===== */
.numpad {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-bottom: 1rem;
}
.num-btn {
  aspect-ratio: 1;
  border-radius: 14px;
  border: 1.5px solid var(--glass-border);
  background: var(--bg-card);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 1.4rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(.4,0,.2,1);
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}
.num-btn:hover {
  background: var(--bg-card-hover);
  border-color: rgba(108, 99, 255, 0.4);
  transform: scale(1.06);
}
.num-btn:active {
  transform: scale(0.95);
  background: var(--digit-active);
}
.num-btn.used {
  opacity: 0.25;
  pointer-events: none;
}

/* ===== Action Buttons ===== */
.action-row {
  display: flex;
  gap: 10px;
}
.btn {
  flex: 1;
  padding: 14px 0;
  border-radius: 14px;
  border: none;
  font-family: var(--font-main);
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(.4,0,.2,1);
  user-select: none;
}
.btn-submit {
  background: linear-gradient(135deg, #6c63ff, #8b5cf6);
  color: #fff;
  box-shadow: 0 4px 20px var(--accent-glow);
}
.btn-submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px var(--accent-glow);
}
.btn-submit:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.btn-clear {
  background: rgba(255,255,255,0.06);
  color: var(--text-secondary);
  border: 1px solid var(--glass-border);
}
.btn-clear:hover {
  background: rgba(255,255,255,0.1);
  color: var(--text-primary);
}

/* ===== History Table ===== */
.history-title {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin-bottom: 0.7rem;
}
.history-list {
  list-style: none;
  max-height: 320px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(108,99,255,0.3) transparent;
}
.history-item {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  border-radius: 12px;
  margin-bottom: 6px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  animation: slideIn 0.35s cubic-bezier(.4,0,.2,1);
  transition: background 0.2s;
}
.history-item:hover {
  background: rgba(255,255,255,0.05);
}
@keyframes slideIn {
  from { opacity: 0; transform: translateY(-8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.history-num {
  width: 28px;
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}
.history-guess {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 1.3rem;
  font-weight: 700;
  letter-spacing: 0.15em;
}
.history-result {
  display: flex;
  gap: 12px;
}
.badge {
  padding: 3px 10px;
  border-radius: 8px;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 700;
}
.badge-hit {
  background: rgba(255, 107, 157, 0.15);
  color: var(--hit-color);
  border: 1px solid rgba(255, 107, 157, 0.25);
}
.badge-blow {
  background: rgba(81, 207, 102, 0.12);
  color: var(--blow-color);
  border: 1px solid rgba(81, 207, 102, 0.2);
}

/* ===== Victory Overlay ===== */
.victory-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(10, 14, 26, 0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.4s;
}
.victory-overlay.show { display: flex; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.victory-card {
  text-align: center;
  padding: 3rem 2.5rem;
  border-radius: 28px;
  background: var(--success-bg);
  border: 1.5px solid var(--success-border);
  max-width: 380px;
  animation: popIn 0.5s cubic-bezier(.4,0,.2,1);
}
@keyframes popIn {
  from { transform: scale(0.8); opacity: 0; }
  to   { transform: scale(1); opacity: 1; }
}
.victory-emoji { font-size: 4rem; margin-bottom: 0.8rem; }
.victory-card h2 {
  font-size: 1.8rem;
  font-weight: 800;
  margin-bottom: 0.4rem;
  background: linear-gradient(135deg, #51cf66, #6c63ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.victory-stats {
  color: var(--text-secondary);
  font-size: 1rem;
  margin-bottom: 1.5rem;
  line-height: 1.7;
}
.victory-stats strong {
  color: var(--text-primary);
  font-weight: 700;
}
.btn-new-game {
  padding: 14px 36px;
  border-radius: 14px;
  border: none;
  background: linear-gradient(135deg, #51cf66, #40c057);
  color: #0a0e1a;
  font-family: var(--font-main);
  font-size: 1rem;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.25s;
}
.btn-new-game:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(81, 207, 102, 0.3);
}

/* ===== Confetti ===== */
.confetti-container {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1001;
  overflow: hidden;
}
.confetti {
  position: absolute;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  top: -20px;
  animation: confettiFall linear forwards;
}
@keyframes confettiFall {
  to {
    top: 110vh;
    transform: rotate(720deg);
  }
}

/* ===== Message Flash ===== */
.message {
  text-align: center;
  padding: 10px;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 1rem;
  display: none;
  animation: slideIn 0.3s;
}
.message.error {
  display: block;
  background: rgba(255, 107, 107, 0.1);
  border: 1px solid rgba(255, 107, 107, 0.25);
  color: #ff6b6b;
}

/* ===== Responsive ===== */
@media (max-width: 400px) {
  .slot { width: 60px; height: 74px; font-size: 1.8rem; }
  .num-btn { font-size: 1.2rem; }
  .header h1 { font-size: 1.8rem; }
}
</style>
</head>
<body>

<div class="header">
  <h1>Hit &amp; Blow</h1>
  <p>3 桁の数字を当てよう（重複なし）</p>
</div>

<div class="game-container">
  <!-- Status -->
  <div class="card">
    <div class="status-bar">
      <div>
        <span class="label">回数</span>
        <span class="value" id="tries-count">0</span>
      </div>
      <div>
        <span class="label">経過時間</span>
        <span class="value" id="timer">00:00</span>
      </div>
    </div>
  </div>

  <!-- Input Area -->
  <div class="card">
    <!-- Message -->
    <div class="message" id="message"></div>

    <!-- Digit Slots -->
    <div class="slots-wrapper">
      <div class="slot selected" data-index="0" onclick="selectSlot(0)"></div>
      <div class="slot" data-index="1" onclick="selectSlot(1)"></div>
      <div class="slot" data-index="2" onclick="selectSlot(2)"></div>
    </div>

    <!-- Number Pad -->
    <div class="numpad">
      <button class="num-btn" onclick="inputDigit('0')">0</button>
      <button class="num-btn" onclick="inputDigit('1')">1</button>
      <button class="num-btn" onclick="inputDigit('2')">2</button>
      <button class="num-btn" onclick="inputDigit('3')">3</button>
      <button class="num-btn" onclick="inputDigit('4')">4</button>
      <button class="num-btn" onclick="inputDigit('5')">5</button>
      <button class="num-btn" onclick="inputDigit('6')">6</button>
      <button class="num-btn" onclick="inputDigit('7')">7</button>
      <button class="num-btn" onclick="inputDigit('8')">8</button>
      <button class="num-btn" onclick="inputDigit('9')">9</button>
    </div>

    <!-- Action Buttons -->
    <div class="action-row">
      <button class="btn btn-clear" onclick="clearSlots()">クリア</button>
      <button class="btn btn-submit" id="submit-btn" onclick="submitGuess()" disabled>送信</button>
    </div>
  </div>

  <!-- History -->
  <div class="card" id="history-card" style="display:none;">
    <div class="history-title">履歴</div>
    <ul class="history-list" id="history-list"></ul>
  </div>
</div>

<!-- Victory Overlay -->
<div class="victory-overlay" id="victory-overlay">
  <div class="victory-card">
    <div class="victory-emoji">🎉</div>
    <h2>正解！</h2>
    <div class="victory-stats" id="victory-stats"></div>
    <button class="btn-new-game" onclick="newGame()">もう一度遊ぶ</button>
  </div>
</div>
<div class="confetti-container" id="confetti-container"></div>

<script>
// ===== Game State =====
let selectedSlot = 0;
const digits = [null, null, null];
let gameOver = false;
let timerInterval = null;
let startTime = null;

// ===== Slot Selection =====
function selectSlot(index) {
  if (gameOver) return;
  selectedSlot = index;
  document.querySelectorAll('.slot').forEach((s, i) => {
    s.classList.toggle('selected', i === index);
  });
}

// ===== Digit Input =====
function inputDigit(d) {
  if (gameOver) return;
  hideMessage();

  // Check if digit is already used in another slot
  for (let i = 0; i < 3; i++) {
    if (i !== selectedSlot && digits[i] === d) {
      showMessage('同じ数字は使えません');
      return;
    }
  }

  digits[selectedSlot] = d;
  const slot = document.querySelector(`.slot[data-index="${selectedSlot}"]`);
  slot.textContent = d;
  slot.classList.add('filled');

  // Animate
  slot.style.transform = 'scale(1.1)';
  setTimeout(() => { slot.style.transform = ''; }, 150);

  // Auto-advance to next empty slot (to the right, wrapping)
  let next = -1;
  for (let offset = 1; offset <= 3; offset++) {
    const idx = (selectedSlot + offset) % 3;
    if (digits[idx] === null) {
      next = idx;
      break;
    }
  }
  if (next !== -1) {
    selectSlot(next);
  }

  updateUsedDigits();
  updateSubmitButton();
}

// ===== Update Used Digits =====
function updateUsedDigits() {
  document.querySelectorAll('.num-btn').forEach(btn => {
    const d = btn.textContent;
    btn.classList.toggle('used', digits.includes(d));
  });
}

// ===== Submit Button State =====
function updateSubmitButton() {
  const allFilled = digits.every(d => d !== null);
  document.getElementById('submit-btn').disabled = !allFilled;
}

// ===== Clear Slots =====
function clearSlots() {
  if (gameOver) return;
  digits.fill(null);
  document.querySelectorAll('.slot').forEach(s => {
    s.textContent = '';
    s.classList.remove('filled');
  });
  selectSlot(0);
  updateUsedDigits();
  updateSubmitButton();
  hideMessage();
}

// ===== Message =====
function showMessage(text) {
  const msg = document.getElementById('message');
  msg.textContent = text;
  msg.className = 'message error';
}
function hideMessage() {
  document.getElementById('message').className = 'message';
}

// ===== Submit Guess =====
async function submitGuess() {
  if (gameOver) return;
  const guess = digits.join('');
  if (guess.length !== 3) return;

  // Start timer on first guess
  if (!startTime) {
    startTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);
  }

  try {
    const res = await fetch('/guess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guess })
    });
    const data = await res.json();

    if (data.error) {
      showMessage(data.error);
      return;
    }

    // Update tries
    document.getElementById('tries-count').textContent = data.tries;

    // Add to history
    addHistory(data.tries, guess, data.hit, data.blow);

    // Check win
    if (data.win) {
      gameOver = true;
      clearInterval(timerInterval);
      // サーバー側で game.py と同じ time.time() で計算した所要時間を使用
      const elapsed = data.elapsed != null ? data.elapsed : ((Date.now() - startTime) / 1000).toFixed(1);
      // game.py L43 と同じメッセージ: 「正解！ {tries} 回で当たり（答え {secret}）」
      showVictory(data.tries, elapsed, guess, data.message);
    } else {
      // Reset for next guess
      clearSlots();
    }
  } catch (err) {
    showMessage('通信エラーが発生しました');
  }
}

// ===== History =====
function addHistory(num, guess, hit, blow) {
  const card = document.getElementById('history-card');
  card.style.display = 'block';
  const list = document.getElementById('history-list');
  const li = document.createElement('li');
  li.className = 'history-item';
  li.innerHTML = `
    <span class="history-num">#${num}</span>
    <span class="history-guess">${guess.split('').join(' ')}</span>
    <span class="history-result">
      <span class="badge badge-hit">H ${hit}</span>
      <span class="badge badge-blow">B ${blow}</span>
    </span>
  `;
  list.prepend(li);
}

// ===== Timer =====
function updateTimer() {
  if (!startTime) return;
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const min = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const sec = String(elapsed % 60).padStart(2, '0');
  document.getElementById('timer').textContent = `${min}:${sec}`;
}

// ===== Victory =====
// game.py L43-44 の表示を GUI で再現:
//   正解！ {tries} 回で当たり（答え {secret}）
//   所要時間: {end - start:.2f} 秒
function showVictory(tries, elapsed, answer, serverMessage) {
  const stats = document.getElementById('victory-stats');
  let html = '';
  if (serverMessage) {
    // サーバーから game.py と同じフォーマットのメッセージを表示
    html += `<strong>${serverMessage}</strong><br>`;
  } else {
    html += `<strong>${answer}</strong> を<br>`;
    html += `<strong>${tries}</strong> 回で正解！<br>`;
  }
  if (elapsed != null) {
    // game.py L44: 所要時間: {end - start:.2f} 秒
    html += `所要時間: <strong>${elapsed}</strong> 秒`;
  }
  stats.innerHTML = html;
  document.getElementById('victory-overlay').classList.add('show');
  launchConfetti();
}

// ===== Confetti =====
function launchConfetti() {
  const container = document.getElementById('confetti-container');
  const colors = ['#6c63ff', '#ff6b9d', '#51cf66', '#ffd43b', '#4ecdc4', '#ff6b6b'];
  for (let i = 0; i < 80; i++) {
    const c = document.createElement('div');
    c.className = 'confetti';
    c.style.left = Math.random() * 100 + 'vw';
    c.style.background = colors[Math.floor(Math.random() * colors.length)];
    c.style.width = (Math.random() * 8 + 6) + 'px';
    c.style.height = (Math.random() * 8 + 6) + 'px';
    c.style.animationDuration = (Math.random() * 2 + 2) + 's';
    c.style.animationDelay = (Math.random() * 1.5) + 's';
    c.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
    container.appendChild(c);
  }
  setTimeout(() => { container.innerHTML = ''; }, 5000);
}

// ===== New Game =====
async function newGame() {
  await fetch('/new_game', { method: 'POST' });
  document.getElementById('victory-overlay').classList.remove('show');
  document.getElementById('history-list').innerHTML = '';
  document.getElementById('history-card').style.display = 'none';
  document.getElementById('tries-count').textContent = '0';
  document.getElementById('timer').textContent = '00:00';
  gameOver = false;
  startTime = null;
  clearInterval(timerInterval);
  timerInterval = null;
  clearSlots();
}

// ===== Keyboard Support =====
document.addEventListener('keydown', (e) => {
  if (gameOver) return;
  if (e.key >= '0' && e.key <= '9') {
    inputDigit(e.key);
  } else if (e.key === 'Backspace') {
    // Clear current slot and move left
    if (digits[selectedSlot] !== null) {
      digits[selectedSlot] = null;
      const slot = document.querySelector(`.slot[data-index="${selectedSlot}"]`);
      slot.textContent = '';
      slot.classList.remove('filled');
      updateUsedDigits();
      updateSubmitButton();
    } else if (selectedSlot > 0) {
      selectSlot(selectedSlot - 1);
      digits[selectedSlot] = null;
      const slot = document.querySelector(`.slot[data-index="${selectedSlot}"]`);
      slot.textContent = '';
      slot.classList.remove('filled');
      updateUsedDigits();
      updateSubmitButton();
    }
  } else if (e.key === 'Enter') {
    submitGuess();
  } else if (e.key === 'ArrowLeft' && selectedSlot > 0) {
    selectSlot(selectedSlot - 1);
  } else if (e.key === 'ArrowRight' && selectedSlot < 2) {
    selectSlot(selectedSlot + 1);
  }
});
</script>
</body>
</html>
"""


# ──────────────────────────────────────────────
# Flask ルーティング
# ──────────────────────────────────────────────
# game.py の play() に対応する処理を Web 向けに再構成。
# 判定・出題は core.py をそのまま呼ぶ。
# タイマーも game.py と同じ挙動（tries==1 で start = time.time()）。
# ──────────────────────────────────────────────


@app.route("/")
def index():
    """ゲーム画面を表示。

    game.py の play() 冒頭に対応:
      secret = make_secret(digits)
      tries = 0
    """
    if "secret" not in session:
        # --- core.make_secret(digits) で答えを生成 (game.py L15) ---
        session["secret"] = make_secret(DIGITS)
        session["tries"] = 0
        session["start_time"] = None  # game.py: start は tries==1 でセット
    return render_template_string(HTML_TEMPLATE)


@app.route("/guess", methods=["POST"])
def guess():
    """ユーザーの予想を判定して JSON で返す。

    game.py の while ループ内のロジックをそのまま再現:
      1. バリデーション (game.py L32)
      2. タイマー開始   (game.py L29-30: if tries == 1: start = time.time())
      3. tries += 1     (game.py L35)
      4. judge()        (game.py L36: hit, blow = judge(secret, guess))
      5. 勝利判定       (game.py L38: if hit == digits)
      6. 所要時間       (game.py L40: end = time.time())
    """
    data = request.get_json()
    g = data.get("guess", "")

    # --- バリデーション: game.py L32 と同じ条件 ---
    # if len(guess) != digits or not guess.isdigit():
    if len(g) != DIGITS or not g.isdigit():
        return jsonify({"error": f"{DIGITS} 桁の数字で入力してね"})

    # 重複チェック（make_secret が重複なしなので GUI 側でも制約）
    if len(set(g)) != len(g):
        return jsonify({"error": "数字が重複しています"})

    secret = session.get("secret")
    if not secret:
        # セッション切れ時のフォールバック
        session["secret"] = make_secret(DIGITS)
        secret = session["secret"]
        session["tries"] = 0
        session["start_time"] = None

    # --- タイマー: game.py L29-30 ---
    # if tries == 1:
    #     start = time.time()
    if session.get("tries", 0) == 1:
        session["start_time"] = time.time()

    # --- tries += 1: game.py L35 ---
    session["tries"] = session.get("tries", 0) + 1

    # --- 判定: core.judge(secret, guess) → game.py L36 ---
    hit, blow = judge(secret, g)

    # --- 勝利判定: game.py L38 (if hit == digits) ---
    win = (hit == DIGITS)

    result = {
        "hit": hit,
        "blow": blow,
        "tries": session["tries"],
        "win": win,
    }

    if win:
        # --- 所要時間: game.py L40 (end = time.time()) ---
        end = time.time()
        start = session.get("start_time")
        if start is not None:
            elapsed = end - start
            result["elapsed"] = round(elapsed, 2)
        # game.py L43: 正解！ {tries} 回で当たり（答え {secret}）
        result["message"] = f"正解！ {session['tries']} 回で当たり（答え {secret}）"

    return jsonify(result)


@app.route("/new_game", methods=["POST"])
def new_game():
    """新しいゲームを開始。game.py の play() 冒頭と同じ初期化。"""
    session["secret"] = make_secret(DIGITS)
    session["tries"] = 0
    session["start_time"] = None
    return jsonify({"ok": True})


# ──────────────────────────────────────────────
# エントリーポイント
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print(f"  Hit & Blow GUI（{DIGITS} 桁・重複なし）")  # game.py L16 と同じ表示
    print("  http://127.0.0.1:5000 でプレイ！")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=True)
