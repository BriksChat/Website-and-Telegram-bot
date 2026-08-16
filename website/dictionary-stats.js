/*
 * Общий словарь доступен только для чтения.
 * Личные пары слов и статистика ошибок всегда запрашиваются по текущему ChatID.
 */
(function initialiseDictionaryAndStats() {
  const apiBase = String(window.ENGLISH_API_URL || '').replace(/\/$/, '');
  const list = document.getElementById('dictionaryList');
  const note = document.getElementById('dictionaryNote');
  const pageLabel = document.getElementById('dictionaryPageLabel');
  const prevButton = document.getElementById('dictionaryPrev');
  const nextButton = document.getElementById('dictionaryNext');
  const commonTab = document.getElementById('dictionaryCommonTab');
  const personalTab = document.getElementById('dictionaryPersonalTab');
  const personalForm = document.getElementById('personalWordForm');
  const personalEn = document.getElementById('personalWordEn');
  const personalRu = document.getElementById('personalWordRu');
  const hardWordBars = document.getElementById('hardWordBars');

  let mode = 'common';
  let page = 1;
  let totalPages = 1;

  function currentChatId() {
    return typeof chat_id === 'string' ? chat_id : '';
  }

  async function apiRequest(path, options = {}) {
    const response = await fetch(`${apiBase}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.message || `Ошибка API: ${response.status}`);
    }
    return data;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function updateTabs() {
    commonTab?.classList.toggle('active', mode === 'common');
    personalTab?.classList.toggle('active', mode === 'personal');
    personalForm?.classList.toggle('hidden', mode !== 'personal');
    if (note) {
      note.textContent = mode === 'common'
        ? 'Общий словарь доступен только для просмотра. Пользователи не могут изменять эти слова.'
        : 'Здесь находятся только ваши личные пары слов, привязанные к текущему ChatID.';
    }
  }

  function renderRows(items) {
    if (!list) return;
    if (!items.length) {
      list.innerHTML = `<div class="dictionary-empty">${
        mode === 'common' ? 'В общем словаре пока нет слов.' : 'Личный словарь пуст. Добавьте первую пару слов.'
      }</div>`;
      return;
    }

    list.innerHTML = items.map(item => {
      const actions = mode === 'personal'
        ? `<div class="dictionary-actions">
            <button class="dictionary-action" type="button" data-edit-word="${item.id}" aria-label="Редактировать">✏️</button>
            <button class="dictionary-action delete" type="button" data-delete-word="${item.id}" aria-label="Удалить">🗑</button>
          </div>`
        : '';
      const cardNumber = mode === 'common'
        ? `<small class="dictionary-card-number">Карточка ${Number(item.card_id)}</small>`
        : '';
      return `<div class="dictionary-row" data-word-id="${item.id}">
        <div class="dictionary-word">
          <strong>${escapeHtml(item.en)}</strong> <span>— ${escapeHtml(item.ru)}</span>
          ${cardNumber}
        </div>
        ${actions}
      </div>`;
    }).join('');
  }

  function updatePagination(data) {
    page = Number(data.page || 1);
    totalPages = Number(data.total_pages || 1);
    if (pageLabel) pageLabel.textContent = `Страница ${page} из ${totalPages}`;
    if (prevButton) prevButton.disabled = page <= 1;
    if (nextButton) nextButton.disabled = page >= totalPages;
  }

  async function loadDictionary() {
    updateTabs();
    if (list) list.innerHTML = '<div class="dictionary-loading">Загружаем слова…</div>';

    try {
      const path = mode === 'common'
        ? `/api/dictionary?page=${page}&per_page=10`
        : `/api/custom-words?chat_id=${encodeURIComponent(currentChatId())}&page=${page}&per_page=10`;
      const data = await apiRequest(path);
      renderRows(Array.isArray(data.items) ? data.items : []);
      updatePagination(data);
    } catch (error) {
      if (list) list.innerHTML = `<div class="dictionary-empty">${escapeHtml(error.message)}</div>`;
    }
  }

  window.openDictionaryFromMenu = function openDictionaryFromMenu() {
    if (typeof closeBurgerMenu === 'function') closeBurgerMenu();
    showScreen('dictionary');
    loadDictionary();
  };

  window.showCommonDictionary = function showCommonDictionary() {
    mode = 'common';
    page = 1;
    loadDictionary();
  };

  window.showPersonalDictionary = function showPersonalDictionary() {
    mode = 'personal';
    page = 1;
    loadDictionary();
  };

  prevButton?.addEventListener('click', () => {
    if (page > 1) {
      page -= 1;
      loadDictionary();
    }
  });

  nextButton?.addEventListener('click', () => {
    if (page < totalPages) {
      page += 1;
      loadDictionary();
    }
  });

  personalForm?.addEventListener('submit', async event => {
    event.preventDefault();
    const en = personalEn.value.trim();
    const ru = personalRu.value.trim();
    if (!en || !ru) return;

    try {
      await apiRequest('/api/custom-words', {
        method: 'POST',
        body: JSON.stringify({ chat_id: currentChatId(), en, ru }),
      });
      personalEn.value = '';
      personalRu.value = '';
      page = 1;
      await loadDictionary();
    } catch (error) {
      alert(error.message);
    }
  });

  list?.addEventListener('click', async event => {
    const editButton = event.target.closest('[data-edit-word]');
    const deleteButton = event.target.closest('[data-delete-word]');
    const row = event.target.closest('.dictionary-row');
    if (!row || mode !== 'personal') return;

    const wordId = Number(row.dataset.wordId);
    const text = row.querySelector('.dictionary-word')?.innerText || '';
    const [currentEn = '', currentRu = ''] = text.split('—').map(part => part.trim());

    if (editButton) {
      const en = prompt('Английское слово:', currentEn);
      if (en === null) return;
      const ru = prompt('Перевод:', currentRu);
      if (ru === null) return;
      if (!en.trim() || !ru.trim()) {
        alert('Заполните оба поля.');
        return;
      }
      try {
        await apiRequest(`/api/custom-word/${wordId}`, {
          method: 'PATCH',
          body: JSON.stringify({ chat_id: currentChatId(), en: en.trim(), ru: ru.trim() }),
        });
        await loadDictionary();
      } catch (error) {
        alert(error.message);
      }
    }

    if (deleteButton && confirm('Удалить эту личную пару слов?')) {
      try {
        await apiRequest(`/api/custom-word/${wordId}?chat_id=${encodeURIComponent(currentChatId())}`, {
          method: 'DELETE',
        });
        await loadDictionary();
      } catch (error) {
        alert(error.message);
      }
    }
  });

  function renderHardWordBars(items) {
    if (!hardWordBars) return;
    if (!items.length) {
      hardWordBars.innerHTML = '<div class="dictionary-empty">Сложных слов пока нет.</div>';
      return;
    }

    const topItems = items.slice(0, 10);
    const maxMistakes = Math.max(...topItems.map(item => Number(item.mistakes || 0)), 1);
    hardWordBars.innerHTML = topItems.map(item => {
      const mistakes = Number(item.mistakes || 0);
      const width = Math.max(7, Math.round(mistakes / maxMistakes * 100));
      const translation = item.ru ? ` — ${escapeHtml(item.ru)}` : '';
      return `<div class="hard-word-item">
        <div class="hard-word-heading">
          <span class="hard-word-name"><strong>${escapeHtml(item.en)}</strong>${translation}</span>
          <span class="hard-word-count">${mistakes}</span>
        </div>
        <div class="hard-word-track" aria-label="Ошибок: ${mistakes}">
          <div class="hard-word-fill" style="width: ${width}%"></div>
        </div>
      </div>`;
    }).join('');
  }

  window.showStats = async function showStatsWithHardWords() {
    showScreen('stats');
    try {
      const progress = await apiRequest(`/api/progress?chat_id=${encodeURIComponent(currentChatId())}`);
      document.getElementById('statCorrect').textContent = Number(progress.total_correct || 0);
      document.getElementById('statWrong').textContent = Number(progress.total_wrong || 0);
      document.getElementById('statAccuracy').textContent = `${Number(progress.accuracy || 0)}%`;
      renderHardWordBars(Array.isArray(progress.hard_word_stats) ? progress.hard_word_stats : []);
    } catch (error) {
      renderHardWordBars([]);
      console.error('Ошибка загрузки статистики:', error);
    }
  };
})();
