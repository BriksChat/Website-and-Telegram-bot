/*
 * ui.js — управление пользовательским интерфейсом сайта English Learning.
 *
 * Отвечает за бургер-меню, переключение экранов, первый запуск карточки
 * и короткую обучающую анимацию для нового пользователя.
 *
 * Зависимости: config.js, script.js, chat-id.js и элементы из index.html.
 * Подключается после script.js и chat-id.js.
 */
(function initialiseInterface() {
  const burgerMenu = document.getElementById('burgerMenu');
  const menuOverlay = document.getElementById('menuOverlay');
  const learningDemo = document.getElementById('learningDemo');
  const demoText = document.getElementById('demoText');
  const demoRu = document.getElementById('demoRu');
  const demoEn = document.getElementById('demoEn');
  const demoNextButton = document.getElementById('demoNextButton');
  const demoSteps = Array.from(document.querySelectorAll('.demo-step'));
  let demoStep = 0;

  // Открывает или закрывает боковое меню и блокирует прокрутку страницы.
  window.toggleBurgerMenu = function toggleBurgerMenu() {
    const isOpen = burgerMenu.classList.toggle('open');
    menuOverlay.classList.toggle('visible', isOpen);
    burgerMenu.setAttribute('aria-hidden', String(!isOpen));
    document.body.classList.toggle('menu-open', isOpen);
  };

  // Полностью закрывает меню независимо от его текущего состояния.
  window.closeBurgerMenu = function closeBurgerMenu() {
    burgerMenu.classList.remove('open');
    menuOverlay.classList.remove('visible');
    burgerMenu.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('menu-open');
  };

  // Закрывает меню перед переключением на выбранный экран.
  function openScreen(screenId) {
    closeBurgerMenu();
    showScreen(screenId);
  }

  async function fetchProgressState() {
    const apiBase = String(window.ENGLISH_API_URL || '').replace(/\/$/, '');
    if (!apiBase) throw new Error('API не настроен');

    const response = await fetch(
      `${apiBase}/api/progress?chat_id=${encodeURIComponent(chat_id)}`,
      { headers: { Accept: 'application/json' } }
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  // Возвращает пользователя к текущей карточке обучения.
  // Если основной курс уже завершён, всегда показываем финальный экран с тремя вариантами.
  window.openLearningFromMenu = async function openLearningFromMenu() {
    closeBurgerMenu();

    try {
      const progress = await fetchProgressState();
      if (progress.finished === true) {
        showScreen('courseComplete');
        return;
      }
    } catch (error) {
      console.warn('Не удалось проверить завершение курса:', error);
    }

    startLearning();
  };

  // Загружает и показывает статистику пользователя.
  window.openStatsFromMenu = function openStatsFromMenu() {
    closeBurgerMenu();
    showStats();
  };

  // Открывает раздел помощи.
  window.openHelpFromMenu = function openHelpFromMenu() {
    openScreen('help');
  };

  // Открывает техническую информацию о проекте.
  window.openDevInfoFromMenu = function openDevInfoFromMenu() {
    openScreen('dev-info');
  };

  // Запрашивает статистику и определяет, начинал ли пользователь обучение.
  async function hasExistingProgress(progressOverride) {
    try {
      const progress = progressOverride || await fetchProgressState();
      const completedCards = Array.isArray(progress.completed_cards)
        ? progress.completed_cards.length
        : 0;

      return Number(progress.total_correct || 0) > 0 ||
        Number(progress.total_wrong || 0) > 0 ||
        completedCards > 0 ||
        Number(progress.current_card || 1) > 1 ||
        progress.finished === true;
    } catch (error) {
      // При неизвестном состоянии не показываем подсказку повторно по ошибке.
      console.warn('Не удалось проверить прогресс для обучения:', error);
      return true;
    }
  }

  // Сбрасывает визуальное состояние демонстрационной пары.
  function resetDemoWords() {
    demoRu.className = 'demo-word';
    demoEn.className = 'demo-word';
  }

  // Отрисовывает один из трёх шагов мини-обучения.
  function renderDemoStep() {
    resetDemoWords();
    demoSteps.forEach((step, index) => step.classList.toggle('active', index === demoStep));

    if (demoStep === 0) {
      demoText.textContent = 'Сначала нажмите на русское слово.';
      demoRu.classList.add('demo-selected');
      demoNextButton.textContent = 'Далее';
    } else if (demoStep === 1) {
      demoText.textContent = 'Затем найдите его английский перевод.';
      demoRu.classList.add('demo-selected');
      demoEn.classList.add('demo-selected');
      demoNextButton.textContent = 'Далее';
    } else {
      demoText.textContent = 'Правильная пара станет зелёной и сохранится в прогрессе.';
      demoRu.classList.add('demo-matched');
      demoEn.classList.add('demo-matched');
      demoNextButton.textContent = 'Начать обучение';
    }
  }

  // Показывает обучение с первого шага.
  window.showLearningDemo = function showLearningDemo() {
    closeBurgerMenu();
    demoStep = 0;
    renderDemoStep();
    learningDemo.classList.remove('hidden');
    document.body.classList.add('menu-open');
  };

  // Переходит к следующему шагу или завершает демонстрацию.
  window.nextLearningDemoStep = function nextLearningDemoStep() {
    if (demoStep < 2) {
      demoStep += 1;
      renderDemoStep();
    } else {
      finishLearningDemo();
    }
  };

  // Закрывает демонстрацию и запоминает, что пользователь её видел.
  window.finishLearningDemo = function finishLearningDemo() {
    localStorage.setItem('learning_demo_seen', '1');
    closeLearningDemo();
    startLearning();
  };

  // Закрывает окно обучения без изменения игрового прогресса.
  window.closeLearningDemo = function closeLearningDemo() {
    learningDemo.classList.add('hidden');
    document.body.classList.remove('menu-open');
  };

  // Закрывает меню и обучение клавишей Escape.
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      closeBurgerMenu();
      closeLearningDemo();
    }
  });

  // Ждёт Chat_ID и при загрузке страницы сначала проверяет состояние курса.
  // Завершённый курс всегда возвращает пользователя на финальный экран,
  // пока он сам не выберет один из трёх вариантов продолжения.
  async function startWhenReady() {
    const loading = document.getElementById('loading');

    for (let attempt = 0; attempt < 50; attempt += 1) {
      if (typeof chat_id === 'string' && chat_id.length >= 5) {
        try {
          let progress = null;
          try {
            progress = await fetchProgressState();
          } catch (error) {
            console.warn('Не удалось проверить состояние курса при загрузке:', error);
          }

          if (progress?.finished === true) {
            showScreen('courseComplete');
            localStorage.setItem('learning_demo_seen', '1');
            return;
          }

          await startLearning();

          const demoWasSeen = localStorage.getItem('learning_demo_seen') === '1';
          const userHasProgress = await hasExistingProgress(progress);

          if (!demoWasSeen && !userHasProgress) {
            showLearningDemo();
          } else if (userHasProgress) {
            // Синхронизируем локальный флаг для следующих быстрых запусков.
            localStorage.setItem('learning_demo_seen', '1');
          }
        } finally {
          if (loading) loading.classList.add('hidden');
        }
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    if (loading) {
      loading.innerHTML = '<p>Не удалось определить Chat_ID. Обновите страницу.</p>';
    }
  }

  startWhenReady();
})();
