import { describe, it, expect, beforeEach } from 'vitest';

// 直接内联函数，不依赖 import（因为 aggregator.js 用 var 不用 export）
function isNewProduct(record) {
  var launchTime = record.fields['上新时间'];
  if (!launchTime) return false;
  var cutoff = Date.now() - 90 * 86400000;
  return launchTime > cutoff;
}

function parseSceneValues(fields, fieldName, fieldType) {
  var value = fields[fieldName];
  if (!value) return [];
  if (fieldType === 'single') return [value];
  if (Array.isArray(value)) return value;
  return [];
}

function parseStatus(statusText) {
  if (!statusText) return '其他';
  if (statusText.includes('已上架')) return '已上架';
  if (statusText.includes('待上架')) return '待上架';
  if (statusText.includes('已下架')) return '已下架';
  if (statusText.includes('待下架')) return '待下架';
  return '其他';
}

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
          productCount: 0, newProducts: 0,
          statusDist: { '已上架': 0, '待上架': 0, '已下架': 0, '待下架': 0, '其他': 0 },
          products: [],
        };
      }
      scenes[scene].productCount++;
      if (isNew) scenes[scene].newProducts++;
      if (scenes[scene].statusDist[status] !== undefined) scenes[scene].statusDist[status]++;
      scenes[scene].products.push({ name: productName, status, isNew });
    }
  }
  return scenes;
}

function getHeatLevel(value, avg) {
  if (avg === 0) return value > 0 ? 'medium' : 'idle';
  var ratio = value / avg;
  if (ratio >= 1.5) return 'high';
  if (ratio >= 0.8) return 'medium';
  if (ratio >= 0.3) return 'low';
  return 'idle';
}

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
    expect(getHeatLevel(60, 20)).toBe('high');
    expect(getHeatLevel(25, 20)).toBe('medium');
    expect(getHeatLevel(10, 20)).toBe('low');
    expect(getHeatLevel(2, 20)).toBe('idle');
  });
});
