/* ── Vinted Favourite Colorizer + Price Filter ── */

// ── 1. Colorize by favourites ──────────────────────────────────────────────
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
    if (count >= 8)      color = '#fca5a5'; // soft red
    else if (count >= 5) color = '#fed7aa'; // peach
    else if (count > 2)  color = '#fef9c3'; // pale yellow
    else return;

    content.style.backgroundColor = color;
  });
}

// ── 2. Price filter ────────────────────────────────────────────────────────
function parsePrice(el) {
  if (!el) return null;
  const raw = el.textContent.replace(/\s/g, '').replace(',', '.');
  const num = parseFloat(raw);
  return isNaN(num) ? null : num;
}

function applyPriceFilter(enabled, min, max) {
  document.querySelectorAll('.new-item-box__container').forEach(card => {
    const gridItem = card.closest('.feed-grid__item');
    if (!gridItem) return;

    if (!enabled) {
      gridItem.style.display = '';
      return;
    }

    const priceEl = card.querySelector('[data-testid$="--price-text"]');
    const price = parsePrice(priceEl);

    gridItem.style.display =
      price !== null && price >= min && price <= max ? '' : 'none';
  });
}

// ── 3. Floating UI panel ───────────────────────────────────────────────────
function createPanel() {
  const panel = document.createElement('div');
  panel.id = 'vfc-panel';
  panel.innerHTML = `
    <style>
      #vfc-panel {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 99999;
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.12);
        font-family: system-ui, sans-serif;
        font-size: 13px;
        color: #111;
        min-width: 220px;
        user-select: none;
      }
      #vfc-panel label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 500; }
      #vfc-panel input[type=checkbox] { width: 16px; height: 16px; cursor: pointer; accent-color: #6ee7b7; }
      #vfc-slider-wrap { margin-top: 12px; display: none; }
      #vfc-slider-wrap.active { display: block; }
      #vfc-range-labels {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: #555;
        margin-bottom: 6px;
      }
      #vfc-range-labels span { font-weight: 600; color: #111; }
      #vfc-track-wrap {
        position: relative;
        height: 20px;
        display: flex;
        align-items: center;
      }
      #vfc-track {
        position: absolute;
        left: 0; right: 0;
        height: 4px;
        border-radius: 2px;
        background: #e5e7eb;
        pointer-events: none;
      }
      #vfc-track-fill {
        position: absolute;
        height: 4px;
        background: #6ee7b7;
        border-radius: 2px;
        pointer-events: none;
      }
      #vfc-track-wrap input[type=range] {
        position: absolute;
        width: 100%;
        height: 4px;
        appearance: none;
        background: transparent;
        pointer-events: none;
        margin: 0;
      }
      #vfc-track-wrap input[type=range]::-webkit-slider-thumb {
        appearance: none;
        width: 16px; height: 16px;
        border-radius: 50%;
        background: #fff;
        border: 2px solid #6ee7b7;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        pointer-events: all;
        cursor: pointer;
      }
    </style>

    <label>
      <input type="checkbox" id="vfc-fav-checkbox" checked>
      Colorize by favourites
    </label>
    <div style="margin-top:10px;border-top:1px solid #e5e7eb;padding-top:10px">
    <label>
      <input type="checkbox" id="vfc-checkbox">
      Filter by price
    </label>
    </div>

    <div id="vfc-slider-wrap">
      <div id="vfc-range-labels">
        <span id="vfc-min-label">0</span>
        <span>–</span>
        <span id="vfc-max-label">1000</span>
        <span style="color:#999;font-weight:400">PLN</span>
      </div>
      <div id="vfc-track-wrap">
        <div id="vfc-track"></div>
        <div id="vfc-track-fill"></div>
        <input type="range" id="vfc-range-min" min="0" max="1000" value="0" step="10">
        <input type="range" id="vfc-range-max" min="0" max="1000" value="1000" step="10">
      </div>
    </div>
  `;
  document.body.appendChild(panel);

  const favCheckbox = panel.querySelector('#vfc-fav-checkbox');

  function resetColors() {
    document.querySelectorAll('.web_ui__Cell__content').forEach(el => {
      el.style.backgroundColor = '';
    });
  }

  favCheckbox.addEventListener('change', () => {
    if (favCheckbox.checked) colorizeByFavourites();
    else resetColors();
  });

  const checkbox   = panel.querySelector('#vfc-checkbox');
  const sliderWrap = panel.querySelector('#vfc-slider-wrap');
  const rangeMin   = panel.querySelector('#vfc-range-min');
  const rangeMax   = panel.querySelector('#vfc-range-max');
  const minLabel   = panel.querySelector('#vfc-min-label');
  const maxLabel   = panel.querySelector('#vfc-max-label');
  const trackFill  = panel.querySelector('#vfc-track-fill');

  function updateFill() {
    const min = parseInt(rangeMin.value);
    const max = parseInt(rangeMax.value);
    trackFill.style.left  = ((min / 1000) * 100).toFixed(1) + '%';
    trackFill.style.right = (100 - (max / 1000) * 100).toFixed(1) + '%';
    minLabel.textContent  = min;
    maxLabel.textContent  = max;
  }

  function onChange() {
    // prevent thumbs crossing
    if (parseInt(rangeMin.value) > parseInt(rangeMax.value)) {
      rangeMin.value = rangeMax.value;
    }
    updateFill();
    applyPriceFilter(
      checkbox.checked,
      parseInt(rangeMin.value),
      parseInt(rangeMax.value)
    );
  }

  checkbox.addEventListener('change', () => {
    sliderWrap.classList.toggle('active', checkbox.checked);
    onChange();
  });

  rangeMin.addEventListener('input', onChange);
  rangeMax.addEventListener('input', onChange);

  updateFill();
}

// ── 4. Init ────────────────────────────────────────────────────────────────
colorizeByFavourites();
createPanel();

const observer = new MutationObserver(() => {
  const favCb = document.querySelector('#vfc-fav-checkbox');
  if (favCb && favCb.checked) colorizeByFavourites();
});
observer.observe(
  document.querySelector('.feed-grid') ?? document.body,
  { childList: true, subtree: true }
);