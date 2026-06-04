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
