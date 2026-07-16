// ===== 対戦（ネットワーク）クライアント =====
// サーバー側 vs_store の状態を /vs/state でポーリングし、
// 自分の手番のときだけ入力できるようにする。

const PID = sessionStorage.getItem('vs_pid');
if (!PID) {
  // pid が無い（直接 /vs/play を開いた等）→ ロビーへ
  window.location.href = '/vs';
}

// ===== 入力状態 =====
let selectedSlot = 0;
const digits = [null, null, null];
let myTurn = false;        // 今、自分の手番か
let finished = false;      // 対戦終了したか
let pollTimer = null;

// ===== スロット選択 =====
function selectSlot(index) {
  if (!myTurn) return;
  selectedSlot = index;
  document.querySelectorAll('.slot').forEach((s, i) => {
    s.classList.toggle('selected', i === index);
  });
}

// ===== 数字入力 =====
function inputDigit(d) {
  if (!myTurn) return;
  hideMessage();

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
  slot.style.transform = 'scale(1.1)';
  setTimeout(() => { slot.style.transform = ''; }, 150);

  let next = -1;
  for (let offset = 1; offset <= 3; offset++) {
    const idx = (selectedSlot + offset) % 3;
    if (digits[idx] === null) { next = idx; break; }
  }
  if (next !== -1) selectSlot(next);

  updateUsedDigits();
  updateSubmitButton();
}

function updateUsedDigits() {
  document.querySelectorAll('.num-btn').forEach(btn => {
    const d = btn.textContent;
    btn.classList.toggle('used', digits.includes(d));
  });
}

function updateSubmitButton() {
  const allFilled = digits.every(d => d !== null);
  document.getElementById('submit-btn').disabled = !allFilled || !myTurn;
}

function clearSlots() {
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

function showMessage(text) {
  const msg = document.getElementById('message');
  msg.textContent = text;
  msg.className = 'message error';
}
function hideMessage() {
  document.getElementById('message').className = 'message';
}

// ===== 予想を送信 =====
async function submitGuess() {
  if (!myTurn) return;
  const guess = digits.join('');
  if (guess.length !== 3 || digits.includes(null)) return;

  try {
    const res = await fetch('/vs/guess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pid: PID, guess }),
    });
    const data = await res.json();
    if (data.error) { showMessage(data.error); return; }
    clearSlots();
    render(data);
  } catch (e) {
    showMessage('通信エラーが発生しました');
  }
}

// ===== アイテム（High/Low ヒント・自分のみ） =====
async function useItem() {
  try {
    const res = await fetch('/vs/item', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pid: PID }),
    });
    const data = await res.json();
    if (data.error) {
      const el = document.getElementById('item-hint');
      el.textContent = data.error;
      el.className = 'item-hint show error';
      return;
    }
    render(data);
  } catch (e) {
    // 通信エラーは次のポーリングで復帰
  }
}

// ===== ポーリング =====
async function poll() {
  try {
    const res = await fetch('/vs/state?pid=' + encodeURIComponent(PID));
    const data = await res.json();
    if (data.error) return;
    render(data);
  } catch (e) {
    // 一時的な失敗は無視（次回リトライ）
  }
}

// ===== 描画 =====
function render(s) {
  const banner = document.getElementById('banner');
  const itemCard = document.getElementById('item-card');
  const inputCard = document.getElementById('input-card');

  // 手番フラグ更新（入力欄の DOM は消さない＝入力途中を保持）
  myTurn = (s.status === 'playing' && s.your_turn);

  // 盤面（両者の履歴）
  renderBoards(s);

  if (s.status === 'waiting') {
    banner.textContent = '相手を待っています…';
    banner.className = 'vs-banner waiting';
    itemCard.style.display = 'none';
    inputCard.style.display = 'none';
  } else if (s.status === 'playing') {
    itemCard.style.display = '';
    inputCard.style.display = '';
    if (myTurn) {
      banner.textContent = 'あなたの番です！予想を入力してください';
      banner.className = 'vs-banner your-turn';
      inputCard.classList.remove('locked');
    } else {
      banner.textContent = '相手の番です…（待機中）';
      banner.className = 'vs-banner wait-turn';
      inputCard.classList.add('locked');
    }
    // アイテムボタン
    const itemBtn = document.getElementById('item-highlow');
    itemBtn.disabled = !!s.you.item_used;
    // 自分のヒント表示
    if (s.you.hint) {
      const el = document.getElementById('item-hint');
      el.textContent = '各桁の大小: ' + s.you.hint.join(', ');
      el.className = 'item-hint show';
    }
    updateSubmitButton();
  } else if (s.status === 'finished') {
    banner.textContent = '対戦終了';
    banner.className = 'vs-banner';
    itemCard.style.display = 'none';
    inputCard.style.display = 'none';
    showResult(s);
  }
}

function renderBoards(s) {
  const boards = document.getElementById('boards');
  const you = s.your_index;
  let html = '';
  s.players.forEach((p, i) => {
    const isYou = i === you;
    const isTurn = s.status === 'playing' && s.turn === i;
    const rows = p.guesses.map(g => `
      <li class="vs-row">
        <span class="history-guess">${g.guess.split('').join(' ')}</span>
        <span class="history-result">
          <span class="badge badge-hit">H ${g.hit}</span>
          <span class="badge badge-blow">B ${g.blow}</span>
        </span>
      </li>`).join('');
    html += `
      <div class="vs-board ${isTurn ? 'active' : ''} ${p.solved ? 'solved' : ''}">
        <div class="vs-name">
          ${p.name}${isYou ? '（あなた）' : ''}
          ${isTurn ? '<span class="turn-dot">●</span>' : ''}
        </div>
        <ul class="vs-history">${rows || '<li class="vs-empty">まだ予想なし</li>'}</ul>
      </div>`;
  });
  // 対戦相手がまだ来ていない場合のプレースホルダ
  if (s.players.length < 2) {
    html += `
      <div class="vs-board">
        <div class="vs-name">? ?（募集中）</div>
        <ul class="vs-history"><li class="vs-empty">参加待ち…</li></ul>
      </div>`;
  }
  boards.innerHTML = html;
}

// ===== 結果 =====
function showResult(s) {
  if (finished) return;   // 二重表示を防ぐ
  finished = true;
  if (pollTimer) clearInterval(pollTimer);

  const iWon = s.winner === s.your_index;
  document.getElementById('result-emoji').textContent = iWon ? '🏆' : '😢';
  document.getElementById('result-title').textContent = iWon ? '勝利！' : '敗北…';
  const winnerName = s.winner_name || '';
  let html = `<strong>${winnerName}</strong> が先に 3HIT で勝ち！<br>`;
  if (s.secret) html += `答え: <strong>${s.secret}</strong>`;
  document.getElementById('result-stats').innerHTML = html;

  const card = document.getElementById('result-card');
  card.classList.toggle('lose', !iWon);
  document.getElementById('result-overlay').classList.add('show');
  if (iWon) launchConfetti();
}

// ===== 紙吹雪（勝利時） =====
function launchConfetti() {
  const colors = ['#6c63ff', '#ff6b9d', '#51cf66', '#ffd43b', '#4ecdc4', '#ff6b6b'];
  let container = document.getElementById('confetti-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'confetti-container';
    container.id = 'confetti-container';
    document.body.appendChild(container);
  }
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

// ===== キーボード =====
document.addEventListener('keydown', (e) => {
  if (!myTurn) return;
  if (e.key >= '0' && e.key <= '9') {
    inputDigit(e.key);
  } else if (e.key === 'Backspace') {
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

// ===== 起動 =====
if (PID) {
  poll();
  pollTimer = setInterval(poll, 1000);
}
