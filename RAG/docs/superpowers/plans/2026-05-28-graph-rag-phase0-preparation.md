# GraphRAG 阶段0：并行准备期 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 并行完成 GraphRAG 知识学习和飞书数据分析，产出知识-数据映射文档和实战 Skill 集。

**Architecture:** 两条并行工作流——视频知识提取流和数据结构分析流——最终汇聚为知识-数据映射文档。知识学习过程中提炼的 Skill 用于后续阶段的执行约束。

**Tech Stack:** Python (数据处理/脚本), Neo4j (目标图数据库), LlamaIndex (RAG 框架), Claude API (LLM)

---

## 文件结构

```
RAG/
├── docs/
│   ├── knowledge/                        # 知识学习产出
│   │   ├── 01-graphrag-concepts.md       # GraphRAG 核心概念
│   │   ├── 02-tech-stack-comparison.md   # 技术选型对比
│   │   ├── 03-practical-steps.md         # 实战落地步骤
│   │   └── 04-pitfalls-best-practices.md # 坑与最佳实践
│   ├── data/                             # 数据分析产出
│   │   ├── feishu-tables-overview.md     # 飞书表格概览
│   │   ├── entity-relation-analysis.md   # 实体关系分析
│   │   └── data-quality-report.md        # 数据质量报告
│   ├── knowledge-data-mapping.md         # 知识-数据映射文档（最终产出）
│   └── skills/                           # Skill 可读副本
│       ├── skill-graph-schema-design.md
│       ├── skill-entity-extraction-pipeline.md
│       ├── skill-graph-query-engine.md
│       └── skill-rag-comparison-test.md
├── data/                                 # 飞书原始数据（CSV/Excel）
│   └── (用户导出的表格文件)
├── .claude/skills/                       # Claude Code 可执行的 Skill
│   ├── skill-graph-schema-design.md
│   ├── skill-entity-extraction-pipeline.md
│   ├── skill-graph-query-engine.md
│   └── skill-rag-comparison-test.md
└── scripts/                              # 辅助脚本
    └── analyze_feishu_data.py            # 飞书数据分析脚本
```

---

## Task 1: 项目结构初始化

**Files:**
- Create: `docs/knowledge/` 目录
- Create: `docs/data/` 目录
- Create: `data/` 目录
- Create: `scripts/` 目录

- [ ] **Step 1: 创建目录结构**

```bash
cd /Users/chenzixian/Downloads/写真行业/RAG
mkdir -p docs/knowledge docs/data data scripts
```

- [ ] **Step 1.5: 创建 .gitignore**

防止将飞书原始数据和敏感信息提交到 git：

```bash
cat > .gitignore << 'EOF'
# 飞书原始数据（可能含敏感信息）
data/*.csv
data/*.xlsx
data/*.xls
data/*.json
# Python
__pycache__/
*.pyc
.venv/
EOF
```

- [ ] **Step 2: 验证目录创建**

```bash
ls -R docs/ data/ scripts/
```
Expected: 显示所有创建的目录

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "chore: initialize project directory structure for Phase 0"
```

---

## Task 2: 视频知识提取（每个视频重复）

**前提：** 用户提供 B站/YouTube 视频链接。此 Task 需要针对每个视频链接重复执行。

**Files:**
- Create: `docs/knowledge/` 下的知识文档（根据视频内容分类）

- [ ] **Step 1: 抓取视频页面内容**

使用 WebFetch/mcp__web_reader__webReader 工具抓取视频链接页面，提取：
- 视频标题
- 视频 description/简介
- 分P 信息
- 字幕/文字稿（如果可获取）

如果文字稿不可用：
1. 记录缺失的视频信息到 `docs/knowledge/transcript-gaps.md`
2. 向用户发送提示：`"请为 [视频标题] 提供关键笔记（Markdown 格式），包括：核心概念、技术栈、实战步骤、注意事项"`
3. 用户提供的笔记直接整合到对应的知识文档中

- [ ] **Step 2: 归纳视频核心知识点**

将提取的内容整理为结构化笔记，分类归入以下文档：
- `docs/knowledge/01-graphrag-concepts.md` — GraphRAG 核心概念
- `docs/knowledge/02-tech-stack-comparison.md` — 技术选型对比
- `docs/knowledge/03-practical-steps.md` — 实战落地步骤
- `docs/knowledge/04-pitfalls-best-practices.md` — 坑与最佳实践

每个知识点格式：
```
### [知识点标题]
- 来源：[视频标题] ([时间戳])
- 内容：[核心内容]
- 实战意义：[对写真行业 GraphRAG 的指导意义]
```

- [ ] **Step 3: 检查知识文档完整性**

验证每个文档至少覆盖：
- 01: 实体、关系、社区检测、查询策略（global/local）
- 02: 至少对比 Neo4j vs NebulaGraph、LlamaIndex vs LangChain
- 03: 至少覆盖数据准备、Schema 设计、实体提取、查询构建步骤
- 04: 至少 3 个常见坑和对应最佳实践

如果不完整，标记缺失内容，等待后续视频补充。

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge/
git commit -m "docs: add knowledge notes from [视频标题]"
```

---

## Task 3: 知识综合与 Skill 提炼

**前提：** Task 2 中所有视频已完成处理，或已有足够的知识积累。

**Files:**
- Read: `docs/knowledge/01-04` 所有文档
- Create: `.claude/skills/skill-graph-schema-design.md`
- Create: `.claude/skills/skill-entity-extraction-pipeline.md`
- Create: `.claude/skills/skill-graph-query-engine.md`
- Create: `.claude/skills/skill-rag-comparison-test.md`
- Create: `docs/skills/` 下的对应副本

- [ ] **Step 1: 综合知识文档**

阅读所有知识文档，检查一致性和完整性。如有冲突或遗漏，记录待确认事项。

- [ ] **Step 2: 识别实战关键环节**

从知识文档中提取实战落地所需的关键步骤，映射为 Skill。预期至少包含：

| Skill | 对应实战环节 |
|-------|------------|
| graph-schema-design | 图谱 Schema 设计（实体标签、关系类型、属性定义） |
| entity-extraction-pipeline | 实体/关系提取流程（LLM + 规则） |
| graph-query-engine | 查询引擎搭建（Cypher + 向量检索） |
| rag-comparison-test | GraphRAG vs 传统 RAG 对比验证 |

- [ ] **Step 3: 编写每个 Skill 文件**

每个 Skill 文件格式：

```markdown
---
name: [skill-name]
description: [一句话描述]
---

# [Skill Name]

## 输入
- [需要什么前置条件和数据]

## 输出
- [完成后应该产出什么]

## 执行步骤
1. [具体步骤]
2. ...

## 检查清单
- [ ] [检查项1]
- [ ] [检查项2]

## 质量验收标准
- [验收条件]

## 常见问题
- [从视频中学习的坑和解决方案]
```

基于 `docs/knowledge/03-practical-steps.md` 和 `04-pitfalls-best-practices.md` 的内容填充每个 Skill。

- [ ] **Step 4: 复制 Skill 到 docs/skills/ 目录**

```bash
mkdir -p docs/skills .claude/skills
cp .claude/skills/*.md docs/skills/
```

- [ ] **Step 5: 验证 Skill 文件质量**

检查每个 Skill 文件：
- 输入/输出定义是否明确
- 执行步骤是否可直接操作
- 检查清单是否覆盖关键质量点
- 验收标准是否可量化

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/ docs/skills/
git commit -m "docs: add practical skills extracted from GraphRAG knowledge"
```

---

## Task 4: 飞书数据分析

**前提：** 用户已将飞书数据表格导出为 CSV/Excel，放入 `data/` 目录。

**Files:**
- Read: `data/` 目录下所有数据文件
- Create: `scripts/analyze_feishu_data.py`
- Create: `docs/data/feishu-tables-overview.md`
- Create: `docs/data/entity-relation-analysis.md`
- Create: `docs/data/data-quality-report.md`

- [ ] **Step 1: 清点数据文件**

```bash
ls -la data/
```
记录文件数量、格式（CSV/Excel）、文件大小。

- [ ] **Step 2: 编写数据分析脚本**

创建 `scripts/analyze_feishu_data.py`，功能：
- 读取 `data/` 下所有 CSV/Excel 文件
- 对每个文件输出：字段名、数据类型、行数、缺失值比例、唯一值数量
- 识别跨表的同名字段（潜在关联键）
- 输出 JSON 格式的分析结果

```python
import pandas as pd
import json
import os
import sys
from pathlib import Path

def analyze_file(filepath):
    """分析单个数据文件"""
    try:
        suffix = Path(filepath).suffix.lower()
        if suffix == '.csv':
            df = pd.read_csv(filepath)
        elif suffix in ('.xlsx', '.xls'):
            df = pd.read_excel(filepath)
        else:
            return None
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return None

    result = {
        "filename": os.path.basename(filepath),
        "rows": len(df),
        "columns": list(df.columns),
        "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
        "null_ratio": {col: round(df[col].isnull().mean(), 3) for col in df.columns},
        "unique_counts": {col: int(df[col].nunique()) for col in df.columns},
        "sample_values": {col: df[col].dropna().head(3).tolist() for col in df.columns},
    }
    return result

def find_cross_table_links(analyses):
    """找跨表同名字段（潜在关联键）"""
    all_columns = {}
    for a in analyses:
        if a is None:
            continue
        for col in a["columns"]:
            all_columns.setdefault(col, []).append(a["filename"])
    return {col: files for col, files in all_columns.items() if len(files) > 1}

def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    analyses = []
    for f in sorted(os.listdir(data_dir)):
        fp = os.path.join(data_dir, f)
        if f.startswith('.') or not os.path.isfile(fp):
            continue
        result = analyze_file(fp)
        if result:
            analyses.append(result)
            print(f"Analyzed: {f} ({result['rows']} rows, {len(result['columns'])} cols)")

    links = find_cross_table_links(analyses)
    output = {"tables": analyses, "cross_table_links": links}
    out_path = os.path.join(data_dir, "analysis_result.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nAnalysis saved to {out_path}")
    print(f"Total tables: {len(analyses)}")
    print(f"Cross-table links found: {len(links)}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 运行分析脚本**

```bash
pip install pandas openpyxl 2>/dev/null
python scripts/analyze_feishu_data.py data/
```
Expected: 输出每张表的行列数，生成 `data/analysis_result.json`

- [ ] **Step 4: 编写飞书表格概览文档**

基于 `analysis_result.json`，编写 `docs/data/feishu-tables-overview.md`：
- 每张表的字段清单、行数、用途推测
- 表间关联字段汇总

- [ ] **Step 5: 编写实体关系分析文档**

编写 `docs/data/entity-relation-analysis.md`：
- 从字段名和数据内容识别潜在实体（如 Customer、Order、Product、Store、Style 等）
- 推断实体间关系（如 Customer-[PLACED]->Order、Order-[CONTAINS]->Product）
- 画出实体关系概要图（文字描述）
- 标注不确定的关系，待用户确认

- [ ] **Step 6: 编写数据质量报告**

编写 `docs/data/data-quality-report.md`：
- 缺失值严重的字段（>30% 缺失）
- 重复数据检测
- 数据类型不一致问题
- 建议的数据清洗优先级
- 数据质量评级标准：
  - A: <5% 缺失值，无明显重复，类型一致
  - B: 5-20% 缺失值，或少量重复
  - C: >20% 缺失值，或严重重复/类型问题

- [ ] **Step 7: Commit**

```bash
git add scripts/ docs/data/ data/analysis_result.json
git commit -m "docs: add feishu data analysis and quality report"
```

---

## Task 5: 知识-数据映射文档

**前提：** Task 3（Skill 提炼）和 Task 4（数据分析）均已完成。

**Files:**
- Read: `docs/knowledge/` 所有文档
- Read: `docs/data/` 所有文档
- Read: `.claude/skills/` 所有 Skill 文件
- Create: `docs/knowledge-data-mapping.md`

- [ ] **Step 1: 汇总知识学习成果和数据分析结果**

交叉比对：
- 知识文档中提到的 GraphRAG 概念 → 对应到哪些飞书数据
- 飞书数据中识别的实体/关系 → 对应到哪些 GraphRAG 处理步骤
- Skill 中定义的输入 → 是否有对应的数据源

- [ ] **Step 2: 编写映射文档**

`docs/knowledge-data-mapping.md` 包含：

**第一部分：数据表映射表**

| 飞书数据表 | 实体/关系类型 | GraphRAG 用途 | 处理 Skill | 优先级 | 数据质量评级 |
|-----------|-------------|-------------|-----------|-------|-----------|

每张飞书表一行，优先级按业务价值排序（P0/P1/P2）。

**第二部分：实体关系图谱概要**

描述核心实体和关系，标注：
- 确定的关系（单角色）
- 潜在多角色关系（如 Customer 可能是 buyer/receiver/referrer）
- 需要用户确认的歧义点

**第三部分：技术选型确认**

基于知识学习和实际数据特点，确认最终技术选型（可能调整设计规格中的初步方案）。

**第四部分：阶段1 PoC 建议**

- 推荐优先验证的场景（归因分析 或 智能问答）
- 推荐优先使用的 2-3 张表
- 预期的验收标准

- [ ] **Step 3: 审查映射文档质量**

检查：
- 所有 30+ 张表是否都在映射表中
- 实体关系是否有遗漏
- 优先级排序是否合理
- 阶段1建议是否具体可执行

- [ ] **Step 4: Commit**

```bash
git add docs/knowledge-data-mapping.md
git commit -m "docs: add knowledge-data mapping document for Phase 0"
```

---

## Task 6: 阶段0 回顾与阶段1 准备

**前提：** Task 5 已完成。

**Files:**
- Read: `docs/knowledge-data-mapping.md`
- Modify: `docs/superpowers/specs/2026-05-28-graph-rag-design.md`（更新阶段1细节）

- [ ] **Step 1: 执行阶段0回顾**

检查阶段0完成度：
- [ ] 知识文档覆盖了 GraphRAG 核心概念
- [ ] 至少 4 个实战 Skill 已提炼
- [ ] 所有飞书表已分析
- [ ] 知识-数据映射文档已完成
- [ ] 阶段1 PoC 场景已确定

- [ ] **Step 2: 记录遗留问题和风险**

将分析过程中发现的问题记录到映射文档的"待确认事项"部分。

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "docs: complete Phase 0 review and prepare for Phase 1"
```

- [ ] **Step 4: 通知用户阶段0完成**

向用户展示：
1. 知识-数据映射文档摘要
2. 阶段1 PoC 建议方案
3. 待用户确认的决策点

---

## 执行依赖关系

```
Task 1 (项目结构初始化)
  ├── Task 2 (视频知识提取) — 可重复执行，依赖用户提供链接
  │     └── Task 3 (知识综合与 Skill 提炼) — 等待足够知识积累
  └── Task 4 (飞书数据分析) — 依赖用户提供数据文件
        └──┐
           └──→ Task 5 (知识-数据映射) — 合并两条流
                  └── Task 6 (阶段0回顾)
```

Task 2 和 Task 4 可以并行执行（分别等用户提供视频链接和数据文件）。
