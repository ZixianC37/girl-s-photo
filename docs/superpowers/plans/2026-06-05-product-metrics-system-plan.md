# 产品指标体系实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 分阶段实施产品指标体系，从 Phase 0 数据校验到 Phase 4 闭环追踪，让产品表现看得见、可诊断、可追踪。

**Architecture:** 双轨并行——飞书多维表侧做数据聚合和仪表盘展示，热力图 Web 应用侧做可视化增强。飞书多维表作为指标计算的 Single Source of Truth，Web 应用从 API 拉取数据做可视化。

**Tech Stack:** 飞书多维表（仪表盘、公式、双向关联）、HTML/CSS/JS（热力图仪表盘）、Python（数据校验脚本）

**Spec:** `docs/superpowers/specs/2026-06-05-product-metrics-system-design.md`

---

## 文件结构

```
heatmap/
├── index.html                          # 修改：增加 L1 指标面板
├── css/style.css                       # 修改：增加指标卡片样式
├── js/
│   ├── config.js                       # 不变
│   ├── config-local.js                 # 不变
│   ├── mock-data.js                    # 修改：增加金额和上新时间字段
│   ├── api.js                          # 修改：增加 L1 指标 API
│   ├── aggregator.js                   # 修改：增加门店级聚合逻辑
│   ├── renderer.js                     # 修改：增加指标面板渲染
│   ├── detail-modal.js                 # 不变
│   └── app.js                          # 修改：增加 L1 指标加载
scripts/
├── phase0_validate_mapping.py          # 新建：Phase 0 数据映射校验脚本
```

飞书多维表改造（在飞书 UI 中操作）：

```
执行output 表（已有）        → 新增字段、修改仪表盘
产品决策日志表（Phase 4 新建） → 新建整张表
```

---

## Phase 0：数据映射校验

> **前置条件**：需要访问飞书多维表「也许文化工作进度表」的管理权限。
> **预计耗时**：1-2 天。

### Task 0.1：编写数据映射校验脚本

**Files:**
- Create: `scripts/phase0_validate_mapping.py`

- [ ] **Step 1: 编写校验脚本**

该脚本通过飞书 API 拉取数据，自动比对映射关系。

```python
#!/usr/bin/env python3
"""Phase 0: 校验日拍摄清单.拍摄风格 ↔ 执行output.方案名称 的映射关系"""
import json
import urllib.request
import sys
import os

# 从 config-local.js 读取凭证（复用 heatmap/server.py 的逻辑）
APP_TOKEN = 'LCHzbZfDhaaSX4s4NAucQ8KPnDc'

def load_credentials():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'heatmap', 'js', 'config-local.js')
    app_id, app_secret = '', ''
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if 'FEISHU_APP_ID' in line and 'cli_' in line:
                    app_id = line.split("'")[1]
                elif 'FEISHU_APP_SECRET' in line and 'HsH' in line:
                    app_secret = line.split("'")[1]
    return app_id, app_secret

def get_token():
    app_id, app_secret = load_credentials()
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    data = json.dumps({'app_id': app_id, 'app_secret': app_secret}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    return result['tenant_access_token']

def fetch_all_records(table_id, token):
    all_records = []
    page_token = None
    while True:
        url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records?page_size=500'
        if page_token:
            url += f'&page_token={page_token}'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        items = data.get('data', {}).get('items', [])
        all_records.extend(items)
        if not data.get('data', {}).get('has_more'):
            break
        page_token = data.get('data', {}).get('page_token')
    return all_records

def validate_mapping():
    token = get_token()
    print(f"✅ Token 获取成功")

    # 1. 拉取执行output的所有方案名称
    # 表 ID 从 config.js 的 OUTPUT_TABLE_ID 获取
    output_table = 'tblnNUnerqMCcjaz'
    print(f"\n📋 拉取执行output表数据...")
    output_records = fetch_all_records(output_table, token)
    output_names = set()
    for r in output_records:
        name = r.get('fields', {}).get('方案名称')
        if name:
            if isinstance(name, list):
                for n in name:
                    output_names.add(str(n).get('text', str(n)) if isinstance(n, dict) else str(n))
            else:
                output_names.add(str(name))
    print(f"   执行output 方案名称数: {len(output_names)}")

    # 2. 拉取各门店日拍摄清单的拍摄风格选项
    store_tables = {
        '麦芽纪滨江': 'tblGZA041E5o5PUU',
        '麦芽纪下沙': 'tblIdWwwM2Gyu1fG',
        '甜熊下沙': 'tblV3qt3aDNz6663',
    }
    # 注意：上述 table_id 来自 config.js，仅为部分门店。
    # 实际使用时需要补全所有门店的 table_id。

    all_styles = {}  # store_name -> set of styles
    for store_name, table_id in store_tables.items():
        print(f"\n📋 拉取 {store_name} 日拍摄清单...")
        try:
            records = fetch_all_records(table_id, token)
            styles = set()
            for r in records:
                style = r.get('fields', {}).get('拍摄风格')
                if style:
                    if isinstance(style, list):
                        for s in style:
                            styles.add(str(s))
                    else:
                        styles.add(str(style))
            all_styles[store_name] = styles
            print(f"   {store_name} 拍摄风格数: {len(styles)}")
        except Exception as e:
            print(f"   ⚠️ {store_name} 拉取失败: {e}")
            all_styles[store_name] = set()

    # 2.5 校验日拍摄清单中的金额字段
    print("\n" + "="*60)
    print("💰 金额字段校验（本次拍摄金额）")
    print("="*60)
    amount_fields = ['本次拍摄金额', '应收全额', '前期定金', '尾款-微信', '尾款-支付宝']
    for store_name, table_id in store_tables.items():
        try:
            records = fetch_all_records(table_id, token)
            total = len(records)
            has_amount = 0
            amount_sum = 0
            for r in records:
                amount = r.get('fields', {}).get('本次拍摄金额')
                if amount and isinstance(amount, (int, float)):
                    has_amount += 1
                    amount_sum += amount
            rate = has_amount / total * 100 if total else 0
            print(f"  {store_name}: {has_amount}/{total} 条有金额 ({rate:.1f}%), 总金额={amount_sum:,.0f}")
        except Exception as e:
            print(f"  {store_name}: 校验失败 {e}")

    # 3. 交叉比对
    print("\n" + "="*60)
    print("📊 映射校验结果")
    print("="*60)

    for store_name, styles in all_styles.items():
        if not styles:
            continue
        matched = styles & output_names
        unmatched = styles - output_names
        rate = len(matched) / len(styles) * 100 if styles else 0

        print(f"\n🏪 {store_name}")
        print(f"   拍摄风格总数: {len(styles)}")
        print(f"   匹配率: {rate:.1f}% ({len(matched)}/{len(styles)})")

        if unmatched:
            print(f"   ⚠️ 未匹配的风格 ({len(unmatched)}个):")
            for s in sorted(unmatched)[:20]:
                print(f"      - {s}")

    # 4. 校验上新时间字段完整性
    print("\n" + "="*60)
    print("📅 上新时间字段校验")
    print("="*60)
    total = 0
    has_launch_time = 0
    no_launch_time = []
    for r in output_records:
        status = r.get('fields', {}).get('小程序端', '')
        if '已上架' in str(status):
            total += 1
            launch_time = r.get('fields', {}).get('上新时间')
            if launch_time:
                has_launch_time += 1
            else:
                name = r.get('fields', {}).get('方案名称', '未知')
                no_launch_time.append(str(name))

    rate = has_launch_time / total * 100 if total else 0
    print(f"已上架产品总数: {total}")
    print(f"有上新时间: {has_launch_time} ({rate:.1f}%)")
    print(f"缺少上新时间: {len(no_launch_time)}")
    if no_launch_time:
        print("缺少上新时间的产品:")
        for n in no_launch_time[:10]:
            print(f"  - {n}")

    # 5. 结论
    print("\n" + "="*60)
    print("🎯 Phase 0 结论")
    print("="*60)
    # 综合评估（取所有门店映射率的最低值）
    rates = []
    for store_name, styles in all_styles.items():
        if styles:
            r = len(styles & output_names) / len(styles) * 100
            rates.append(r)
    min_rate = min(rates) if rates else 0
    avg_rate = sum(rates) / len(rates) if rates else 0

    if min_rate >= 90:
        print(f"✅ 最低映射率 {min_rate:.1f}% ≥ 90% → 可直接进入 Phase 1")
    elif min_rate >= 80:
        print(f"⚠️ 最低映射率 {min_rate:.1f}% (80-90%) → 需建立映射对照表后进入 Phase 1")
    else:
        print(f"❌ 最低映射率 {min_rate:.1f}% < 80% → 需先修复数据结构")

if __name__ == '__main__':
    validate_mapping()
```

- [ ] **Step 2: 运行校验脚本**

Run: `cd /Users/chenzixian/Downloads/写真行业 && python3 scripts/phase0_validate_mapping.py`

Expected: 输出各门店映射率和上新时间完整性报告

> **注意**：脚本中的 `store_tables` 字典需要补全所有门店的 table_id。当前只包含了 config.js 中已知的3个。其余门店的 table_id 需要从飞书多维表的 URL 中获取。

- [ ] **Step 3: 根据结果决策**

根据映射率决定后续路径：
- ≥ 90%：直接进入 Phase 1
- 80-90%：在飞书多维表中新建「拍摄风格映射表」，记录别名→标准名的映射
- < 80%：暂停，与用户讨论数据结构问题

- [ ] **Step 4: Commit**

```bash
git add scripts/phase0_validate_mapping.py
git commit -m "feat: add Phase 0 data mapping validation script"
```

---

## Phase 1：基础经营指标

> **前置条件**：Phase 0 校验通过。
> **预计耗时**：3-5 天。
> **涉及两部分**：(A) 飞书多维表仪表盘配置 (B) 热力图 Web 应用集成。

### Task 1A：飞书多维表 — L1 仪表盘配置

> 以下操作全部在飞书多维表 Web UI 中完成。每一步都标注了具体的操作路径。

### ⚠️ 飞书多维表公式语法说明

飞书多维表公式的语法类似 Excel，但有差异。以下关键点需要注意：

1. **字段引用**：直接写中文字段名，如 `上新时间`，不需要方括号或引号
2. **日期函数**：`TODAY()` 返回今天日期；`DATETODATE(开始日期, 结束日期)` 返回天数差
3. **条件函数**：`IF(条件, 真值, 假值)`；多层嵌套用 `IFS(条件1, 值1, 条件2, 值2, ..., 默认值)`
4. **空值处理**：用 `ISNULL()` 或 `=""` 判断空值；日期字段为空时 `> 0` 可能不生效，建议用 `NOT(ISNULL(上新时间))`
5. **多选字段**：一级分类是多选字段，在公式中不能直接用于分组。仪表盘图表遇到多选字段时会自动展开（每个选项各计一次）
6. **公式调试**：在公式编辑器中可以看到实时预览。如果公式报错，检查字段名是否完全匹配（区分大小写和空格）

**回滚指引**：如果新增公式字段导致问题，可以直接删除该字段（右键列头 → 删除字段），不影响其他数据。公式字段是虚拟的，不存储实际数据，删除是安全的。

**公式验证声明**：以上公式基于飞书多维表格的常见公式语法编写，但未在真实环境中测试验证。实际操作时，请先在公式编辑器中输入并检查实时预览是否正确。如果函数名不对（如 `DATETODATE` 可能实际是 `DATEDIF`），飞书编辑器会标红提示，请根据提示调整。建议先在测试记录上验证公式正确后再批量应用。

- [ ] **Step 1: 在执行output表中确认现有公式字段**

操作路径：飞书多维表 → 也许文化工作进度表 → 执行output 表 → 切换到「表格视图」

需要确认以下字段已存在且公式正确：
- `滨江店近三十天拍摄量`（公式字段，类型 20）
- `下沙店近三十天拍摄量`（公式字段，类型 20）
- `下沙甜熊近三十天拍量`（公式字段，类型 20）
- `上新时间`（日期字段，类型 5）
- `小程序端`（单选字段，类型 3）
- `一级分类`（多选字段，类型 4）

记录这些字段的实际情况（存在/不存在/公式内容），后续步骤依赖这些字段。

- [ ] **Step 2: 在执行output表中新增生命周期天数公式字段**

操作路径：执行output 表 → 点击最右侧「+」号 → 添加字段

配置：
- **字段名称**：`生命周期天数`
- **字段类型**：公式
- **公式内容**：

```
IF(NOT(ISNULL(上新时间)), DATETODATE(上新时间, TODAY()), "")
```

> **飞书公式说明**：
> - `NOT(ISNULL(上新时间))` 判断上新时间是否非空（比 `> 0` 更可靠）
> - `DATETODATE(上新时间, TODAY())` 返回从上新时间到今天的天数差
> - 如果公式编辑器报错，尝试用 `IFERROR(DATETODATE(上新时间, TODAY()), "")` 包裹
> - 验证方法：保存后，已知上架日期的产品应显示天数（如「120」），未填上新时间的显示空白

验证：保存后，已有上新时间的产品应该显示一个数字（如「120」表示上架120天）。

- [ ] **Step 3: 在执行output表中新增生命周期阶段公式字段**

操作路径：同上，继续添加字段

配置：
- **字段名称**：`生命周期阶段`
- **字段类型**：公式
- **公式内容**：

```
IF(生命周期天数 = "", "",
  IF(生命周期天数 <= 30, "🔥爆发期",
    IF(生命周期天数 <= 90, "⚡稳定期",
      IF(生命周期天数 <= 180, "📉衰退期", "🏷️长尾期")
    )
  )
)
```

验证：检查不同上架时间的产品显示正确阶段标签。

- [ ] **Step 4: 在执行output表中新增是否30日新品公式字段**

配置：
- **字段名称**：`是否30日新品`
- **字段类型**：公式
- **公式内容**：

```
IF(AND(上新时间 > 0, 生命周期天数 <= 30), "是", "否")
```

验证：近30天上新的产品显示「是」，其余显示「否」。

- [ ] **Step 5: 在执行output表中新增生命周期天数公式字段（如已有则跳过）**

> ⚠️ 如果执行output 表的「近三十天拍摄量」公式已经是正确的，则不需要新建。这一步是为了确认这些字段能正常工作。

检查现有公式字段 `滨江店近三十天拍摄量` 的公式内容是否正确引用了日拍摄清单。如果该字段返回的是数字而非空值，说明公式正常。

- [ ] **Step 6: 创建 L1 经营指标仪表盘**

操作路径：飞书多维表 → 也许文化工作进度表 → 左侧导航点击「+ 新建仪表盘」→ 输入名称「产品经营指标 L1」

在仪表盘中添加以下**图表卡片**：

**卡片 1：产品点拍排行 TOP20**
- 图表类型：条形图（水平）
- 数据源：执行output 表
- X轴：方案名称
- Y轴：滨江店近三十天拍摄量（求和）
- 排序：降序，取前20
- 筛选：小程序端 = 已上架

**卡片 2：30日新品点拍占比（全局）**
- 图表类型：饼图
- 数据源：执行output 表
- 分组：是否30日新品
- 值：滨江店近三十天拍摄量（求和）+ 下沙店近三十天拍摄量（求和）
- 筛选：小程序端 = 已上架
- 注意：此处只展示有拍摄量公式字段的门店（滨江、下沙、甜熊下沙），其他门店数据暂缺

**卡片 3：各生命周期阶段产品数量**
- 图表类型：柱状图
- 数据源：执行output 表
- X轴：生命周期阶段
- Y轴：记录数（计数）
- 筛选：小程序端 = 已上架

**卡片 4：僵尸产品列表**
- 图表类型：表格
- 数据源：执行output 表
- 显示字段：方案名称、一级分类、上新时间、生命周期天数、小程序端
- 筛选：小程序端 包含 "已上架"
- 额外说明：由于各门店拍摄量字段是独立的公式字段，飞书仪表盘的筛选条件只能按单字段筛选。建议先筛选「滨江店近三十天拍摄量 = 0」查看滨江的僵尸产品，再换字段查其他门店。如果需要跨门店 AND 逻辑，需要创建一个「总拍摄量」公式字段。

**卡片 5：各一级分类的点拍量对比**
- 图表类型：柱状图（堆叠）
- 数据源：执行output 表
- X轴：一级分类
- Y轴：近三十天拍摄量（求和）
- 颜色分组：是否30日新品
- ⚠️ **多选字段注意**：一级分类是多选字段（一个产品可属于多个分类）。飞书仪表盘会自动将多选值展开（如产品同时属于「日韩少女」和「甜辣少女」，两个分类各计一次）。这意味着分类点拍量之和 > 全局总点拍量是正常的，不是数据错误。

- [ ] **Step 7: 验证仪表盘数据**

在仪表盘界面检查：
1. 数据是否正常加载（不是全0或全空）
2. 数字是否合理（如点拍排行 TOP1 的产品拍了几十次是正常的，拍了几千次可能是公式有问题）
3. 僵尸产品列表是否有数据（通常会有一些）

---

### Task 1B：热力图 Web 应用 — L1 指标集成

**Files:**
- Modify: `heatmap/js/mock-data.js` — 增加金额字段
- Modify: `heatmap/js/aggregator.js` — 增加门店级聚合
- Modify: `heatmap/js/renderer.js` — 增加 L1 指标面板
- Modify: `heatmap/js/app.js` — 集成 L1 指标

- [ ] **Step 1: 更新 mock-data.js 增加金额字段**

在 `generateMockRecords()` 函数中，找到 `record.fields` 的构建部分，在 `'一级分类'` 之后增加金额字段：

```javascript
// 在 record.fields 对象中增加（紧跟在 '一级分类' 字段之后）：
record.fields['本次拍摄金额'] = Math.floor(Math.random() * 3000) + 500; // 500-3500元随机金额
```

同时确保 `上新时间` 字段在 mock 数据中已正确生成（当前代码中已有 `now - daysAgo * 86400000`）。

- [ ] **Step 2: 更新 aggregator.js 增加门店级聚合函数**

在文件末尾（`if (typeof window !== 'undefined')` 之前）增加门店级聚合函数：

```javascript
/**
 * 门店级 L1 经营指标汇总
 * @param {Array} records - 执行output的全部记录
 * @param {string} fieldName - 影棚字段名（如「滨江影棚」）
 * @param {string} fieldType - 字段类型（'single' 或 'multi'）
 * @returns {Object} 门店级汇总指标
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
    var amount = Number(r.fields['本次拍摄金额']) || 0;
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
```

在全局导出中增加（在 `window.getHeatLevel = getHeatLevel;` 之后）：

```javascript
window.aggregateStoreMetrics = aggregateStoreMetrics;
```

- [ ] **Step 3: 更新 renderer.js 的 renderSummary，展示门店级 L1 指标**

修改 `renderSummary` 函数签名，增加 `storeMetrics` 参数：

```javascript
function renderSummary(scenes, storeName, storeMetrics) {
  var bar = document.getElementById('summaryBar');
  if (!bar) return;

  // 场景级统计
  var totalProducts = 0;
  var totalNew = 0;
  var sceneCount = Object.keys(scenes).length;
  var hotCount = 0;
  var avgProductCount = calcAverage(scenes, 'productCount');

  Object.values(scenes).forEach(function(s) {
    totalProducts += s.productCount;
    totalNew += s.newProducts;
    if (s.productCount >= avgProductCount * 1.5) hotCount++;
  });

  var avgPerScene = sceneCount > 0 ? (totalProducts / sceneCount).toFixed(1) : '0';

  // 构建 HTML：场景级指标 + 门店级 L1 指标
  var html =
    '<div class="summary-item">' +
      '<span class="summary-value">' + sceneCount + '</span>' +
      '<span class="summary-label">场景</span>' +
    '</div>' +
    '<div class="summary-item">' +
      '<span class="summary-value">' + totalProducts + '</span>' +
      '<span class="summary-label">关联产品</span>' +
    '</div>' +
    '<div class="summary-item">' +
      '<span class="summary-value accent">' + totalNew + '</span>' +
      '<span class="summary-label">上新产品</span>' +
    '</div>' +
    '<div class="summary-item">' +
      '<span class="summary-value">' + avgPerScene + '</span>' +
      '<span class="summary-label">场均产品</span>' +
    '</div>' +
    '<div class="summary-item">' +
      '<span class="summary-value">' + hotCount + '</span>' +
      '<span class="summary-label">热门场景</span>' +
    '</div>';

  // 门店级 L1 指标（如果 storeMetrics 有数据）
  if (storeMetrics) {
    html +=
      '<div class="summary-divider"></div>' +
      '<div class="summary-item">' +
        '<span class="summary-value">¥' + (storeMetrics.totalRevenue / 10000).toFixed(1) + '万</span>' +
        '<span class="summary-label">总成交</span>' +
      '</div>' +
      '<div class="summary-item">' +
        '<span class="summary-value">¥' + storeMetrics.avgPrice + '</span>' +
        '<span class="summary-label">客单价</span>' +
      '</div>' +
      '<div class="summary-item">' +
        '<span class="summary-value accent">' + storeMetrics.newProductRevenueRatio + '%</span>' +
        '<span class="summary-label">30日新品占比</span>' +
      '</div>' +
      '<div class="summary-item">' +
        '<span class="summary-value">' + storeMetrics.activeProductCount + '</span>' +
        '<span class="summary-label">活跃产品</span>' +
      '</div>';
  }

  bar.innerHTML = html;
}
```

- [ ] **Step 4: 更新 app.js 调用门店级聚合**

修改 `renderCurrentStore` 函数，在调用 `renderSceneGrid` 的位置增加门店级指标计算：

在 `app.js` 的 `renderCurrentStore` 函数中，找到：

```javascript
renderSceneGrid(sceneGrid, scenes, currentStore);
```

在其之前增加：

```javascript
// 计算门店级 L1 指标
var storeMetrics = aggregateStoreMetrics(
  allOutputRecords,
  config.fieldName,
  config.fieldType
);
```

然后将 `renderSceneGrid` 调用改为：

```javascript
renderSceneGrid(sceneGrid, scenes, currentStore, storeMetrics);
```

同时更新 `renderer.js` 中的 `renderSceneGrid` 函数签名，把 `storeMetrics` 传给 `renderSummary`：

```javascript
function renderSceneGrid(container, scenes, storeName, storeMetrics) {
  // ... 现有代码不变 ...
  // 在最后调用 renderSummary 时传入 storeMetrics
  renderSummary(scenes, storeName, storeMetrics);
}
```

- [ ] **Step 5: 更新 style.css 增加分隔符样式**

在 `heatmap/css/style.css` 的 `.summary-label` 规则之后增加：

```css
.summary-divider {
  width: 1px;
  background: var(--border-subtle);
  align-self: stretch;
  margin: 0 0.5rem;
}
```

- [ ] **Step 6: 运行并验证**

Run: `cd /Users/chenzixian/Downloads/写真行业/heatmap && python3 server.py 9090`

打开 http://localhost:9090，检查：
- 摘要统计栏显示「场景 | 关联产品 | 上新产品 | 场均产品 | 热门场景 | ─ | 总成交 | 客单价 | 30日新品占比 | 活跃产品」
- 金额数据不为 0
- 浏览器控制台无报错

- [ ] **Step 7: Commit**

```bash
git add heatmap/js/mock-data.js heatmap/js/aggregator.js heatmap/js/renderer.js heatmap/js/app.js heatmap/css/style.css
git commit -m "feat: integrate L1 store-level metrics into heatmap dashboard"
```

---

## Phase 2：健康度分析

> **前置条件**：Phase 1 完成。
> **预计耗时**：1-2 周。

### Task 2A：飞书多维表 — 健康度评分字段

- [ ] **Step 1: 在执行output表中新增转化力评分公式字段**

配置：
- **字段名称**：`转化力评分`
- **字段类型**：公式
- **公式内容**：

```
IF(小程序端 = "已上架",
  LET(
    shoots, 滨江店近三十天拍摄量 + 下沙店近三十天拍摄量 + 下沙甜熊近三十天拍量,
    IF(shoots = 0, 1,
      IF(shoots >= 20, 5,
        IF(shoots >= 10, 4,
          IF(shoots >= 5, 3,
            IF(shoots >= 2, 2, 1)
          )
        )
      )
    )
  ),
  0
)
```

> **说明**：简化评分法——用绝对点拍数映射到 1-5 分。后续可升级为分类内百分位评分（需要高级公式或脚本）。

- [ ] **Step 2: 在执行output表中新增生命力评分公式字段**

配置：
- **字段名称**：`生命力评分`
- **字段类型**：公式
- **公式内容**：

```
IF(小程序端 = "已上架",
  IF(生命周期天数 = "", 1,
    IF(生命周期天数 <= 30, 5,
      IF(生命周期天数 <= 90, 4,
        IF(生命周期天数 <= 180, 2, 1)
      )
    )
  ),
  0
)
```

- [ ] **Step 3: 在执行output表中新增综合健康度公式字段**

配置：
- **字段名称**：`健康度评分`
- **字段类型**：公式
- **公式内容**：

```
IF(小程序端 = "已上架",
  (转化力评分 * 2 + 生命力评分) / 3,
  0
)
```

> **说明**：转化力权重 ×2（更重要的维度），生命力 ×1。引流力（Phase 3 加入）和营收力将在此公式中逐步加入。

- [ ] **Step 4: 更新 L1 仪表盘，增加健康度图表**

在「产品经营指标 L1」仪表盘中增加：

**卡片 6：产品健康度分布**
- 图表类型：饼图
- 数据源：执行output 表
- 分组：健康度评分（按 1-5 分桶）
- 筛选：小程序端 = 已上架

**卡片 7：生命周期阶段 × 健康度 散点**
- 图表类型：散点图（如果飞书支持）
- X轴：生命周期天数
- Y轴：转化力评分
- 数据源：执行output 表
- 筛选：小程序端 = 已上架

### Task 2B：热力图 Web 应用 — 健康度可视化

**Files:**
- Modify: `heatmap/js/aggregator.js` — 增加健康度评分计算
- Modify: `heatmap/js/renderer.js` — 卡片增加健康度标签
- Modify: `heatmap/css/style.css` — 健康度相关样式

- [ ] **Step 1: 在 aggregator.js 中增加健康度评分函数**

```javascript
function calcHealthScore(sceneData, avgProductCount) {
  // 转化力：基于产品数量相对平均值
  var conversionScore = avgProductCount > 0 ? sceneData.productCount / avgProductCount : 0;
  conversionScore = Math.min(5, Math.max(1, Math.round(conversionScore * 2.5)));

  // 生命力：基于新品占比
  var vitalityScore = sceneData.productCount > 0
    ? Math.min(5, Math.max(1, Math.round((sceneData.newProducts / sceneData.productCount) * 5 + 1)))
    : 1;

  // 综合评分（转化力权重×2）
  var overall = (conversionScore * 2 + vitalityScore) / 3;
  return {
    conversion: conversionScore,
    vitality: vitalityScore,
    overall: Math.round(overall * 10) / 10
  };
}
```

- [ ] **Step 2: 在 renderer.js 中集成健康度到卡片**

修改 `renderSceneGrid`，在卡片 HTML 中增加健康度标签。

- [ ] **Step 3: 运行验证并 Commit**

---

## Phase 3：引流归因

> **前置条件**：Phase 2 完成 + 运营团队协调完毕。
> **预计耗时**：1-2 周。
> **需要业务决策**：客资归因的录入方式。

### Task 3A：飞书多维表 — 客资归因字段

- [ ] **Step 1: 在新品追踪表中确认「链接」字段**

新品追踪表已有3个链接字段和3个发布人字段。确认这些链接是否指向公域内容（小红书帖子）。

- [ ] **Step 2: 评估是否在日拍摄清单中新增「来源产品」字段**

这需要门店录入，门店运营专家建议：
- 字段类型：单选（下拉选择）
- 选项列表：从执行output表自动同步
- 是否必填：否（非必填，减少门店负担）
- 默认值：空

**决策点**：此步骤需要用户确认是否在门店端增加此字段。

- [ ] **Step 3: 如确认新增，在各门店日拍摄清单表中添加字段**

操作路径：各门店日拍摄清单 → 添加字段 → 单选

配置：
- **字段名称**：`来源产品`
- **字段类型**：单选
- **选项**：手动录入前50个热门方案名称（后续可扩展）
- **是否必填**：否

- [ ] **Step 4: 更新执行output表增加引流力评分**

待客资归因数据积累1-2周后，新增引流力评分公式字段（公式待定，依赖实际数据分布）。

### Task 3B：热力图 Web 应用 — 引流浪费预警

- [ ] **Step 1: 在 aggregator.js 中增加引流力维度**

当来源产品数据可用后，增加引流力评分计算。

- [ ] **Step 2: 更新仪表盘异常面板**

增加 R5「引流浪费」异常检测。

---

## Phase 4：闭环管理

> **前置条件**：Phase 3 完成。
> **预计耗时**：1 周。

### Task 4A：飞书多维表 — 产品决策日志表

- [ ] **Step 1: 新建「产品决策日志」表**

操作路径：飞书多维表 → 也许文化工作进度表 → 左侧导航「+ 新建表格」→ 从空白创建 → 命名为「产品决策日志」

- [ ] **Step 2: 添加字段**

按以下顺序添加：

| 序号 | 字段名称 | 类型 | 配置 |
|------|----------|------|------|
| 1 | 方案名称 | 双向关联 | 关联到「执行output」，反向关联名称「决策记录」 |
| 2 | 决策类型 | 单选 | 选项：上新、下架、调整、场景迁移、价格调整 |
| 3 | 决策日期 | 日期 | 开启时间选择 |
| 4 | 决策原因 | 多行文本 | 默认 |
| 5 | 预期效果 | 多行文本 | 默认 |
| 6 | 决策人 | 单选 | 选项：莱、小水、灰灰、陈玄、绘绘、狗吉、小乐 |
| 7 | 关联异常 | 单选 | 选项：R1-僵尸、R2-遇冷、R3-衰退、R4-低收、R5-引流浪费、R6-经典款、R7-拥堵、无 |
| 8 | 效果评价 | 单选 | 选项：超预期、符合预期、低于预期、失败、待评估（默认） |

- [ ] **Step 3: 在仪表盘中增加决策追踪面板**

在「产品经营指标 L1」仪表盘中增加：

**卡片：近期决策列表**
- 图表类型：表格
- 数据源：产品决策日志
- 显示字段：方案名称、决策类型、决策日期、决策原因、效果评价
- 排序：决策日期 降序

---

## 飞书多维表改造汇总

> 所有需要你在飞书 UI 中操作的改动，按 Phase 汇总如下：

### 执行output 表新增字段汇总

| Phase | 字段名 | 类型 | 公式/配置 |
|-------|--------|------|-----------|
| 1 | 生命周期天数 | 公式 | `IF(上新时间 > 0, DATETODATE(TODAY(), 上新时间), "")` |
| 1 | 生命周期阶段 | 公式 | 嵌套 IF 映射到4个阶段 |
| 1 | 是否30日新品 | 公式 | `IF(AND(上新时间 > 0, 生命周期天数 <= 30), "是", "否")` |
| 2 | 转化力评分 | 公式 | 点拍数 → 1-5分映射 |
| 2 | 生命力评分 | 公式 | 生命周期天数 → 1-5分映射 |
| 2 | 健康度评分 | 公式 | `(转化力*2 + 生命力) / 3` |
| 3 | 引流力评分 | 公式 | 待定（依赖客资归因数据） |

### 新建表汇总

| Phase | 表名 | 用途 |
|-------|------|------|
| 0 | 拍摄风格映射表（条件性） | 拍摄风格↔方案名称映射 |
| 4 | 产品决策日志 | 决策记录和效果追踪 |

### 仪表盘汇总

| Phase | 仪表盘 | 新增卡片 |
|-------|--------|----------|
| 1 | 产品经营指标 L1 | 点拍TOP20、30日新品占比、生命周期分布、僵尸产品、分类对比 |
| 2 | 同上（扩展） | 健康度分布、散点图 |
| 4 | 同上（扩展） | 决策追踪表格 |
