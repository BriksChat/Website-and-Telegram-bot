// Единственная точка доступа к данным — REST API проекта.
const API_BASE_URL = String(window.ENGLISH_API_URL || '').replace(/\/$/, '');
const LOCAL_API = /^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/i.test(API_BASE_URL);
if (!API_BASE_URL.startsWith('https://') && !LOCAL_API) {
  throw new Error('В config.js укажите локальный HTTP-адрес или публичный HTTPS-адрес API');
}

let words = [];

const ROUND_SIZE = 5;
const TRANSITION_DELAY_MS = 1500;
const NEXT_ROUND_DELAY_MS = 700;

// Статистика
let stats = { correct: 0, wrong: 0 };
let chat_id = '';
let syncQueue = Promise.resolve();

// Состояние раунда
let currentRound = 0;
let roundWords = [];
let selectedWord = null;   // { el, word, side } — универсальный выбор
let matchedCount = 0;

// ===== ГЕНЕРАЦИЯ CHATID =====
function generateChatId() {
  const randomDigits = Math.floor(10000000 + Math.random() * 90000000);
  return 'Persona' + randomDigits;
}

// ===== ЗАГРУЗКА/СОХРАНЕНИЕ ПРОГРЕССА =====
function requestChatId() {
  const saved = localStorage.getItem('chat_id');
  chat_id = saved || generateChatId();

  if (!saved) {
    localStorage.setItem('chat_id', chat_id);
  }

  document.getElementById('currentChatId').textContent = chat_id;
  loadProgress();
}

function loadProgress() {
  return fetch(`${API_BASE_URL}/api/progress?chat_id=${encodeURIComponent(chat_id)}`)
    .then(response => {
      if (!response.ok) throw new Error(`API вернул ${response.status}`);
      return response.json();
    })
    .then(data => {
      stats = { correct: data.total_correct, wrong: data.total_wrong };
      console.log('✅ Прогресс загружен из общей базы:', stats);
    })
    .catch(err => console.error('Ошибка загрузки прогресса:', err));
}

function recordAnswer(isCorrect, wordEn) {
  syncQueue = syncQueue.then(() => fetch(`${API_BASE_URL}/api/check-answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id, word_en: wordEn, is_correct: isCorrect })
  }))
    .then(response => {
      if (!response.ok) throw new Error(`API вернул ${response.status}`);
      return response.json();
    })
    .then(data => {
      stats = { correct: data.total_correct, wrong: data.total_wrong };
    })
    .catch(err => console.error('Ошибка синхронизации ответа:', err));
  return syncQueue;
}

function completeCurrentCard() {
  syncQueue = syncQueue.then(() => fetch(`${API_BASE_URL}/api/complete-card`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id })
  })).then(response => {
    if (!response.ok) throw new Error(`API вернул ${response.status}`);
    return response.json();
  });
  return syncQueue;
}

function saveProgress() {
  fetch(`${API_BASE_URL}/api/progress`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id,
      total_correct: stats.correct,
      total_wrong: stats.wrong
    })
  })
    .then(response => {
      if (!response.ok) throw new Error(`API вернул ${response.status}`);
      return response.json();
    })
    .catch(err => console.error('Ошибка сохранения прогресса:', err));
}

// ===== Смена ChatID =====
function changeChatId() {
  const newId = prompt('Введи новый Chat_ID:', chat_id);
  if (newId === null) return;
  const trimmed = newId.trim();
  if (trimmed.length < 5) {
    alert('Chat_ID должен содержать минимум 5 символов!');
    return;
  }
  if (trimmed === chat_id) {
    alert('Это тот же Chat_ID. Изменений нет.');
    return;
  }
  const confirmChange = window.confirm(
    `⚠️ ВНИМАНИЕ!\n\n` +
    `Сменить Chat_ID с "${chat_id}" на "${trimmed}"?\n\n` +
    `Прогресс для старого Chat_ID будет недоступен.\n` +
    `Убедитесь, что вы сохранили старый Chat_ID!\n\n` +
    `Продолжить?`
  );
  if (!confirmChange) return;
  chat_id = trimmed;
  localStorage.setItem('chat_id', chat_id);
  document.getElementById('currentChatId').textContent = chat_id;
  loadProgress();
  alert(`✅ Chat_ID изменён на "${chat_id}"`);
}

function copyChatId() {
  navigator.clipboard.writeText(chat_id).then(() => {
    alert(`✅ ChatID скопирован: ${chat_id}`);
  }).catch(() => {
    const textArea = document.createElement('textarea');
    textArea.value = chat_id;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    alert(`✅ ChatID скопирован: ${chat_id}`);
  });
}

function showIdHelp() {
    alert(
    '❓ Что такое ChatID?\n\n' +
    'ChatID — это ваш уникальный идентификатор, к которому привязан прогресс обучения.\n\n' +
    '📌 Запомните или сохраните его — при утере вы потеряете статистику.\n\n' +
    '✏️ Изменить ChatID можно, нажав на карандаш рядом.\n'
    );
}

// ===== ПЕРЕКЛЮЧЕНИЕ ЭКРАНОВ =====
function showScreen(screenId) {
  document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
  document.getElementById(screenId).classList.remove('hidden');
}
function backToMenu() {
  showScreen('menu');
}

function openTelegramBot() {
  window.open(window.TELEGRAM_BOT_URL || 'https://t.me/YOUR_BOT_USERNAME', '_blank', 'noopener');
}

// ===== СТАРТ ОБУЧЕНИЯ =====
async function startLearning() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/current-card?chat_id=${encodeURIComponent(chat_id)}`);
    if (!response.ok) throw new Error(`API вернул ${response.status}`);
    const data = await response.json();
    if (data.finished) {
      showScreen('complete');
      return;
    }
    words = data.card.words.map(word => ({ en: word.en.trim(), ru: word.ru.trim() }));
    currentRound = 0;
    startRound();
  } catch (error) {
    console.error('Ошибка загрузки карточки:', error);
    alert('Не удалось загрузить карточку. Проверьте соединение с API Amvera.');
  }
}

function startRound() {
  const start = currentRound * ROUND_SIZE;
  roundWords = words.slice(start, start + ROUND_SIZE);
  matchedCount = 0;
  selectedWord = null;
  document.getElementById('currentRound').textContent = currentRound + 1;
  document.getElementById('totalPairs').textContent = words.length;
  document.getElementById('totalRounds').textContent = Math.ceil(words.length / ROUND_SIZE);
  renderBoard();
  showScreen('matching');
  clearFeedback();
}

// ===== ОТРИСОВКА ДОСКИ =====
function renderBoard() {
  const leftCol = document.getElementById('leftColumn');
  const rightCol = document.getElementById('rightColumn');
  leftCol.innerHTML = '';
  rightCol.innerHTML = '';

  const leftWords = shuffle([...roundWords]);
  const rightWords = shuffle([...roundWords]);

  leftWords.forEach(w => {
    const btn = document.createElement('button');
    btn.className = 'word-btn';
    btn.textContent = w.ru;
    btn.dataset.en = w.en;
    btn.dataset.side = 'left';
    btn.onclick = () => handleWordClick(btn, w, 'left');
    leftCol.appendChild(btn);
  });

  rightWords.forEach(w => {
    const btn = document.createElement('button');
    btn.className = 'word-btn';
    btn.textContent = w.en;
    btn.dataset.en = w.en;
    btn.dataset.side = 'right';
    btn.onclick = () => handleWordClick(btn, w, 'right');
    rightCol.appendChild(btn);
  });

  updatePairCounter();
}

function updatePairCounter() {
  const totalInRound = matchedCount + (currentRound * ROUND_SIZE);
  document.getElementById('currentPair').textContent = totalInRound;
}

// ===== УНИВЕРСАЛЬНЫЙ КЛИК ПО СЛОВУ (любая колонка) =====
function handleWordClick(btn, word, side) {
  // Уже собранная пара — игнор
  if (btn.classList.contains('matched')) return;

  // 1) Ничего не выбрано → выбираем эту кнопку
  if (!selectedWord) {
    btn.classList.add('selected');
    selectedWord = { el: btn, word, side };
    setFeedback('Выбери пару →', '');
    return;
  }

  // 2) Нажали ту же самую кнопку → снимаем выбор
  if (selectedWord.el === btn) {
    btn.classList.remove('selected');
    selectedWord = null;
    clearFeedback();
    return;
  }

  // 3) Нажали кнопку с той же стороны → переключаем выбор
  if (selectedWord.side === side) {
    selectedWord.el.classList.remove('selected');
    btn.classList.add('selected');
    selectedWord = { el: btn, word, side };
    return;
  }

  // 4) Нажали кнопку с ДРУГОЙ стороны → проверяем пару
  if (selectedWord.word.en === word.en) {
    // ✅ Верно
    selectedWord.el.classList.remove('selected');
    selectedWord.el.classList.add('matched', 'disabled');
    btn.classList.add('matched', 'disabled');
    stats.correct++;
    matchedCount++;
    setFeedback('Верно! ✓', 'success');
    selectedWord = null;
    updatePairCounter();
    recordAnswer(true, word.en);

    if (matchedCount === roundWords.length) {
     setTimeout(() => {
         const nextStart = (currentRound + 1) * ROUND_SIZE;
        if (nextStart < words.length) {
          // Показываем экран перехода между раундами
          const transition = document.getElementById('roundTransition');
             if (transition) {
             transition.classList.remove('hidden');
             setTimeout(() => {
             transition.classList.add('hidden');
             currentRound++;
             startRound();
             }, TRANSITION_DELAY_MS);
            } else {
             currentRound++;
             startRound();
            }
        } else {
         completeCurrentCard()
           .then(() => showScreen('complete'))
           .catch(error => {
             console.error('Ошибка завершения карточки:', error);
             showScreen('complete');
           });
        }
     }, NEXT_ROUND_DELAY_MS);
    }
  } else {
    // ❌ Неверно
    stats.wrong++;
    btn.classList.add('wrong');
    selectedWord.el.classList.add('wrong');
    setFeedback('Неверно, попробуй ещё', 'error');

    const wrongBtn = btn;
    const wrongPrev = selectedWord.el;
    setTimeout(() => {
      wrongBtn.classList.remove('wrong');
      wrongPrev.classList.remove('wrong', 'selected');
    }, 500);
    selectedWord = null;
    recordAnswer(false, word.en);
  }
}

// ===== УТИЛИТЫ =====
function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function setFeedback(text, type) {
  const fb = document.getElementById('feedback');
  fb.textContent = text;
  fb.className = 'feedback ' + (type || '');
}

function clearFeedback() {
  const fb = document.getElementById('feedback');
  fb.textContent = '';
  fb.className = 'feedback';
}

// ===== СТАТИСТИКА =====
function showStats() {
  const total = stats.correct + stats.wrong;
  const accuracy = total > 0 ? Math.round((stats.correct / total) * 100) : 0;
  document.getElementById('statCorrect').textContent = stats.correct;
  document.getElementById('statWrong').textContent = stats.wrong;
  document.getElementById('statAccuracy').textContent = accuracy + '%';
  showScreen('stats');
}

function resetStats() {
if (!confirm('⚠️ Вы уверены, что хотите сбросить статистику?\n\nЭто действие нельзя отменить.')) return;
stats = { correct: 0, wrong: 0 };
saveProgress();
showStats();
}

// ===== ЗАПУСК =====
requestChatId();
