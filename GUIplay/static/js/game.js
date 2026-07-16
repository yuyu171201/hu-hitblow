// ===== Config (mode-specific endpoints) =====
// index.html の <script> で定義。無ければ 1人プレイのデフォルト。
const CONFIG = window.GAME_CONFIG || {
  mode: 'solo', guessUrl: '/guess', itemUrl: '/item', newGameUrl: '/new_game',
};

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
    const res = await fetch(CONFIG.guessUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guess })
    });
    const data = await res.json();

    if (data.error) {
      showMessage(data.error);
      return;
    }

    // Update tries / lives
    document.getElementById('tries-count').textContent = data.tries;
    if (data.lives != null) updateLives(data.lives);

    // Add to history
    addHistory(data.tries, guess, data.hit, data.blow);

    // Check win
    if (data.win) {
      gameOver = true;
      clearInterval(timerInterval);
      // サーバー側で game.py と同じ time.time() で計算した所要時間を使用
      const elapsed = data.elapsed != null ? data.elapsed : ((Date.now() - startTime) / 1000).toFixed(1);
      // game.py L43 と同じメッセージ: 「正解！ {tries} 回で当たり（答え {secret}）」
      showVictory(data.tries, elapsed, guess, data.message, data.score, data.next_url);
    } else if (data.gameover) {
      // ライフ切れ → ゲームオーバー (game.py L75-76)
      gameOver = true;
      clearInterval(timerInterval);
      showGameOver(data.message, data.next_url);
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
function showVictory(tries, elapsed, answer, serverMessage, score, nextUrl) {
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
    // game.py L67: 基本所要時間: {base_time:.2f} 秒
    html += `所要時間: <strong>${elapsed}</strong> 秒<br>`;
  }
  if (score != null) {
    // game.py L71: ★ 最終スコア: {final_score:.2f}
    html += `★ 最終スコア: <strong>${score}</strong>`;
  }
  stats.innerHTML = html;
  applyEndButton('victory-btn', nextUrl);
  document.getElementById('victory-overlay').classList.add('show');
  launchConfetti();
}

// 対戦モードでは「もう一度遊ぶ」の代わりに次フェーズへ遷移させる。
function applyEndButton(btnId, nextUrl) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  if (CONFIG.mode === 'vs' && nextUrl) {
    btn.textContent = '次へ →';
    btn.onclick = () => { window.location.href = nextUrl; };
  }
}

// ===== Game Over =====
// game.py L76: ゲームオーバー... ライフが0になりました。（答えは {secret} でした）
function showGameOver(serverMessage, nextUrl) {
  document.getElementById('gameover-stats').innerHTML =
    serverMessage ? `<strong>${serverMessage}</strong>` : 'ライフが 0 になりました';
  applyEndButton('gameover-btn', nextUrl);
  document.getElementById('gameover-overlay').classList.add('show');
}

// ===== Lives =====
function updateLives(lives) {
  const el = document.getElementById('lives-count');
  el.textContent = lives;
  // 残り少なくなったら赤く警告
  el.classList.toggle('low', lives <= 3);
}

// ===== Items =====
// game.py の use_item() を呼び出す。1ゲーム1回のみ使用可能。
async function useItem(kind) {
  if (gameOver) return;
  try {
    const res = await fetch(CONFIG.itemUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind })
    });
    const data = await res.json();

    if (data.error) {
      showItemHint(data.error, true);
      return;
    }

    // どちらのアイテムも使用したら両方無効化（item_amount は 1→0）
    if (data.item_amount != null && data.item_amount <= 0) {
      document.getElementById('item-shuffle').disabled = true;
      document.getElementById('item-highlow').disabled = true;
    }
    showItemHint(`【アイテム使用】${data.message}`, false);
  } catch (err) {
    showItemHint('通信エラーが発生しました', true);
  }
}

function showItemHint(text, isError) {
  const el = document.getElementById('item-hint');
  el.textContent = text;
  el.className = 'item-hint show' + (isError ? ' error' : '');
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
  await fetch(CONFIG.newGameUrl, { method: 'POST' });
  document.getElementById('victory-overlay').classList.remove('show');
  document.getElementById('gameover-overlay').classList.remove('show');
  document.getElementById('history-list').innerHTML = '';
  document.getElementById('history-card').style.display = 'none';
  document.getElementById('tries-count').textContent = '0';
  document.getElementById('timer').textContent = '00:00';
  // ライフ・アイテムを初期状態に戻す
  updateLives(15);
  // アイテムは1人プレイのみ存在（対戦では非表示）
  const shuffleBtn = document.getElementById('item-shuffle');
  const highlowBtn = document.getElementById('item-highlow');
  if (shuffleBtn) shuffleBtn.disabled = false;
  if (highlowBtn) highlowBtn.disabled = false;
  const itemHint = document.getElementById('item-hint');
  if (itemHint) itemHint.className = 'item-hint';
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
