# 门店场景热力图 MVP 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于飞书多维表数据的门店场景利用率热力图，以门店视角展示物理场景的业务数据。

**Architecture:** 独立的纯前端应用（HTML/JS/CSS + ECharts），通过飞书 JS-SDK 获取认证后直接调用 Bitable REST API 读取数据，前端完成聚合计算和热力图渲染。不依赖后端服务。

**Tech Stack:** HTML5, JavaScript (ES6+), ECharts 5.x (CDN), 飞书 JS-SDK (CDN), Vitest (测试)

**Spec:** `docs/superpowers/specs/2026-06-04-store-scene-heatmap-design.md`

---

## File Structure

```
heatmap/
├── index.html              # 主入口页面
├── css/
│   └── style.css           # 样式（卡片网格、弹窗、筛选器）
├── js/
│   ├── config.js           # 常量配置（门店映射、字段ID、颜色阈值）
│   ├── api.js              # 飞书 Bitable API 客户端（认证 + 分页拉取）
│   ├── aggregator.js       # 数据聚合逻辑（按场景统计产品数、上新数、状态分布）
│   ├── renderer.js         # ECharts 渲染（场景卡片网格 + 热力颜色）
│   ├── detail-modal.js     # 场景详情弹窗（产品列表表格）
│   └── app.js              # 主控制器（初始化、门店切换、筛选、事件绑定）
└── tests/
    └── aggregator.test.js  # 聚合逻辑的单元测试
```

---

### Task 1: 项目骨架 + 常量配置

**Files:**
- Create: `heatmap/index.html`
- Create: `heatmap/js/config.js`
- Create: `heatmap/css/style.css`

- [ ] **Step 1: 创建项目目录和 index.html 骨架**

创建 `heatmap/index.html`，引入 ECharts CDN 和飞书 JS-SDK，包含页面基本结构：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>门店场景热力图</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <div id="app">
    <header class="header">
      <h1>🗺️ 门店场景热力图</h1>
      <div class="filters">
        <div class="store-tabs" id="storeTabs"></div>
      </div>
    </header>
    <main class="main">
      <div class="loading" id="loading">加载中...</div>
      <div class="error" id="error" style="display:none;"></div>
      <div class="scene-grid" id="sceneGrid"></div>
    </main>
    <div class="modal-overlay" id="modalOverlay" style="display:none;">
      <div class="modal" id="modal"></div>
    </div>
  </div>
  <script src="js/config.js"></script>
  <script src="js/api.js"></script>
  <script src="js/aggregator.js"></script>
  <script src="js/renderer.js"></script>
  <script src="js/detail-modal.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 创建 config.js — 门店与字段映射配置**

创建 `heatmap/js/config.js`：

```javascript
'use strict';

// 飞书多维表配置（部署时替换为实际值）
const APP_TOKEN = '';       // 多维表 app_token
const OUTPUT_TABLE_ID = ''; // 执行output 表 table_id

// 门店配置：门店名 → { 品牌, 影棚字段名, 字段类型 }
const STORE_CONFIG = {
  '滨江': {
    brand: '麦芽纪',
    fieldName: '滨江影棚',
    fieldType: 'multi',       // 多选
    tableId: 'tblGZA041E5o5PUU', // 影棚汇总表 ID（可选，用于取30天使用次数）
  },
  '下沙': {
    brand: '麦芽纪',
    fieldName: '下沙影棚',
    fieldType: 'single',      // 单选
    tableId: 'tblIdWwwM2Gyu1fG',
  },
  '上海': {
    brand: '麦芽纪',
    fieldName: '上海影棚',
    fieldType: 'multi',
    tableId: null,             // 无汇总表，从执行output聚合
  },
  '西湖': {
    brand: '麦芽岛',
    fieldName: '西湖影棚',
    fieldType: 'multi',
    tableId: null,
  },
  '甜熊下沙': {
    brand: '甜熊',
    fieldName: '甜熊下沙影棚',
    fieldType: 'single',
    tableId: 'tblV3qt3aDNz6663',
  },
};

// 品牌颜色映射
const BRAND_COLORS = {
  '麦芽纪': '#6366f1',
  '麦芽岛': '#10b981',
  '甜熊': '#f59e0b',
};

// 上新产品判定：距今多少天内算新品
const NEW_PRODUCT_DAYS = 90;

// 热力颜色阈值（同门店内相对值）
const HEAT_COLORS = {
  high: '#ef4444',    // > 均值 × 1.5
  medium: '#fb923c',  // 均值 × 0.8 ~ 1.5
  low: '#fde68a',     // 均值 × 0.3 ~ 0.8
  idle: '#f1f5f9',    // < 均值 × 0.3 或为0
};

// Bitable API 分页大小
const PAGE_SIZE = 500;
```

- [ ] **Step 3: 创建 style.css — 基础样式**

创建 `heatmap/css/style.css`，包含：header、store-tabs、scene-grid（CSS Grid 卡片布局）、scene-card（带热力颜色）、modal 弹窗、loading/error 状态。具体样式实现时参考设计规格中的 UI 模型。

- [ ] **Step 4: 提交**

```bash
git add heatmap/
git commit -m "feat(heatmap): scaffold project with config and base HTML"
```

---

### Task 2: 飞书 Bitable API 客户端

**Files:**
- Create: `heatmap/js/api.js`

- [ ] **Step 1: 编写 Bitable API 客户端**

创建 `heatmap/js/api.js`，实现三个核心函数：

```javascript
'use strict';

/**
 * 获取飞书 access_token
 * 生产环境通过 JS-SDK 获取；本地开发可用个人访问令牌
 */
async function getAccessToken() {
  // TODO: 集成飞书 JS-SDK 认证
  // 开发阶段先返回空，用硬编码 token 测试
  return '';
}

/**
 * 分页拉取多维表全部记录
 * @param {string} tableId - 表 ID
 * @param {object} [filter] - 可选筛选条件
 * @returns {Promise<Array>} 所有记录数组
 */
async function fetchAllRecords(tableId, filter) {
  const token = await getAccessToken();
  const allRecords = [];
  let pageToken = null;
  let hasMore = true;

  while (hasMore) {
    const url = new URL(
      `https://open.feishu.cn/open-apis/bitable/v1/apps/${APP_TOKEN}/tables/${tableId}/records`
    );
    url.searchParams.set('page_size', PAGE_SIZE.toString());
    if (pageToken) url.searchParams.set('page_token', pageToken);

    const resp = await fetch(url.toString(), {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    const json = await resp.json();

    if (json.code !== 0) {
      throw new Error(`Bitable API error: ${json.msg}`);
    }

    const items = json.data.items || [];
    allRecords.push(...items);
    hasMore = json.data.has_more;
    pageToken = json.data.page_token;
  }

  return allRecords;
}

/**
 * 拉取执行output表的全部记录
 * @returns {Promise<Array>}
 */
async function fetchOutputRecords() {
  return fetchAllRecords(OUTPUT_TABLE_ID);
}

/**
 * 拉取影棚汇总表记录（可选，用于获取30天使用次数）
 * @param {string} tableId - 影棚表 ID
 * @returns {Promise<Array>}
 */
async function fetchStudioRecords(tableId) {
  if (!tableId) return [];
  return fetchAllRecords(tableId);
}
```

- [ ] **Step 2: 提交**

```bash
git add heatmap/js/api.js
git commit -m "feat(heatmap): add Bitable API client with pagination"
```

---

### Task 3: 数据聚合逻辑 + 单元测试

**Files:**
- Create: `heatmap/js/aggregator.js`
- Create: `heatmap/tests/aggregator.test.js`
- Create: `heatmap/package.json` (vitest 配置)

- [ ] **Step 1: 初始化测试环境**

创建 `heatmap/package.json`：

```json
{
  "name": "heatmap",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "vitest run"
  },
  "devDependencies": {
    "vitest": "^3.0.0"
  }
}
```

运行 `cd heatmap && npm install`。

- [ ] **Step 2: 编写聚合逻辑的失败测试**

创建 `heatmap/tests/aggregator.test.js`：

```javascript
import { describe, it, expect } from 'vitest';
import { aggregateByScene, isNewProduct, getHeatLevel } from '../js/aggregator.js';

describe('aggregateByScene', () => {
  it('should handle multi-select fields (array)', () => {
    const records = [
      { fields: { '滨江影棚': ['月蝶房', '爱豆房'], '小程序端': '已上架', '上新时间': Date.now() } },
      { fields: { '滨江影棚': ['月蝶房'], '小程序端': '待上架', '上新时间': Date.now() } },
    ];
    const result = aggregateByScene(records, '滨江影棚', 'multi');
    expect(result['月蝶房'].productCount).toBe(2);
    expect(result['月蝶房'].newProducts).toBe(2);
    expect(result['月蝶房'].statusDist['已上架']).toBe(1);
    expect(result['爱豆房'].productCount).toBe(1);
  });

  it('should handle single-select fields (string)', () => {
    const records = [
      { fields: { '下沙影棚': '复古房', '小程序端': '已上架', '上新时间': 0 } },
      { fields: { '下沙影棚': '复古房', '小程序端': '已下架', '上新时间': 0 } },
    ];
    const result = aggregateByScene(records, '下沙影棚', 'single');
    expect(result['复古房'].productCount).toBe(2);
    expect(result['复古房'].statusDist['已上架']).toBe(1);
    expect(result['复古房'].statusDist['已下架']).toBe(1);
  });

  it('should skip records with empty scene field', () => {
    const records = [
      { fields: { '滨江影棚': null, '小程序端': '已上架', '上新时间': 0 } },
      { fields: { '小程序端': '已上架' } },
    ];
    const result = aggregateByScene(records, '滨江影棚', 'multi');
    expect(Object.keys(result)).toHaveLength(0);
  });
});

describe('isNewProduct', () => {
  it('should return true for products within 90 days', () => {
    const record = { fields: { '上新时间': Date.now() - 30 * 86400000 } };
    expect(isNewProduct(record)).toBe(true);
  });

  it('should return false for products older than 90 days', () => {
    const record = { fields: { '上新时间': Date.now() - 100 * 86400000 } };
    expect(isNewProduct(record)).toBe(false);
  });

  it('should return false for missing date', () => {
    expect(isNewProduct({ fields: {} })).toBe(false);
  });
});

describe('getHeatLevel', () => {
  it('should classify heat levels correctly', () => {
    expect(getHeatLevel(60, 20)).toBe('high');   // 60 > 20*1.5=30
    expect(getHeatLevel(25, 20)).toBe('medium');  // 25 between 16 and 30
    expect(getHeatLevel(10, 20)).toBe('low');     // 10 between 6 and 16
    expect(getHeatLevel(2, 20)).toBe('idle');      // 2 < 6
  });
});
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd heatmap && npx vitest run
```

Expected: FAIL — `aggregateByScene`, `isNewProduct`, `getHeatLevel` 未定义。

- [ ] **Step 4: 实现聚合逻辑**

创建 `heatmap/js/aggregator.js`：

```javascript
'use strict';

/**
 * 判断是否为上新产品（上新时间在 NEW_PRODUCT_DAYS 天内）
 * @param {object} record - Bitable 记录
 * @returns {boolean}
 */
function isNewProduct(record) {
  const launchTime = record.fields['上新时间'];
  if (!launchTime) return false;
  // Bitable 日期字段返回毫秒时间戳
  const cutoff = Date.now() - NEW_PRODUCT_DAYS * 86400000;
  return launchTime > cutoff;
}

/**
 * 从记录中解析场景值（兼容单选字符串和多选数组）
 * @param {object} fields - 记录的 fields 对象
 * @param {string} fieldName - 影棚字段名
 * @param {string} fieldType - 'single' 或 'multi'
 * @returns {string[]} 场景名称数组
 */
function parseSceneValues(fields, fieldName, fieldType) {
  const value = fields[fieldName];
  if (!value) return [];
  if (fieldType === 'single') return [value];
  if (Array.isArray(value)) return value;
  return [];
}

/**
 * 解析小程序端状态
 * @param {string} statusText - 状态文本
 * @returns {string} 标准化状态：已上架/待上架/已下架/其他
 */
function parseStatus(statusText) {
  if (!statusText) return '其他';
  if (statusText.includes('已上架')) return '已上架';
  if (statusText.includes('待上架')) return '待上架';
  if (statusText.includes('已下架')) return '已下架';
  if (statusText.includes('待下架')) return '待下架';
  return '其他';
}

/**
 * 按场景聚合产品数据
 * @param {Array} records - 执行output表的全部记录
 * @param {string} fieldName - 影棚字段名（如 '滨江影棚'）
 * @param {string} fieldType - 'single' 或 'multi'
 * @returns {object} { [场景名]: { productCount, newProducts, statusDist, products } }
 */
function aggregateByScene(records, fieldName, fieldType) {
  const scenes = {};

  for (const record of records) {
    const sceneValues = parseSceneValues(record.fields, fieldName, fieldType);
    const status = parseStatus(record.fields['小程序端']);
    const isNew = isNewProduct(record);
    const productName = record.fields['方案名称'] || '未命名';

    for (const scene of sceneValues) {
      if (!scenes[scene]) {
        scenes[scene] = {
          productCount: 0,
          newProducts: 0,
          statusDist: { '已上架': 0, '待上架': 0, '已下架': 0, '待下架': 0, '其他': 0 },
          products: [],
        };
      }
      scenes[scene].productCount++;
      if (isNew) scenes[scene].newProducts++;
      if (scenes[scene].statusDist[status] !== undefined) {
        scenes[scene].statusDist[status]++;
      }
      scenes[scene].products.push({ name: productName, status, isNew });
    }
  }

  return scenes;
}

/**
 * 计算热力等级
 * @param {number} value - 当前值
 * @param {number} avg - 同门店平均值
 * @returns {string} 'high' | 'medium' | 'low' | 'idle'
 */
function getHeatLevel(value, avg) {
  if (avg === 0) return value > 0 ? 'medium' : 'idle';
  const ratio = value / avg;
  if (ratio >= 1.5) return 'high';
  if (ratio >= 0.8) return 'medium';
  if (ratio >= 0.3) return 'low';
  return 'idle';
}

// 导出（兼容浏览器全局变量和 ES module 测试）
if (typeof window !== 'undefined') {
  window.aggregateByScene = aggregateByScene;
  window.isNewProduct = isNewProduct;
  window.getHeatLevel = getHeatLevel;
}

export { aggregateByScene, isNewProduct, getHeatLevel, parseSceneValues, parseStatus };
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd heatmap && npx vitest run
```

Expected: ALL PASS

- [ ] **Step 6: 提交**

```bash
git add heatmap/js/aggregator.js heatmap/tests/ heatmap/package.json heatmap/package-lock.json
git commit -m "feat(heatmap): add data aggregation logic with tests"
```

---

### Task 4: 场景卡片网格渲染

**Files:**
- Create: `heatmap/js/renderer.js`
- Modify: `heatmap/css/style.css` (补充卡片样式)

- [ ] **Step 1: 实现场景卡片渲染器**

创建 `heatmap/js/renderer.js`：

```javascript
'use strict';

/**
 * 计算同门店所有场景的平均值
 * @param {object} scenes - aggregateByScene 的输出
 * @param {string} metric - 'productCount' 或其他数值字段
 * @returns {number}
 */
function calcAverage(scenes, metric) {
  const values = Object.values(scenes).map(s => s[metric] || 0);
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

/**
 * 渲染场景卡片网格
 * @param {HTMLElement} container - #sceneGrid 容器
 * @param {object} scenes - aggregateByScene 的输出
 * @param {string} storeName - 门店名称
 */
function renderSceneGrid(container, scenes, storeName) {
  container.innerHTML = '';
  const avgProductCount = calcAverage(scenes, 'productCount');

  // 按产品数降序排列
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

/**
 * 渲染门店选择标签
 * @param {HTMLElement} container - #storeTabs 容器
 * @param {object} storeConfig - STORE_CONFIG
 * @param {Function} onSelect - 切换门店的回调
 */
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

// 浏览器全局变量
if (typeof window !== 'undefined') {
  window.renderSceneGrid = renderSceneGrid;
  window.renderStoreTabs = renderStoreTabs;
}

export { renderSceneGrid, renderStoreTabs, calcAverage };
```

- [ ] **Step 2: 补充 CSS 卡片样式**

在 `heatmap/css/style.css` 中添加 `.scene-card`、`.heat-high/medium/low/idle`、`.scene-stats`、`.badge` 等样式。卡片使用 CSS Grid 自适应布局（`grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))`），热力颜色作为卡片背景色。

- [ ] **Step 3: 提交**

```bash
git add heatmap/js/renderer.js heatmap/css/style.css
git commit -m "feat(heatmap): add scene card grid renderer with heat colors"
```

---

### Task 5: 场景详情弹窗

**Files:**
- Create: `heatmap/js/detail-modal.js`

- [ ] **Step 1: 实现详情弹窗**

创建 `heatmap/js/detail-modal.js`：

```javascript
'use strict';

/**
 * 显示场景详情弹窗
 * @param {string} sceneName - 场景名
 * @param {string} storeName - 门店名
 * @param {object} sceneData - aggregateByScene 输出中该场景的数据
 * @param {number} [usageCount] - 近30天使用次数（来自影棚汇总表，可选）
 */
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

// 浏览器全局变量
if (typeof window !== 'undefined') {
  window.showDetailModal = showDetailModal;
  window.hideDetailModal = hideDetailModal;
}

export { showDetailModal, hideDetailModal };
```

- [ ] **Step 2: 提交**

```bash
git add heatmap/js/detail-modal.js
git commit -m "feat(heatmap): add scene detail modal with product list"
```

---

### Task 6: 主控制器 — 串联所有模块

**Files:**
- Create: `heatmap/js/app.js`

- [ ] **Step 1: 实现主控制器**

创建 `heatmap/js/app.js`，串联所有模块：

```javascript
'use strict';

(async function main() {
  // 状态
  let currentStore = '滨江';
  let allOutputRecords = [];
  let studioUsageData = {}; // { 场景名: 近30天使用次数 }

  // DOM 元素
  const sceneGrid = document.getElementById('sceneGrid');
  const storeTabs = document.getElementById('storeTabs');
  const loading = document.getElementById('loading');
  const errorEl = document.getElementById('error');

  // 显示加载状态
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

  // 加载数据
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

  // 渲染当前门店的场景热力图
  function renderCurrentStore() {
    const config = STORE_CONFIG[currentStore];
    if (!config) return;

    // 聚合数据
    const scenes = aggregateByScene(
      allOutputRecords,
      config.fieldName,
      config.fieldType
    );

    // 渲染卡片网格
    renderSceneGrid(sceneGrid, scenes, currentStore);

    // 高亮当前门店标签
    document.querySelectorAll('.store-tab').forEach(tab => {
      tab.classList.toggle('active', tab.textContent === currentStore);
    });

    // 绑定卡片点击事件
    sceneGrid.querySelectorAll('.scene-card').forEach(card => {
      card.addEventListener('click', () => {
        const sceneName = card.dataset.scene;
        const sceneData = scenes[sceneName];
        showDetailModal(sceneName, currentStore, sceneData);
      });
    });
  }

  // 切换门店
  function switchStore(storeName) {
    currentStore = storeName;
    renderCurrentStore();
  }

  // 初始化
  renderStoreTabs(storeTabs, STORE_CONFIG, switchStore);
  await loadData();
})();
```

- [ ] **Step 2: 提交**

```bash
git add heatmap/js/app.js
git commit -m "feat(heatmap): add main controller connecting all modules"
```

---

### Task 7: 本地验证 + 飞书认证集成

**Files:**
- Modify: `heatmap/js/api.js` (集成飞书 JS-SDK 认证)
- Modify: `heatmap/js/config.js` (填入实际的 APP_TOKEN 和 TABLE_ID)

- [ ] **Step 1: 填入飞书多维表的实际配置**

在飞书开放平台获取：
1. 多维表的 `app_token`（从多维表 URL 中提取）
2. 执行output表的 `table_id`（从 `也许文化工作进度表.base` 中已知为 `tblnNUnerqMCcjaz`）
3. 飞书企业自建应用的 `app_id` 和 `app_secret`

将值填入 `heatmap/js/config.js`。

- [ ] **Step 2: 集成飞书 JS-SDK 认证**

在 `heatmap/js/api.js` 中替换 `getAccessToken()` 实现：

```javascript
async function getAccessToken() {
  // 方案1：在飞书应用内运行时，通过 JS-SDK 获取
  if (window.h5sdk) {
    await window.h5sdk.ready();
    // JS-SDK 会自动在请求中注入认证头
    return null; // 不需要手动传 token
  }

  // 方案2：本地开发调试，使用 tenant_access_token
  // 通过飞书开放平台 API 获取（需要 app_id + app_secret）
  const resp = await fetch('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      app_id: APP_ID,
      app_secret: APP_SECRET,
    }),
  });
  const json = await resp.json();
  return json.tenant_access_token;
}
```

同时在 `index.html` 的 `<head>` 中添加飞书 JS-SDK：
```html
<script src="https://lf1-cdn-tos.bytegoofy.com/goofy/lark/op/h5sdk-1.9.24.js"></script>
```

- [ ] **Step 3: 本地浏览器打开验证**

```bash
cd heatmap && python3 -m http.server 8080
```

打开 `http://localhost:8080`，验证：
- 数据是否正常加载
- 场景卡片是否正确显示
- 门店切换是否正常
- 点击卡片弹窗是否正常
- 热力颜色是否合理

- [ ] **Step 4: 修复发现的问题并提交**

```bash
git add heatmap/
git commit -m "feat(heatmap): integrate Feishu auth and verify with real data"
```

---

### Task 8: 部署为飞书企业应用

**Files:**
- None (飞书开放平台配置)

- [ ] **Step 1: 飞书开放平台创建企业自建应用**

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 在"应用能力"中添加"H5 网页应用"
4. 配置"桌面端主页"URL（指向部署后的 heatmap 页面地址）
5. 在"权限管理"中申请 `bitable:app` 权限

- [ ] **Step 2: 部署 heatmap 静态文件**

选择以下任一方式：
- **飞书云文档**：创建文档，使用"嵌入网页"功能
- **Vercel/Netlify**：免费静态托管（推荐 `heatmap/` 目录直接部署）
- **公司内部服务器**：如果有可用的静态文件服务器

- [ ] **Step 3: 发布应用并验证**

1. 在飞书开放平台点击"创建版本"并发布
2. 从飞书工作台打开应用验证
3. 验证数据加载和交互功能正常

- [ ] **Step 4: 在多维表仪表盘添加入口**

1. 打开飞书多维表「也许文化工作进度表」
2. 进入仪表盘视图
3. 添加一个文本卡片或按钮组件，文字为"🗺️ 查看门店场景热力图"
4. 链接到飞书应用的 URL

- [ ] **Step 5: 最终提交**

```bash
git add -A
git commit -m "feat(heatmap): complete MVP - deploy as Feishu enterprise app"
```

---

## Summary

| Task | 内容 | 预估 |
|------|------|------|
| 1 | 项目骨架 + 常量配置 | 0.5h |
| 2 | Bitable API 客户端 | 1h |
| 3 | 聚合逻辑 + 单元测试 | 1.5h |
| 4 | 场景卡片网格渲染 | 1.5h |
| 5 | 场景详情弹窗 | 1h |
| 6 | 主控制器串联 | 0.5h |
| 7 | 本地验证 + 飞书认证 | 2h |
| 8 | 部署为飞书企业应用 | 1h |
| **Total** | | **~9h (1.5-2天)** |
