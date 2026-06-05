'use strict';

(function main() {
  var currentStore = '滨江';
  var allOutputRecords = [];

  var sceneGrid = document.getElementById('sceneGrid');
  var storeTabs = document.getElementById('storeTabs');
  var loading = document.getElementById('loading');
  var errorEl = document.getElementById('error');

  // 显示日期副标题
  var dateEl = document.getElementById('dateSubtitle');
  if (dateEl) {
    var now = new Date();
    var weekDays = ['日', '一', '二', '三', '四', '五', '六'];
    dateEl.textContent = now.getFullYear() + '/' +
      String(now.getMonth() + 1).padStart(2, '0') + '/' +
      String(now.getDate()).padStart(2, '0') + ' 周' +
      weekDays[now.getDay()];
  }

  function showLoading() {
    loading.style.display = 'flex';
    sceneGrid.innerHTML = '';
    errorEl.style.display = 'none';
  }

  function showError(msg) {
    loading.style.display = 'none';
    errorEl.style.display = 'block';
    errorEl.textContent = msg;
  }

  function loadData() {
    showLoading();
    return fetchOutputRecords()
      .then(function(records) {
        allOutputRecords = records;
        loading.style.display = 'none';
        renderCurrentStore();
      })
      .catch(function(err) {
        showError('数据加载失败: ' + err.message);
        console.error(err);
      });
  }

  function renderCurrentStore() {
    var config = STORE_CONFIG[currentStore];
    if (!config) return;

    var storeMetrics = aggregateStoreMetrics(
      allOutputRecords,
      config.fieldName,
      config.fieldType
    );

    var scenes = aggregateByScene(
      allOutputRecords,
      config.fieldName,
      config.fieldType
    );

    renderSceneGrid(sceneGrid, scenes, currentStore, storeMetrics);

    // 更新标签高亮
    var tabs = document.querySelectorAll('.store-tab');
    for (var i = 0; i < tabs.length; i++) {
      var isActive = tabs[i].textContent === currentStore;
      tabs[i].classList.toggle('active', isActive);
    }

    // 绑定卡片点击
    var cards = sceneGrid.querySelectorAll('.scene-card');
    for (var j = 0; j < cards.length; j++) {
      cards[j].addEventListener('click', function() {
        var sceneName = this.dataset.scene;
        var sceneData = scenes[sceneName];
        if (sceneData) {
          showDetailModal(sceneName, currentStore, sceneData);
        }
      });
    }
  }

  function switchStore(storeName) {
    currentStore = storeName;
    renderCurrentStore();
  }

  renderStoreTabs(storeTabs, STORE_CONFIG, switchStore);
  loadData();
})();
