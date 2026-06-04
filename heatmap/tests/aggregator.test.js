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
    expect(getHeatLevel(60, 20)).toBe('high');
    expect(getHeatLevel(25, 20)).toBe('medium');
    expect(getHeatLevel(10, 20)).toBe('low');
    expect(getHeatLevel(2, 20)).toBe('idle');
  });
});
