'use strict';

(async function main() {
  let currentStore = '滨江';
  let allOutputRecords = [];

  const sceneGrid = document.getElementById('sceneGrid');
  const storeTabs = document.getElementById('storeTabs');
  const loading = document.getElementById('loading');
  const errorEl = document.getElementById('error');

  function showLoading() {
    loading.style.display = 'block';
    sceneGrid.innerHTML = '';
    errorEl.style.display = 'none';
  }

  function showError(msg) {
    loading.style.display = 'none';
    errorEl.style.display = 'block';
    errorEl.textContent = msg;
  }

  async function loadData() {
    showLoading();
    try {
      allOutputRecords = await fetchOutputRecords();
      loading.style.display = 'none';
      renderCurrentStore();
    } catch (err) {
      showError(`数据加载失败: ${err.message}`);
      console.error(err);
    }
  }

  function renderCurrentStore() {
    const config = STORE_CONFIG[currentStore];
    if (!config) return;

    const scenes = aggregateByScene(
      allOutputRecords,
      config.fieldName,
      config.fieldType
    );

    renderSceneGrid(sceneGrid, scenes, currentStore);

    document.querySelectorAll('.store-tab').forEach(tab => {
      tab.classList.toggle('active', tab.textContent === currentStore);
    });

    sceneGrid.querySelectorAll('.scene-card').forEach(card => {
      card.addEventListener('click', () => {
        const sceneName = card.dataset.scene;
        const sceneData = scenes[sceneName];
        showDetailModal(sceneName, currentStore, sceneData);
      });
    });
  }

  function switchStore(storeName) {
    currentStore = storeName;
    renderCurrentStore();
  }

  renderStoreTabs(storeTabs, STORE_CONFIG, switchStore);
  await loadData();
})();
