'use strict';

function calcAverage(scenes, metric) {
  const values = Object.values(scenes).map(s => s[metric] || 0);
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function renderSceneGrid(container, scenes, storeName) {
  container.innerHTML = '';
  const avgProductCount = calcAverage(scenes, 'productCount');
  const sorted = Object.entries(scenes).sort((a, b) => b[1].productCount - a[1].productCount);

  for (const [sceneName, data] of sorted) {
    const heatLevel = getHeatLevel(data.productCount, avgProductCount);
    const card = document.createElement('div');
    card.className = `scene-card heat-${heatLevel}`;
    card.dataset.scene = sceneName;
    card.dataset.store = storeName;

    card.innerHTML = `
      <div class="scene-name">${sceneName}</div>
      <div class="scene-stats">
        <span class="stat"><strong>${data.productCount}</strong>品</span>
        <span class="stat new">${data.newProducts}新</span>
      </div>
      <div class="scene-status">
        ${data.statusDist['已上架'] > 0 ? `<span class="badge badge-active">${data.statusDist['已上架']}上架</span>` : ''}
        ${data.statusDist['待上架'] > 0 ? `<span class="badge badge-pending">${data.statusDist['待上架']}待上</span>` : ''}
        ${data.statusDist['已下架'] > 0 ? `<span class="badge badge-offline">${data.statusDist['已下架']}下架</span>` : ''}
      </div>
      <div class="heat-indicator heat-${heatLevel}">
        ${heatLevel === 'high' ? '🔴 热门' : heatLevel === 'medium' ? '🟠 偏热' : heatLevel === 'low' ? '🟡 低频' : '⬜ 闲置'}
      </div>
    `;
    container.appendChild(card);
  }
}

function renderStoreTabs(container, storeConfig, onSelect) {
  container.innerHTML = '';
  for (const [storeName, config] of Object.entries(storeConfig)) {
    const tab = document.createElement('button');
    tab.className = 'store-tab';
    tab.textContent = storeName;
    tab.dataset.brand = config.brand;
    tab.style.borderBottomColor = BRAND_COLORS[config.brand];
    tab.addEventListener('click', () => onSelect(storeName));
    container.appendChild(tab);
  }
}

if (typeof window !== 'undefined') {
  window.renderSceneGrid = renderSceneGrid;
  window.renderStoreTabs = renderStoreTabs;
  window.calcAverage = calcAverage;
}
