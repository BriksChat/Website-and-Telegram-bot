/* LearEnglish: автономное ядро без API, базы данных и Telegram. */
const STORAGE_KEY = 'learenglish-local-core-v3';
const ROUND_SIZE = 5;
const DICTIONARY_PAGE_SIZE = 10;
const cards = (window.LEARN_CARDS || []).filter((card) => Array.isArray(card.words) && card.words.length > 0);
const allWords = cards.flatMap((card) => card.words.map((word) => ({ ...word, cardId: card.id })));

let progress = loadProgress();
if (progress.personalWords.some((word) => !word.id)) {
  progress.personalWords = progress.personalWords.map((word, index) => ({ ...word, id: word.id || Date.now() + index }));
  saveProgress();
}
let cardWords = [];
let currentCard = null;
let currentRound = 0;
let roundWords = [];
let selectedWord = null;
let matchedInRound = 0;
let dictionaryMode = 'common';
let dictionaryPage = 1;
let demoStep = 0;

function initialProgress() {
  return { correct: 0, wrong: 0, completed: [], cardId: 1, mistakes: {}, personalWords: [], history: [] };
}
function loadProgress() {
  try { return { ...initialProgress(), ...JSON.parse(localStorage.getItem(STORAGE_KEY)) }; }
  catch { return initialProgress(); }
}
function saveProgress() { localStorage.setItem(STORAGE_KEY, JSON.stringify(progress)); }
function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
function shuffle(items) {
  const result = [...items];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [result[index], result[randomIndex]] = [result[randomIndex], result[index]];
  }
  return result;
}
function showScreen(id) {
  document.querySelectorAll('.screen').forEach((screen) => screen.classList.add('hidden'));
  document.getElementById(id)?.classList.remove('hidden');
}
function setFeedback(text, type = '') {
  const feedback = document.getElementById('feedback');
  feedback.textContent = text;
  feedback.className = `feedback ${type}`;
}
function clearFeedback() { setFeedback(''); }

function toggleBurgerMenu() {
  const menu = document.getElementById('burgerMenu');
  const overlay = document.getElementById('menuOverlay');
  const isOpen = menu.classList.toggle('open');
  overlay.classList.toggle('visible', isOpen);
  menu.setAttribute('aria-hidden', String(!isOpen));
}
function closeBurgerMenu() {
  document.getElementById('burgerMenu').classList.remove('open');
  document.getElementById('menuOverlay').classList.remove('visible');
  document.getElementById('burgerMenu').setAttribute('aria-hidden', 'true');
}
function openLearningFromMenu() { closeBurgerMenu(); startLearning(); }
function openDictionaryFromMenu() { closeBurgerMenu(); showCommonDictionary(); }
function openStatsFromMenu() { closeBurgerMenu(); showStats(); }
function openHelpFromMenu() { closeBurgerMenu(); showScreen('help'); }
function openDevInfoFromMenu() { closeBurgerMenu(); showScreen('dev-info'); }
function backToMenu() { startLearning(); }
function openTelegramBot() { alert('Telegram-бот подключается на пятом этапе. Локальное ядро работает без него.'); }

function localChatId() {
  let value = localStorage.getItem('learenglish-local-chat-id');
  if (!value) { value = String(Math.floor(100000000 + Math.random() * 900000000)); localStorage.setItem('learenglish-local-chat-id', value); }
  return value;
}
function changeChatId() {
  const value = prompt('Введите локальный Chat_ID:', localChatId());
  if (value && value.trim()) { localStorage.setItem('learenglish-local-chat-id', value.trim()); document.getElementById('currentChatId').textContent = value.trim(); }
}
function showIdHelp() { alert('В ядре Chat_ID локальный. После подключения API и Telegram он станет общим идентификатором прогресса.'); }

function startLearning() {
  if (progress.completed.length >= cards.length) { showScreen('courseComplete'); return; }
  currentCard = cards.find((card) => card.id === progress.cardId) || cards.find((card) => !progress.completed.includes(card.id)) || cards[0];
  progress.cardId = currentCard.id;
  cardWords = currentCard.words.map((word) => ({ en: word.en.trim(), ru: word.ru.trim() }));
  currentRound = 0;
  startRound();
}
function startRound() {
  const start = currentRound * ROUND_SIZE;
  roundWords = cardWords.slice(start, start + ROUND_SIZE);
  selectedWord = null;
  matchedInRound = 0;
  document.getElementById('currentRound').textContent = currentRound + 1;
  document.getElementById('totalRounds').textContent = Math.ceil(cardWords.length / ROUND_SIZE);
  document.getElementById('totalPairs').textContent = cardWords.length;
  renderBoard();
  clearFeedback();
  showScreen('matching');
}
function renderBoard() {
  const left = document.getElementById('leftColumn');
  const right = document.getElementById('rightColumn');
  left.replaceChildren(); right.replaceChildren();
  shuffle(roundWords).forEach((word) => left.appendChild(createWordButton(word, 'left')));
  shuffle(roundWords).forEach((word) => right.appendChild(createWordButton(word, 'right')));
  updatePairCounter();
}
function createWordButton(word, side) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'word-btn';
  button.textContent = side === 'left' ? word.ru : word.en;
  button.onclick = () => handleWordClick(button, word, side);
  return button;
}
function updatePairCounter() {
  const solvedInCard = currentRound * ROUND_SIZE + matchedInRound;
  const displayedPair = matchedInRound === 0 ? solvedInCard + 1 : solvedInCard;
  document.getElementById('currentPair').textContent = Math.min(displayedPair, cardWords.length);
}
function handleWordClick(button, word, side) {
  if (button.classList.contains('matched')) return;
  if (!selectedWord) {
    button.classList.add('selected');
    selectedWord = { button, word, side };
    setFeedback('Выбери пару →');
    return;
  }
  if (selectedWord.button === button) {
    button.classList.remove('selected'); selectedWord = null; clearFeedback(); return;
  }
  if (selectedWord.side === side) {
    selectedWord.button.classList.remove('selected'); button.classList.add('selected'); selectedWord = { button, word, side }; return;
  }
  if (selectedWord.word.en === word.en) {
    selectedWord.button.classList.remove('selected');
    selectedWord.button.classList.add('matched', 'disabled');
    button.classList.add('matched', 'disabled');
    progress.correct += 1;
    matchedInRound += 1;
    selectedWord = null;
    saveProgress();
    setFeedback('Верно! ✓', 'success');
    updatePairCounter();
    if (matchedInRound === roundWords.length) setTimeout(finishRound, 550);
  } else {
    progress.wrong += 1;
    const difficultWord = selectedWord.word.en;
    progress.mistakes[difficultWord] = (progress.mistakes[difficultWord] || 0) + 1;
    button.classList.add('wrong'); selectedWord.button.classList.add('wrong');
    const previous = selectedWord.button;
    selectedWord = null;
    saveProgress();
    setFeedback('Неверно, попробуй ещё', 'error');
    setTimeout(() => { button.classList.remove('wrong'); previous.classList.remove('wrong', 'selected'); }, 500);
  }
}
function finishRound() {
  if ((currentRound + 1) * ROUND_SIZE < cardWords.length) {
    const transition = document.getElementById('roundTransition');
    transition.classList.remove('hidden');
    setTimeout(() => { transition.classList.add('hidden'); currentRound += 1; startRound(); }, 1000);
    return;
  }
  showCardCompleteOverlay(() => completeCurrentCard());
}
function showCardCompleteOverlay(after) {
  const overlay = document.getElementById('cardCompleteOverlay');
  overlay.classList.remove('hidden');
  setTimeout(() => { overlay.classList.add('hidden'); after(); }, 900);
}
function completeCurrentCard() {
  if (!progress.completed.includes(currentCard.id)) progress.completed.push(currentCard.id);
  const next = cards.find((card) => !progress.completed.includes(card.id));
  progress.cardId = next ? next.id : cards[0].id;
  if (!next) {
    progress.history.push({ number: progress.history.length + 1, correct: progress.correct, wrong: progress.wrong, completedAt: new Date().toLocaleDateString('ru-RU'), mistakes: { ...progress.mistakes } });
  }
  saveProgress();
  showScreen('complete');
}
function restartMainCourse() {
  progress.completed = [];
  progress.cardId = cards[0].id;
  progress.correct = 0;
  progress.wrong = 0;
  progress.mistakes = {};
  saveProgress();
  startLearning();
}
function startPersonalLearning() { showPersonalDictionary(); }

function showStats() {
  const total = progress.correct + progress.wrong;
  document.getElementById('statCorrect').textContent = progress.correct;
  document.getElementById('statWrong').textContent = progress.wrong;
  document.getElementById('statAccuracy').textContent = `${total ? Math.round(progress.correct / total * 100) : 0}%`;
  const hard = Object.entries(progress.mistakes).sort((first, second) => second[1] - first[1]);
  const maxMistakes = hard.length ? Math.max(...hard.map(([, count]) => count), 1) : 1;
  document.getElementById('hardWordBars').innerHTML = hard.length
    ? hard.slice(0, 10).map(([word, count]) => `<div class="hard-word-item">
        <div class="hard-word-heading"><span class="hard-word-name"><strong>${escapeHtml(word)}</strong></span><span class="hard-word-count">${count}</span></div>
        <div class="hard-word-track" aria-label="Ошибок: ${count}"><div class="hard-word-fill" style="width:${Math.max(7, Math.round(count / maxMistakes * 100))}%"></div></div>
      </div>`).join('')
    : '<div class="dictionary-empty">Сложных слов пока нет.</div>';
  const history = document.getElementById('courseHistory');
  history.innerHTML = progress.history.length
    ? progress.history.map((item, index) => `<button class="history-card" type="button" onclick="showHistoryDetail(${index})">Курс ${item.number} · ${item.completedAt}</button>`).join('')
    : `<div class="dictionary-loading">Пройдено карточек: ${progress.completed.length} из ${cards.length}</div>`;
  showScreen('stats');
}
function showHistoryDetail(index) {
  const item = progress.history[index];
  if (!item) return;
  document.getElementById('historyTitle').textContent = `Статистика курса ${item.number}`;
  document.getElementById('historySummary').innerHTML = `<div class="stat-item"><span>Правильно:</span><strong>${item.correct}</strong></div><div class="stat-item"><span>Неправильно:</span><strong>${item.wrong}</strong></div>`;
  const hard = Object.entries(item.mistakes || {}).sort((first, second) => second[1] - first[1]);
  document.getElementById('historyHardWords').innerHTML = hard.length ? hard.map(([word, count]) => `<div class="hard-word-row"><span>${word}</span><strong>${count}</strong></div>`).join('') : '<p>Сложных слов нет.</p>';
  showScreen('historyDetail');
}

function currentDictionaryWords() { return dictionaryMode === 'common' ? allWords : progress.personalWords; }
function renderDictionary() {
  const items = currentDictionaryWords();
  const pages = Math.max(1, Math.ceil(items.length / DICTIONARY_PAGE_SIZE));
  dictionaryPage = Math.min(Math.max(dictionaryPage, 1), pages);
  const visible = items.slice((dictionaryPage - 1) * DICTIONARY_PAGE_SIZE, dictionaryPage * DICTIONARY_PAGE_SIZE);
  document.getElementById('dictionaryList').innerHTML = visible.length
    ? visible.map((word, index) => {
      const wordId = word.id || `${dictionaryPage}-${index}`;
      const cardNumber = dictionaryMode === 'common' ? `<small class="dictionary-card-number">Карточка ${Number(word.cardId)}</small>` : '';
      const actions = dictionaryMode === 'personal' ? `<div class="dictionary-actions">
          <button class="dictionary-action" type="button" data-edit-word="${wordId}" aria-label="Редактировать">✏️</button>
          <button class="dictionary-action delete" type="button" data-delete-word="${wordId}" aria-label="Удалить">🗑</button>
        </div>` : '';
      return `<div class="dictionary-row" data-word-id="${wordId}">
        <div class="dictionary-word"><strong>${escapeHtml(word.en)}</strong> <span>— ${escapeHtml(word.ru)}</span>${cardNumber}</div>
        ${actions}
      </div>`;
    }).join('')
    : `<div class="dictionary-empty">${dictionaryMode === 'common' ? 'В общем словаре пока нет слов.' : 'Личный словарь пуст. Добавьте первую пару слов.'}</div>`;
  document.getElementById('dictionaryPageLabel').textContent = `Страница ${dictionaryPage} из ${pages}`;
  document.getElementById('dictionaryPrev').disabled = dictionaryPage <= 1;
  document.getElementById('dictionaryNext').disabled = dictionaryPage >= pages;
}
function showCommonDictionary() {
  dictionaryMode = 'common'; dictionaryPage = 1;
  document.getElementById('dictionaryCommonTab').classList.add('active');
  document.getElementById('dictionaryPersonalTab').classList.remove('active');
  document.getElementById('dictionaryNote').textContent = 'Общий словарь доступен только для просмотра. Пользователи не могут изменять эти слова.';
  document.getElementById('personalWordForm').classList.add('hidden');
  renderDictionary(); showScreen('dictionary');
}
function showPersonalDictionary() {
  dictionaryMode = 'personal'; dictionaryPage = 1;
  document.getElementById('dictionaryCommonTab').classList.remove('active');
  document.getElementById('dictionaryPersonalTab').classList.add('active');
  document.getElementById('dictionaryNote').textContent = 'Здесь находятся ваши личные пары слов. В ядре они сохраняются только в этом браузере.';
  document.getElementById('personalWordForm').classList.remove('hidden');
  renderDictionary(); showScreen('dictionary');
}

function showLearningDemo() { document.getElementById('learningDemo').classList.remove('hidden'); updateLearningDemo(); }
function updateLearningDemo() {
  const titles = ['Как собрать пару?', 'Теперь выберите перевод', 'Готово!'];
  const texts = ['Сначала нажмите на русское слово.', 'Затем нажмите на подходящее английское слово.', 'Правильная пара подсветится.'];
  document.getElementById('demoTitle').textContent = titles[demoStep];
  document.getElementById('demoText').textContent = texts[demoStep];
  document.querySelectorAll('.demo-step').forEach((item, index) => item.classList.toggle('active', index === demoStep));
  document.getElementById('demoNextButton').textContent = demoStep === 2 ? 'Начать' : 'Далее';
}
function nextLearningDemoStep() { if (demoStep < 2) { demoStep += 1; updateLearningDemo(); } else finishLearningDemo(); }
function finishLearningDemo() { localStorage.setItem('learenglish-demo-seen', '1'); document.getElementById('learningDemo').classList.add('hidden'); }
function closeLearningDemo() { finishLearningDemo(); }

document.getElementById('dictionaryPrev').addEventListener('click', () => { dictionaryPage -= 1; renderDictionary(); });
document.getElementById('dictionaryNext').addEventListener('click', () => { dictionaryPage += 1; renderDictionary(); });
document.getElementById('personalWordForm').addEventListener('submit', (event) => {
  event.preventDefault();
  const en = document.getElementById('personalWordEn').value.trim();
  const ru = document.getElementById('personalWordRu').value.trim();
  if (!en || !ru) return;
  progress.personalWords.push({ id: Date.now(), en, ru });
  saveProgress(); event.target.reset(); renderDictionary();
});

document.getElementById('dictionaryList').addEventListener('click', (event) => {
  if (dictionaryMode !== 'personal') return;
  const editButton = event.target.closest('[data-edit-word]');
  const deleteButton = event.target.closest('[data-delete-word]');
  const row = event.target.closest('.dictionary-row');
  if (!row || (!editButton && !deleteButton)) return;
  const index = progress.personalWords.findIndex((word) => String(word.id) === row.dataset.wordId);
  if (index < 0) return;
  if (editButton) {
    const en = prompt('Английское слово:', progress.personalWords[index].en);
    if (en === null) return;
    const ru = prompt('Перевод:', progress.personalWords[index].ru);
    if (ru === null || !en.trim() || !ru.trim()) return;
    progress.personalWords[index] = { ...progress.personalWords[index], en: en.trim(), ru: ru.trim() };
  }
  if (deleteButton && !confirm(`Удалить слово «${progress.personalWords[index].en}»?`)) return;
  if (deleteButton) progress.personalWords.splice(index, 1);
  saveProgress(); renderDictionary();
});

document.getElementById('loading').classList.add('hidden');
document.getElementById('currentChatId').textContent = localChatId();
startLearning();
if (localStorage.getItem('learenglish-demo-seen') !== '1') showLearningDemo();
