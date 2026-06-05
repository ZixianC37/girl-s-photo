'use strict';

function showDetailModal(sceneName, storeName, sceneData) {
  var overlay = document.getElementById('modalOverlay');
  var modal = document.getElementById('modal');
  var newProducts = sceneData.products.filter(function(p) { return p.isNew; });
  var oldProducts = sceneData.products.filter(function(p) { return !p.isNew; });

  function badgeClass(status) {
    if (status === '已上架') return 'badge-active';
    if (status === '待上架') return 'badge-pending';
    return 'badge-offline';
  }

  modal.innerHTML =
    '<div class="modal-header">' +
      '<h2>📍 ' + sceneName + ' — ' + storeName + '店</h2>' +
      '<button class="modal-close" id="modalClose">✕</button>' +
    '</div>' +
    '<div class="modal-stats">' +
      '<span>关联产品：<strong>' + sceneData.productCount + '</strong>个</span>' +
      '<span>上新品：<strong>' + sceneData.newProducts + '</strong>个</span>' +
      '<span>已上架：<strong>' + (sceneData.statusDist['已上架'] || 0) + '</strong>个</span>' +
      '<span>已下架：<strong>' + (sceneData.statusDist['已下架'] || 0) + '</strong>个</span>' +
    '</div>' +
    '<div class="modal-section">' +
      '<h3>上新产品（' + newProducts.length + '个）</h3>' +
      '<table class="product-table">' +
        '<thead><tr><th>方案名称</th><th>状态</th></tr></thead>' +
        '<tbody>' +
          (newProducts.length > 0
            ? newProducts.map(function(p) {
                return '<tr><td>' + p.name + '</td><td><span class="badge ' + badgeClass(p.status) + '">' + p.status + '</span></td></tr>';
              }).join('')
            : '<tr><td colspan="2" class="empty">暂无上新产品</td></tr>') +
        '</tbody>' +
      '</table>' +
    '</div>' +
    '<div class="modal-section">' +
      '<h3>往期产品（' + oldProducts.length + '个）</h3>' +
      '<table class="product-table">' +
        '<thead><tr><th>方案名称</th><th>状态</th></tr></thead>' +
        '<tbody>' +
          (oldProducts.length > 0
            ? oldProducts.slice(0, 20).map(function(p) {
                return '<tr><td>' + p.name + '</td><td><span class="badge ' + badgeClass(p.status) + '">' + p.status + '</span></td></tr>';
              }).join('') +
              (oldProducts.length > 20 ? '<tr><td colspan="2" class="more">...还有 ' + (oldProducts.length - 20) + ' 个</td></tr>' : '')
            : '<tr><td colspan="2" class="empty">暂无往期产品</td></tr>') +
        '</tbody>' +
      '</table>' +
    '</div>';

  overlay.style.display = 'flex';
  document.getElementById('modalClose').addEventListener('click', hideDetailModal);
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) hideDetailModal();
  });

  // ESC 关闭
  var escHandler = function(e) {
    if (e.key === 'Escape') {
      hideDetailModal();
      document.removeEventListener('keydown', escHandler);
    }
  };
  document.addEventListener('keydown', escHandler);
}

function hideDetailModal() {
  var overlay = document.getElementById('modalOverlay');
  if (overlay) overlay.style.display = 'none';
}

if (typeof window !== 'undefined') {
  window.showDetailModal = showDetailModal;
  window.hideDetailModal = hideDetailModal;
}
