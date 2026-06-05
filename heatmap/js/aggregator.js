'use strict';

/**
 * 判断是否为上新产品（上新时间在 NEW_PRODUCT_DAYS 天内）
 */
function isNewProduct(record) {
  var launchTime = record.fields['上新时间'];
  if (!launchTime) return false;
  var cutoff = Date.now() - NEW_PRODUCT_DAYS * 86400000;
  return launchTime > cutoff;
}

/**
 * 从记录中解析场景值（兼容单选字符串和多选数组）
 */
function parseSceneValues(fields, fieldName, fieldType) {
  var value = fields[fieldName];
  if (!value) return [];
  if (fieldType === 'single') return [value];
  if (Array.isArray(value)) return value;
  return [];
}

/**
 * 解析小程序端状态
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
 */
function aggregateByScene(records, fieldName, fieldType) {
  var scenes = {};

  for (var i = 0; i < records.length; i++) {
    var record = records[i];
    var sceneValues = parseSceneValues(record.fields, fieldName, fieldType);
    var status = parseStatus(record.fields['小程序端']);
    var isNew = isNewProduct(record);
    var productName = record.fields['方案名称'] || '未命名';

    for (var j = 0; j < sceneValues.length; j++) {
      var scene = sceneValues[j];
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
      scenes[scene].products.push({ name: productName, status: status, isNew: isNew });
    }
  }

  return scenes;
}

/**
 * 计算热力等级
 */
function getHeatLevel(value, avg) {
  if (avg === 0) return value > 0 ? 'medium' : 'idle';
  var ratio = value / avg;
  if (ratio >= 1.5) return 'high';
  if (ratio >= 0.8) return 'medium';
  if (ratio >= 0.3) return 'low';
  return 'idle';
}

/**
 * 门店级 L1 经营指标汇总
 */
function aggregateStoreMetrics(records, fieldName, fieldType) {
  var totalPointShoot = 0;
  var totalRevenue = 0;
  var newProductRevenue = 0;
  var newProductPointShoot = 0;
  var activeProducts = {};
  var now = Date.now();
  var cutoff = now - 30 * 86400000;

  for (var i = 0; i < records.length; i++) {
    var r = records[i];
    var scenes = parseSceneValues(r.fields, fieldName, fieldType);
    if (scenes.length === 0) continue;

    var status = parseStatus(r.fields['小程序端']);
    if (status !== '已上架') continue;

    var launchTime = r.fields['上新时间'] || 0;
    var isNew = launchTime > cutoff;
    var amount = Number(r.fields['业绩']) || Number(r.fields['本次拍摄金额']) || 0;
    var productName = r.fields['方案名称'] || '';

    for (var j = 0; j < scenes.length; j++) {
      totalPointShoot++;
      totalRevenue += amount;
      activeProducts[productName] = true;
      if (isNew) {
        newProductPointShoot++;
        newProductRevenue += amount;
      }
    }
  }

  var productCount = Object.keys(activeProducts).length;

  return {
    totalPointShoot: totalPointShoot,
    totalRevenue: totalRevenue,
    avgPrice: totalPointShoot > 0 ? Math.round(totalRevenue / totalPointShoot) : 0,
    newProductPointShoot: newProductPointShoot,
    newProductRevenue: newProductRevenue,
    newProductRevenueRatio: totalRevenue > 0 ? (newProductRevenue / totalRevenue * 100).toFixed(1) : '0.0',
    newProductPointShootRatio: totalPointShoot > 0 ? (newProductPointShoot / totalPointShoot * 100).toFixed(1) : '0.0',
    activeProductCount: productCount
  };
}

// 浏览器全局变量
if (typeof window !== 'undefined') {
  window.aggregateByScene = aggregateByScene;
  window.isNewProduct = isNewProduct;
  window.getHeatLevel = getHeatLevel;
  window.aggregateStoreMetrics = aggregateStoreMetrics;
}
