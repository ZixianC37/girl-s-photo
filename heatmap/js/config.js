'use strict';

// 飞书多维表配置（部署时替换为实际值）
const APP_TOKEN = '';       // 多维表 app_token
const OUTPUT_TABLE_ID = ''; // 执行output 表 table_id

// 门店配置：门店名 → { 品牌, 影棚字段名, 字段类型 }
const STORE_CONFIG = {
  '滨江': {
    brand: '麦芽纪',
    fieldName: '滨江影棚',
    fieldType: 'multi',
    tableId: 'tblGZA041E5o5PUU',
  },
  '下沙': {
    brand: '麦芽纪',
    fieldName: '下沙影棚',
    fieldType: 'single',
    tableId: 'tblIdWwwM2Gyu1fG',
  },
  '上海': {
    brand: '麦芽纪',
    fieldName: '上海影棚',
    fieldType: 'multi',
    tableId: null,
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

const BRAND_COLORS = {
  '麦芽纪': '#6366f1',
  '麦芽岛': '#10b981',
  '甜熊': '#f59e0b',
};

export const NEW_PRODUCT_DAYS = 90;

const HEAT_COLORS = {
  high: '#ef4444',
  medium: '#fb923c',
  low: '#fde68a',
  idle: '#f1f5f9',
};

const PAGE_SIZE = 500;
