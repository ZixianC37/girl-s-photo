'use strict';

function calcAverage(scenes, metric) {
  var values = Object.values(scenes).map(function(s) { return s[metric] || 0; });
  if (values.length === 0) return 0;
  return values.reduce(function(a, b) { return a + b; }, 0) / values.length;
}

function calcMax(scenes, metric) {
  var values = Object.values(scenes).map(function(s) { return s[metric] || 0; });
  return Math.max.apply(null, values) || 1;
}

function renderSceneGrid(container, scenes, storeName, storeMetrics) {
  container.innerHTML = '';
  var avgProductCount = calcAverage(scenes, 'productCount');
  var maxProductCount = calcMax(scenes, 'productCount');
  var sorted = Object.entries(scenes).sort(function(a, b) { return b[1].productCount - a[1].productCount; });

  sorted.forEach(function(entry, index) {
    var sceneName = entry[0];
    var data = entry[1];
    var heatLevel = getHeatLevel(data.productCount, avgProductCount);
    var barWidth = Math.round((data.productCount / maxProductCount) * 100);

    var card = document.createElement('div');
    card.className = 'scene-card heat-' + heatLevel;
    card.dataset.scene = sceneName;
    card.dataset.store = storeName;
    // 入场动画延迟（交错出现）
    card.style.animationDelay = (index * 40) + 'ms';

    card.innerHTML =
      '<div class="scene-name">' + sceneName + '</div>' +
      '<div class="scene-stats">' +
        '<span class="stat"><strong>' + data.productCount + '</strong>品</span>' +
        '<span class="stat new"><strong>' + data.newProducts + '</strong>新</span>' +
      '</div>' +
      '<div class="scene-status">' +
        (data.statusDist['已上架'] > 0 ? '<span class="badge badge-active">' + data.statusDist['已上架'] + '上架</span>' : '') +
        (data.statusDist['待上架'] > 0 ? '<span class="badge badge-pending">' + data.statusDist['待上架'] + '待上</span>' : '') +
        (data.statusDist['已下架'] > 0 ? '<span class="badge badge-offline">' + data.statusDist['已下架'] + '下架</span>' : '') +
      '</div>' +
      '<div class="heat-indicator heat-' + heatLevel + '">' +
        (heatLevel === 'high' ? '🔥 热门' : heatLevel === 'medium' ? '⚡ 偏热' : heatLevel === 'low' ? '❄️ 低频' : '💤 闲置') +
      '</div>' +
      '<div class="heat-bar"><div class="heat-bar-fill ' + heatLevel + '" style="width:' + barWidth + '%"></div></div>';

    container.appendChild(card);
  });

  // 渲染摘要统计
  renderSummary(scenes, storeName, storeMetrics);
}

function renderSummary(scenes, storeName, storeMetrics) {
  var bar = document.getElementById('summaryBar');
  if (!bar) return;

  var totalProducts = 0;
  var totalNew = 0;
  var sceneCount = Object.keys(scenes).length;
  var hotCount = 0;
  var avgProductCount = calcAverage(scenes, 'productCount');

  Object.values(scenes).forEach(function(s) {
    totalProducts += s.productCount;
    totalNew += s.newProducts;
    if (s.productCount >= avgProductCount * 1.5) hotCount++;
  });

  var avgPerScene = sceneCount > 0 ? (totalProducts / sceneCount).toFixed(1) : '0';

  var html =
    '<div class="summary-item">' +
      '<span class="summary-value">' + sceneCount + '</span>' +
      '<span class="summary-label">场景</span>' +
    '</div>' +
    '<div class="summary-item">' +
      '<span class="summary-value">' + totalProducts + '</span>' +
      '<span class="summary-label">关联产品</span>' +
    '</div>' +
    '<div class="summary-item">' +
      '<span class="summary-value accent">' + totalNew + '</span>' +
      '<span class="summary-label">上新产品</span>' +
    '</div>' +
    '<div class="summary-item">' +
      '<span class="summary-value">' + avgPerScene + '</span>' +
      '<span class="summary-label">场均产品</span>' +
    '</div>' +
    '<div class="summary-item">' +
      '<span class="summary-value">' + hotCount + '</span>' +
      '<span class="summary-label">热门场景</span>' +
    '</div>';

  if (storeMetrics) {
    html +=
      '<div class="summary-divider"></div>' +
      '<div class="summary-item">' +
        '<span class="summary-value">¥' + (storeMetrics.totalRevenue / 10000).toFixed(1) + '万</span>' +
        '<span class="summary-label">总成交</span>' +
      '</div>' +
      '<div class="summary-item">' +
        '<span class="summary-value">¥' + storeMetrics.avgPrice + '</span>' +
        '<span class="summary-label">客单价</span>' +
      '</div>' +
      '<div class="summary-item">' +
        '<span class="summary-value accent">' + storeMetrics.newProductRevenueRatio + '%</span>' +
        '<span class="summary-label">30日新品占比</span>' +
      '</div>' +
      '<div class="summary-item">' +
        '<span class="summary-value">' + storeMetrics.activeProductCount + '</span>' +
        '<span class="summary-label">活跃产品</span>' +
      '</div>';
  }

  bar.innerHTML = html;
}

function renderStoreTabs(container, storeConfig, onSelect) {
  container.innerHTML = '';
  for (var storeName in storeConfig) {
    if (!storeConfig.hasOwnProperty(storeName)) continue;
    var config = storeConfig[storeName];
    var tab = document.createElement('button');
    tab.className = 'store-tab';
    tab.textContent = storeName;
    tab.dataset.brand = config.brand;
    tab.addEventListener('click', (function(name) {
      return function() { onSelect(name); };
    })(storeName));
    container.appendChild(tab);
  }
}

if (typeof window !== 'undefined') {
  window.renderSceneGrid = renderSceneGrid;
  window.renderStoreTabs = renderStoreTabs;
  window.calcAverage = calcAverage;
  window.renderSummary = renderSummary;
}
