/**
 * 模拟数据 — 基于真实的门店场景结构生成
 * 场景名称来自执行output表的实际选项
 */

function generateMockRecords() {
  const stores = {
    '滨江影棚': {
      type: 'multi',
      scenes: ['月蝶房','爱豆房','厨房','水吧房','月光房','婚纱房','钢琴房','日系房','妲已房','小空地','小熊房','二楼卧室房','公主房','外景','309无影墙','空地or背景款'],
    },
    '下沙影棚': {
      type: 'single',
      scenes: ['三角房','复古房','无影棚','香槟房','小房间','空地or背景款','下沙影棚'],
    },
    '上海影棚': {
      type: 'multi',
      scenes: ['301棚','无影棚','主棚','厨房空地','石膏房','公主房','花房','玩具','上海影棚'],
    },
    '西湖影棚': {
      type: 'multi',
      scenes: ['榻榻米','儿童区','沙发区','一楼厨房','木色露台','二楼厨房','二楼空地','阳台','大床区','柜子区','三楼沙发区','韩系房','外景','西湖影棚'],
    },
    '甜熊下沙影棚': {
      type: 'single',
      scenes: ['复古房','日系房','影棚1','影棚2','影棚3','厨房','小空地','大床房','石膏墙','空地或背景款','甜熊下沙影棚'],
    },
  };

  const statuses = ['已上架','已上架','已上架','已上架','待上架','待上架','已下架','已下架','已下架'];
  const productNames = [
    '拾花缘','乌梅子酱','人鱼搁浅','万物可爱','世纪古堡','一帘幽梦','一梦浮生',
    '云端星星人','人偶夜曲','人鱼之泪','仙蒂瑞拉','佳偶天成','乌梅子酱2.0',
    '花束般的恋爱','月光鸣奏曲','庭幕の夜','弥散梦境','彩带生日','撒花生日',
    '日杂画报','摇滚乐队','叛逆兔子','墨语','心动警告','奶油派对','小熊派对',
    '圣诞物语','叶语契','山月记','幻羽集','彩虹入场券','京の乙女','冬日恋歌',
    '失格反叛','奶白梦境','学院1990','大灰狼','十四行诗','冬季情书',
    'kitty喵','love','三只小熊','初雪','光羽之间','公主的下午茶',
    '东方兰','丝光倩影','元气满满','合家欢乐','卖火柴的baby','To宝宝',
  ];

  const now = Date.now();
  const records = [];
  let id = 0;

  for (const [fieldName, config] of Object.entries(stores)) {
    for (const scene of config.scenes) {
      // 每个场景分配 2-8 个产品
      const productCount = 2 + Math.floor(Math.random() * 7);
      for (let i = 0; i < productCount; i++) {
        id++;
        const daysAgo = Math.floor(Math.random() * 180); // 0-180天前
        const isNew = daysAgo < 90;
        const status = isNew
          ? (Math.random() > 0.3 ? '待上架' : '已上架')
          : statuses[Math.floor(Math.random() * statuses.length)];

        const record = {
          fields: {
            '方案名称': productNames[(id - 1) % productNames.length] + (id > productNames.length ? ` ${Math.ceil(id/productNames.length)}代` : ''),
            '小程序端': status,
            '上新时间': now - daysAgo * 86400000,
            '一级分类': ['生日系列','日韩少女','甜辣少女','国风少女','梦幻少女','暗黑少女','轻熟少女'][Math.floor(Math.random()*7)],
            '本次拍摄金额': Math.floor(Math.random() * 3000) + 500,
            '业绩': Math.floor(Math.random() * 3000) + 500,
          },
        };

        // 按字段类型赋值
        if (config.type === 'multi') {
          // 多选：主要场景 + 可能附带 1-2 个相邻场景
          const extra = Math.random() > 0.7 ? [config.scenes[Math.floor(Math.random()*config.scenes.length)]] : [];
          record.fields[fieldName] = [scene, ...extra];
        } else {
          record.fields[fieldName] = scene;
        }

        records.push(record);
      }
    }
  }

  return records;
}

// 生成并缓存
var MOCK_RECORDS = generateMockRecords();
console.log(`📦 模拟数据已生成: ${MOCK_RECORDS.length} 条记录`);
