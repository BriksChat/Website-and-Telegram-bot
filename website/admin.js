(() => {
  'use strict';

  const API = String(window.ENGLISH_API_URL || '').replace(/\/$/, '');
  const state = { page: 1, totalPages: 1, search: '', password: sessionStorage.getItem('adminPassword') || '' };

  const loginView = document.getElementById('loginView');
  const adminView = document.getElementById('adminView');
  const loginForm = document.getElementById('loginForm');
  const passwordInput = document.getElementById('password');
  const loginMessage = document.getElementById('loginMessage');
  const adminMessage = document.getElementById('adminMessage');
  const wordsBody = document.getElementById('wordsBody');
  const summary = document.getElementById('summary');
  const pageInfo = document.getElementById('pageInfo');
  const prevPage = document.getElementById('prevPage');
  const nextPage = document.getElementById('nextPage');
  const searchInput = document.getElementById('searchInput');

  function showMessage(element, text, type = '') {
    element.textContent = text;
    element.className = `message ${type}`.trim();
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('Content-Type', 'application/json');
    if (state.password) headers.set('X-Admin-Password', state.password);
    const response = await fetch(`${API}${path}`, { ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.message || `Ошибка ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function setAuthenticated(value) {
    loginView.hidden = value;
    adminView.hidden = !value;
  }

  async function login(password) {
    const response = await fetch(`${API}/api/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || 'Не удалось войти');
    state.password = password;
    sessionStorage.setItem('adminPassword', password);
    setAuthenticated(true);
    await loadWords(1);
  }

  function renderWords(items) {
    wordsBody.textContent = '';
    if (!items.length) {
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.colSpan = 5;
      cell.textContent = 'Слова не найдены';
      row.appendChild(cell);
      wordsBody.appendChild(row);
      return;
    }

    items.forEach((item) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${item.id}</td>
        <td>${item.card_id}</td>
        <td></td>
        <td></td>
        <td class="actions"></td>
      `;

      const englishWord = document.createElement('input');
      englishWord.value = item.en;
      englishWord.maxLength = 120;
      row.children[2].appendChild(englishWord);

      const translation = document.createElement('input');
      translation.value = item.ru;
      translation.maxLength = 255;
      row.children[3].appendChild(translation);

      const saveButton = document.createElement('button');
      saveButton.type = 'button';
      saveButton.textContent = 'Сохранить';
      saveButton.addEventListener('click', async () => {
        const nextEn = englishWord.value.trim();
        const nextRu = translation.value.trim();
        if (!nextEn || !nextRu) {
          showMessage(adminMessage, 'Английское слово и перевод не могут быть пустыми', 'error');
          return;
        }

        try {
          const oldEnglishWord = item.en;

          if (nextEn === item.en) {
            const data = await api(`/api/admin/words/${item.id}`, {
              method: 'PATCH',
              body: JSON.stringify({ ru: nextRu })
            });
            item.ru = data.item.ru;
          } else {
            const created = await api('/api/admin/words', {
              method: 'POST',
              body: JSON.stringify({
                card_id: item.card_id,
                en: nextEn,
                ru: nextRu
              })
            });

            try {
              await api(`/api/admin/words/${item.id}`, { method: 'DELETE' });
            } catch (deleteError) {
              await api(`/api/admin/words/${created.item.id}`, { method: 'DELETE' }).catch(() => {});
              throw deleteError;
            }

            item.id = created.item.id;
            item.en = created.item.en;
            item.ru = created.item.ru;
          }

          englishWord.value = item.en;
          translation.value = item.ru;
          showMessage(adminMessage, `Слово “${oldEnglishWord}” сохранено как “${item.en}” — “${item.ru}”`, 'success');
          await loadWords(state.page);
        } catch (error) {
          handleError(error);
        }
      });

      const deleteButton = document.createElement('button');
      deleteButton.type = 'button';
      deleteButton.className = 'danger';
      deleteButton.textContent = 'Удалить';
      deleteButton.addEventListener('click', async () => {
        if (!confirm(`Удалить слово “${item.en}”?`)) return;
        try {
          await api(`/api/admin/words/${item.id}`, { method: 'DELETE' });
          showMessage(adminMessage, `Слово “${item.en}” удалено`, 'success');
          await loadWords(state.page);
        } catch (error) {
          handleError(error);
        }
      });

      row.children[4].append(saveButton, deleteButton);
      wordsBody.appendChild(row);
    });
  }

  function handleError(error) {
    if (error.status === 401) {
      sessionStorage.removeItem('adminPassword');
      state.password = '';
      setAuthenticated(false);
      showMessage(loginMessage, 'Сессия завершена. Введите пароль снова.', 'error');
      return;
    }
    showMessage(adminMessage, error.message || 'Произошла ошибка', 'error');
  }

  async function loadWords(page = 1) {
    showMessage(adminMessage, 'Загрузка…');
    const params = new URLSearchParams({ page: String(page), per_page: '25' });
    if (state.search) params.set('search', state.search);
    try {
      const data = await api(`/api/admin/words?${params}`);
      state.page = data.page;
      state.totalPages = data.total_pages;
      renderWords(data.items);
      summary.textContent = `Всего слов: ${data.total}`;
      pageInfo.textContent = `Страница ${data.page} из ${data.total_pages}`;
      prevPage.disabled = data.page <= 1;
      nextPage.disabled = data.page >= data.total_pages;
      showMessage(adminMessage, '');
    } catch (error) {
      handleError(error);
    }
  }

  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    showMessage(loginMessage, 'Проверка…');
    try {
      await login(passwordInput.value);
      passwordInput.value = '';
      showMessage(loginMessage, '');
    } catch (error) {
      showMessage(loginMessage, error.message, 'error');
    }
  });

  document.getElementById('logoutButton').addEventListener('click', () => {
    sessionStorage.removeItem('adminPassword');
    state.password = '';
    setAuthenticated(false);
  });

  document.getElementById('addForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const cardId = document.getElementById('newCardId');
    const en = document.getElementById('newEn');
    const ru = document.getElementById('newRu');
    try {
      await api('/api/admin/words', {
        method: 'POST',
        body: JSON.stringify({ card_id: Number(cardId.value), en: en.value.trim(), ru: ru.value.trim() })
      });
      en.value = '';
      ru.value = '';
      showMessage(adminMessage, 'Новое слово добавлено', 'success');
      await loadWords(1);
    } catch (error) {
      handleError(error);
    }
  });

  document.getElementById('searchButton').addEventListener('click', () => {
    state.search = searchInput.value.trim();
    loadWords(1);
  });
  searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      state.search = searchInput.value.trim();
      loadWords(1);
    }
  });
  document.getElementById('resetSearchButton').addEventListener('click', () => {
    searchInput.value = '';
    state.search = '';
    loadWords(1);
  });
  prevPage.addEventListener('click', () => loadWords(state.page - 1));
  nextPage.addEventListener('click', () => loadWords(state.page + 1));

  if (!API) {
    showMessage(loginMessage, 'Не настроен адрес API в config.js', 'error');
    return;
  }
  if (state.password) {
    setAuthenticated(true);
    loadWords(1);
  }
})();
