'use strict';

function showDetailModal(sceneName, storeName, sceneData, usageCount) {
  const overlay = document.getElementById('modalOverlay');
  const modal = document.getElementById('modal');
  const newProducts = sceneData.products.filter(p => p.isNew);
  const oldProducts = sceneData.products.filter(p => !p.isNew);

  modal.innerHTML = `
    <div class="modal-header">
      <h2>📍 ${sceneName} — ${storeName}店</h2>
      <button class="modal-close" id="modalClose">✕</button>
    </div>
    <div class="modal-stats">
      ${usageCount !== undefined ? `<span>近30天使用：<strong>${usageCount}</strong>次</span>` : ''}
      <span>关联产品：<strong>${sceneData.productCount}</strong>个</span>
      <span>上新品：<strong>${sceneData.newProducts}</strong>个</span>
    </div>
    <div class="modal-section">
      <h3>上新产品（${newProducts.length}个）</h3>
      <table class="product-table">
        <thead><tr><th>方案名称</th><th>状态</th></tr></thead>
        <tbody>
          ${newProducts.map(p => `<tr><td>${p.name}</td><td><span class="badge badge-${p.status === '已上架' ? 'active' : p.status === '待上架' ? 'pending' : 'offline'}">${p.status}</span></td></tr>`).join('')}
          ${newProducts.length === 0 ? '<tr><td colspan="2" class="empty">暂无上新产品</td></tr>' : ''}
        </tbody>
      </table>
    </div>
    <div class="modal-section">
      <h3>往期产品（${oldProducts.length}个）</h3>
      <table class="product-table">
        <thead><tr><th>方案名称</th><th>状态</th></tr></thead>
        <tbody>
          ${oldProducts.slice(0, 20).map(p => `<tr><td>${p.name}</td><td><span class="badge badge-${p.status === '已上架' ? 'active' : p.status === '待上架' ? 'pending' : 'offline'}">${p.status}</span></td></tr>`).join('')}
          ${oldProducts.length > 20 ? `<tr><td colspan="2" class="more">...还有 ${oldProducts.length - 20} 个</td></tr>` : ''}
          ${oldProducts.length === 0 ? '<tr><td colspan="2" class="empty">暂无往期产品</td></tr>' : ''}
        </tbody>
      </table>
    </div>
  `;

  overlay.style.display = 'flex';
  document.getElementById('modalClose').addEventListener('click', hideDetailModal);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) hideDetailModal();
  });
}

function hideDetailModal() {
  document.getElementById('modalOverlay').style.display = 'none';
}

if (typeof window !== 'undefined') {
  window.showDetailModal = showDetailModal;
  window.hideDetailModal = hideDetailModal;
}
