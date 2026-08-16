/* Завершение основного курса, история прохождений и отдельное обучение личному словарю. */
(function () {
  const apiBase = String(window.ENGLISH_API_URL || '').replace(/\/$/, '');
  let lastCourseFinished = false, personalMode = false, personalWords = [], personalPage = 0, personalTransition = null;
  const originalComplete = window.completeCurrentCard;
  const originalShowScreen = window.showScreen;
  const originalRecordAnswer = window.recordAnswer;

  window.showScreen = function (screenId) {
    if (screenId === 'complete' && personalTransition) {
      const destination = personalTransition;
      personalTransition = null;
      if (destination === 'next') return;
      return originalShowScreen('personalComplete');
    }
    if (screenId === 'complete' && lastCourseFinished) {
      lastCourseFinished = false;
      return originalShowScreen('courseComplete');
    }
    return originalShowScreen(screenId);
  };

  window.openTelegramBot = function () { window.location.href = 'telegram.html'; };

  window.restartMainCourse = async function () {
    if (!confirm('Начать новый курс? Статистика завершённого курса будет сохранена в истории.')) return;
    try {
      const response = await fetch(`${apiBase}/api/course/restart`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({chat_id})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Не удалось начать новый курс');
      stats = {correct:0, wrong:0}; personalMode = false; await startLearning();
    } catch (error) { alert(error.message); }
  };

  function renderPersonalBatch() {
    const batch = personalWords.slice(personalPage * 10, personalPage * 10 + 10);
    words = batch.map(w => ({en:w.en.trim(), ru:w.ru.trim()}));
    currentRound = 0; roundWords = []; matchedCount = 0; selectedWord = null; startRound();
  }

  window.startPersonalLearning = async function () {
    try {
      const response = await fetch(`${apiBase}/api/custom-words?chat_id=${encodeURIComponent(chat_id)}&all=1`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Не удалось загрузить личный словарь');
      personalWords = Array.isArray(data.items) ? data.items : [];
      if (!personalWords.length) { alert('Ваш личный словарь пока пуст. Сначала добавьте слова в разделе «Мой словарь».'); return; }
      personalMode = true; personalPage = 0; renderPersonalBatch();
    } catch (error) { alert(error.message); }
  };

  window.recordAnswer = function (isCorrect, wordEn) { return personalMode ? Promise.resolve() : originalRecordAnswer(isCorrect, wordEn); };

  window.completeCurrentCard = function () {
    if (personalMode) {
      personalPage += 1;
      if (personalPage * 10 >= personalWords.length) {
        personalMode = false; personalTransition = 'finished';
      } else {
        personalTransition = 'next'; renderPersonalBatch();
      }
      return Promise.resolve({finished:false, personal:true});
    }
    return originalComplete().then(data => { lastCourseFinished = Boolean(data.finished); return data; });
  };

  function escapeText(v){ const d=document.createElement('div'); d.textContent=String(v); return d.innerHTML; }
  function renderBars(target, items) {
    if (!target) return;
    if (!items.length) { target.innerHTML = '<div class="dictionary-empty">Сложных слов нет.</div>'; return; }
    const max = Math.max(...items.map(x => Number(x.mistakes || 0)), 1);
    target.innerHTML = items.slice(0,10).map(x => `<div class="hard-word-item"><div class="hard-word-heading"><span><strong>${escapeText(x.en)}</strong>${x.ru ? ' — '+escapeText(x.ru) : ''}</span><span>${Number(x.mistakes||0)}</span></div><div class="hard-word-track"><div class="hard-word-fill" style="width:${Math.max(7,Math.round(Number(x.mistakes||0)/max*100))}%"></div></div></div>`).join('');
  }

  const previousShowStats = window.showStats;
  window.showStats = async function () {
    await previousShowStats();
    try {
      const response = await fetch(`${apiBase}/api/course-history?chat_id=${encodeURIComponent(chat_id)}`); const data = await response.json();
      const box = document.getElementById('courseHistory'); const items = Array.isArray(data.items) ? data.items : [];
      box.innerHTML = items.length ? items.map((item,index) => `<button class="history-button" type="button" data-history-index="${index}">Статистика ${item.course_number}-го курса</button>`).join('') : '<div class="dictionary-empty">Завершённых прошлых курсов пока нет.</div>';
      box.querySelectorAll('[data-history-index]').forEach(btn => btn.onclick = () => showHistory(items[Number(btn.dataset.historyIndex)]));
    } catch(e) { console.error('История курса:', e); }
  };

  function showHistory(item) {
    document.getElementById('historyTitle').textContent = `Статистика ${item.course_number}-го курса`;
    document.getElementById('historySummary').innerHTML = `<div class="stat-item"><span>Правильно:</span><strong>${item.total_correct}</strong></div><div class="stat-item"><span>Неправильно:</span><strong>${item.total_wrong}</strong></div><div class="stat-item"><span>Точность:</span><strong>${item.accuracy}%</strong></div><div class="stat-item"><span>Лучшая серия:</span><strong>${item.best_streak}</strong></div>`;
    renderBars(document.getElementById('historyHardWords'), item.hard_word_stats || []); originalShowScreen('historyDetail');
  }
})();
