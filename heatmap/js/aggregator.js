'use strict';

import { NEW_PRODUCT_DAYS } from './config.js';

/**
 * 判断是否为上新产品（上新时间在 NEW_PRODUCT_DAYS 天内）
 * @param {object} record - Bitable 记录
 * @returns {boolean}
 */
function isNewProduct(record) {
  const launchTime = record.fields['上新时间'];
  if (!launchTime) return false;
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
 * @param {string} statusText
 * @returns {string} 标准化状态
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
 * @param {string} fieldName - 影棚字段名
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

// Browser globals
if (typeof window !== 'undefined') {
  window.aggregateByScene = aggregateByScene;
  window.isNewProduct = isNewProduct;
  window.getHeatLevel = getHeatLevel;
}

export { aggregateByScene, isNewProduct, getHeatLevel, parseSceneValues, parseStatus };
