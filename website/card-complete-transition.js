/*
 * Короткий полноэкранный акцент после завершения всей карточки.
 *
 * Основная игровая логика остаётся в script.js. Этот файл показывает отдельный
 * полноэкранный слой на 1,5 секунды, а затем разрешает открыть обычный экран
 * «Карточка пройдена» с кнопкой «Продолжить».
 */
(function addCardCompleteTransition() {
  const originalCompleteCurrentCard = window.completeCurrentCard;
  const overlay = document.getElementById('cardCompleteOverlay');
  const CARD_COMPLETE_DELAY_MS = 1500;

  if (typeof originalCompleteCurrentCard !== 'function' || !overlay) {
    return;
  }

  window.completeCurrentCard = function completeCardWithAttentionScreen() {
    overlay.classList.remove('hidden');

    // Сохранение на Amvera и визуальная пауза начинаются одновременно.
    const savePromise = originalCompleteCurrentCard();
    const delayPromise = new Promise(resolve => setTimeout(resolve, CARD_COMPLETE_DELAY_MS));

    return Promise.allSettled([savePromise, delayPromise]).then(results => {
      overlay.classList.add('hidden');

      const saveResult = results[0];
      if (saveResult.status === 'rejected') {
        throw saveResult.reason;
      }

      return saveResult.value;
    });
  };
})();
