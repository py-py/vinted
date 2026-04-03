function colorizeByFavourites() {
  document.querySelectorAll('[data-testid$="--favourite"]').forEach(btn => {
    const countEl = btn.querySelector('[data-testid="favourite-count-text"]');
    if (!countEl) return;

    const count = parseInt(countEl.textContent.trim(), 10);
    if (isNaN(count)) return;

    const container = btn.closest('.new-item-box__container');
    if (!container) return;

    const content = container.querySelector('.web_ui__Cell__content');
    if (!content) return;

    let color;
    if (count >= 8) {
      color = '#fca5a5';
    } else if (count >= 5) {
      color = '#fed7aa';
    } else if (count > 2) {
      color = '#fef9c3';
    } else {
      return;
    }

    content.style.backgroundColor = color;
  });
}

// Initial run
colorizeByFavourites();

// Watch for dynamically loaded cards
const observer = new MutationObserver(() => colorizeByFavourites());
observer.observe(
  document.querySelector('.feed-grid') ?? document.body,
  { childList: true, subtree: true }
);