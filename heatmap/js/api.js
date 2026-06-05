'use strict';

/**
 * 数据拉取 — 开发模式使用模拟数据，生产模式走飞书 API
 */

var USE_MOCK = true; // 改为 false 后走真实 API

/**
 * 拉取执行output表的全部记录
 * @returns {Promise<Array>}
 */
async function fetchOutputRecords() {
  if (USE_MOCK && typeof MOCK_RECORDS !== 'undefined') {
    console.log('📦 使用模拟数据');
    return MOCK_RECORDS;
  }

  // 真实 API 调用（通过本地代理）
  return fetchAllRecords(OUTPUT_TABLE_ID);
}

/**
 * 分页拉取多维表全部记录（真实 API）
 */
async function fetchAllRecords(tableId) {
  const allRecords = [];
  let pageToken = null;
  let hasMore = true;

  while (hasMore) {
    let url = `/api/records/${tableId}?page_size=${PAGE_SIZE}`;
    if (pageToken) url += `&page_token=${pageToken}`;

    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`API 请求失败 (${resp.status})`);

    const json = await resp.json();
    if (json.code !== 0) throw new Error(`Bitable API 错误: ${json.msg}`);

    allRecords.push(...(json.data.items || []));
    hasMore = json.data.has_more;
    pageToken = json.data.page_token;
  }

  return allRecords;
}
