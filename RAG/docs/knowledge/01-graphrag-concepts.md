# GraphRAG 核心概念

## 1. 什么是 GraphRAG

### 1.1 定义
GraphRAG（Graph-based Retrieval-Augmented Generation）是一种结合知识图谱和大语言模型的增强检索生成技术。它通过构建结构化的知识图谱来补充和增强传统 RAG 的检索能力。

### 1.2 与传统 RAG 的区别

| 特性 | 传统 RAG | GraphRAG |
|------|---------|----------|
| **数据结构** | 非结构化文本片段 | 结构化实体-关系网络 |
| **检索方式** | 向量相似度匹配 | 图查询 + 向量检索混合 |
| **知识表示** | 文本片段 | 实体、关系、社区 |
| **推理能力** | 局部语义匹配 | 多跳关系推理 |
| **可解释性** | 较低 | 高（可追溯实体路径） |
| **维护成本** | 低 | 高（需维护图谱结构） |

**来源：** Bilibili 简介

### 1.3 核心优势
- **多跳推理能力**：能够通过实体关系链进行深层推理
- **全局上下文理解**：通过社区层次结构理解整体知识脉络
- **关系驱动检索**：基于实体关系而非仅基于语义相似度
- **可视化呈现**：知识图谱支持直观的可视化分析

**来源：** YouTube Video 1, 2, 3

---

## 2. 核心概念

### 2.1 实体（Entity）

**定义：** 知识图谱中的基本单元，代表现实世界中的对象或概念。

**类型示例：**
- **写真行业：** Customer（客户）、Order（订单）、Product（产品）、Photographer（摄影师）、Studio（工作室）
- **医疗行业：** Disease（疾病）、Medicine（药物）、Symptom（症状）、Department（科室）

**属性示例：**
```python
Customer 实体属性:
- customer_id: 唯一标识符
- name: 客户姓名
- phone: 联系电话
- preferences: 拍摄偏好
- membership_level: 会员等级
```

**来源：** Bilibili Series P11, P15, 写真行业模型

### 2.2 关系（Relationship）

**定义：** 连接实体的有向边，表示实体间的语义关联。

**写真行业关系示例：**
- `Customer -[PLACED]-> Order`：客户下单
- `Order -[CONTAINS]-> Product`：订单包含产品
- `Order -[ASSIGNED_TO]-> Photographer`：订单分配给摄影师
- `Customer -[PREFERRED]-> Photographer`：客户偏好摄影师
- `Order -[SHOT_AT]-> Studio`：订单在工作室拍摄

**医疗行业关系示例：**
- `Disease -[TREATED_BY]-> Medicine`：疾病用药治疗
- `Disease -[HAS_SYMPTOM]-> Symptom`：疾病症状
- `Medicine -[HAS_SIDE_EFFECT]-> Symptom`：药物副作用

**来源：** Bilibili Series P6, P12, 写真行业模型

### 2.3 社区（Community）

**定义：** 通过层次化聚类算法发现的实体集合，代表相关的知识主题或领域。

**社区层次结构：**
```
Level 0 (原子实体)
├── Customer: 张三
├── Product: 个人写真套餐
└── Photographer: 李摄影师

Level 1 (社区)
└── 会员客户群: [张三, 王五, 赵六]

Level 2 (社区)
└── 高价值客户群: [会员客户群, VIP客户群]
```

**用途：**
- 支持全局检索（Global Search）
- 提供领域级知识概览
- 优化大规模图谱查询

**来源：** YouTube Video 2, GraphRAG 论文

### 2.4 索引（Index）

**索引类型：**

1. **实体索引**
   - 对实体的关键属性建立索引
   - 示例：`CREATE INDEX FOR (n:Customer) ON (n.customer_id)`

2. **关系索引**
   - 加速关系查询
   - 示例：`CALL apoc.schema.relationship.create('PLACED', ['Customer'], ['Order'])`

3. **全文索引**
   - 支持文本搜索
   - 示例：`CREATE FULLTEXT INDEX customer_name FOR (n:Customer) ON EACH [n.name]`

4. **向量索引**
   - 支持语义相似度搜索
   - 与 Chroma/FAISS 集成

**来源：** Bilibili Series P5, P10

---

## 3. 查询策略

### 3.1 Local Search（局部检索）

**原理：**
- 基于用户问题中的关键词匹配相关实体
- 检索实体的直接邻居关系（1-2跳）
- 结合向量检索补充语义上下文

**适用场景：**
- 具体事实查询："张三最近一次订单是什么？"
- 实体属性查询："个人写真套餐包含哪些服务？"
- 单跳关系查询："李摄影师擅长什么风格？"

**查询流程：**
```python
def local_search(query, graph_db, vector_db):
    # 1. 提取查询中的实体
    entities = extract_entities(query)

    # 2. 检索实体的邻居关系
    cypher_query = """
    MATCH (n)-[r]-(neighbor)
    WHERE n.name IN $entities
    RETURN n, r, neighbor
    LIMIT 20
    """
    graph_results = graph_db.run(cypher_query, entities=entities)

    # 3. 向量检索补充
    vector_results = vector_db.similarity_search(query, k=10)

    # 4. 构建上下文
    context = build_context(graph_results, vector_results)

    # 5. 生成答案
    answer = llm.generate(query, context)
    return answer
```

**来源：** YouTube Video 2, Bilibili Series P7, P16

### 3.2 Global Search（全局检索）

**原理：**
- 基于社区层次结构进行检索
- 从高层社区概览到低层实体细节
- 适合需要全局理解的查询

**适用场景：**
- 总结性查询："会员客户的消费特点是什么？"
- 趋势分析："高价值客户群的拍摄偏好趋势？"
- 领域概览："写真行业的客户结构如何？"

**查询流程：**
```python
def global_search(query, graph_db, community_hierarchy):
    # 1. 识别查询相关的社区
    relevant_communities = identify_communities(query)

    # 2. 从高到低遍历社区层次
    context = ""
    for level in community_hierarchy:
        for community in level:
            if community in relevant_communities:
                context += get_community_summary(community)

    # 3. 生成答案
    answer = llm.generate(query, context)
    return answer
```

**来源：** YouTube Video 2, GraphRAG 0.4.0 更新

### 3.3 DRIFT Search（图推理搜索）

**原理：**
- 通过图遍历进行多跳推理
- 动态调整检索路径
- 结合概率推理优化路径选择

**适用场景：**
- 复杂推理查询："与李摄影师合作最多的客户有什么共同特征？"
- 隐性关系发现："哪些客户可能对新产品感兴趣？"
- 推荐系统："推荐与张三相似偏好的摄影师"

**特性：**
- 支持深度关系探索（3+跳）
- 结合 LLM 进行路径推理
- 动态调整检索策略

**来源：** YouTube Video 3 (GraphRAG 0.4.0 新功能)

---

## 4. 知识图谱构建流程概述

### 4.1 整体流程图

```
原始数据
    ↓
数据清洗与预处理
    ↓
实体提取（正则/NLP/LLM）
    ↓
Schema 设计（实体/关系定义）
    ↓
图谱创建（节点/边导入）
    ↓
索引构建（性能优化）
    ↓
社区检测（层次聚类）
    ↓
质量验证与优化
    ↓
知识图谱完成
```

**来源：** Bilibili Series P7, P9, P13

### 4.2 详细步骤

**Step 1: 数据准备**
- 数据格式转换（CSV/JSON/数据库）
- 数据清洗（去重、补全、标准化）
- 数据质量检查

**Step 2: Schema 设计**
- 实体类型定义
- 关系类型定义
- 属性设计
- 索引策略

**Step 3: 实体提取**
- 规则提取（正则匹配）
- NLP 提取（实体识别）
- LLM 辅助提取（复杂实体）

**Step 4: 关系构建**
- 关系类型定义
- 批量创建关系
- 数据一致性验证

**Step 5: 图谱导入**
- 批量数据导入
- 事务管理
- 性能优化

**Step 6: 后处理**
- 社区检测
- 索引创建
- 质量验证

**来源：** Bilibili Series P7-P16

---

## 5. GraphRAG 的增量更新机制

### 5.1 需求背景
传统 GraphRAG 需要全量重建索引，成本高、耗时长。增量更新允许只处理新增或修改的数据。

### 5.2 增量更新流程

**新增数据：**
```
新数据 → 实体提取 → 关系推断 → 差异更新 → 索引更新
```

**修改数据：**
```
修改数据 → 识别受影响节点 → 删除旧关系 → 创建新关系 → 索引重建
```

**删除数据：**
```
删除数据 → 级联删除关系 → 清理孤立节点 → 索引优化
```

### 5.3 技术实现
```python
def incremental_update(new_data, graph_db):
    # 1. 提取新实体
    new_entities = extract_entities(new_data)

    # 2. 检测现有图谱中的匹配实体
    existing_entities = find_existing_entities(new_entities, graph_db)

    # 3. 创建新实体
    for entity in new_entities:
        if entity not in existing_entities:
            create_entity(entity)

    # 4. 更新关系
    update_relationships(new_data, graph_db)

    # 5. 更新社区层次
    if should_recluster(graph_db):
        recluster_communities(graph_db)
```

### 5.4 优势
- **成本降低**：只处理变化的数据，减少 LLM 调用
- **效率提升**：无需全量重建，更新速度更快
- **实时性**：支持近实时数据更新

**来源：** YouTube Video 3 (GraphRAG 0.4.0 新功能)

---

## 6. 知识图谱可视化（Neo4j）

### 6.1 Neo4j Bloom

**特性：**
- 无代码可视化探索
- 自然语言查询支持
- 交互式图表编辑
- 多维度数据展示

**适用场景：**
- 数据探索与发现
- 模式识别
- 业务洞察
- 演示与汇报

**来源：** YouTube Video 1, 6

### 6.2 3D 可视化

**工具：**
- Neo4j Bloom 3D 视图
- 自定义 WebGL 可视化
- D3.js / ECharts 集成

**优势：**
- 直观展示复杂关系
- 支持大规模图谱
- 交互式探索

**来源：** YouTube Video 6

### 6.3 可视化配置示例

```python
# 使用 Neo4j Python Driver 生成可视化数据
def generate_visualization_data(graph_db, entity_type):
    query = f"""
    MATCH (n:{entity_type})-[r]-(m)
    RETURN n.name AS source, type(r) AS relationship, m.name AS target
    LIMIT 100
    """
    return graph_db.run(query).data()
```

**来源：** YouTube Video 1

---

## 7. 性能与成本指标

### 7.1 索引构建对比（LightRAG vs GraphRAG）

| 指标 | LightRAG | GraphRAG |
|------|----------|----------|
| **LLM 调用次数** | 较少 | 较多 |
| **Token 消耗** | 低 | 高 |
| **构建时间** | 快 | 慢 |
| **索引质量** | 中等 | 高 |
| **社区检测** | 无 | 有 |
| **成本** | 低 | 高 |

**来源：** YouTube Video 2

### 7.2 检索质量对比

| 检索类型 | LightRAG | GraphRAG |
|----------|----------|----------|
| **Local Search** | 中等 | 优秀 |
| **Global Search** | 无 | 优秀 |
| **推理能力** | 单跳 | 多跳 |
| **可解释性** | 中等 | 优秀 |

**来源：** YouTube Video 2

### 7.3 成本示例

**20,000 字符文本处理：**
- GraphRAG：约 1.4 元人民币（使用 GPT-3.5）
- LightRAG：更低
- 本地模型（Ollama）：免费（硬件成本）

**来源：** YouTube Video 6

---

## 8. 知识点来源标注

| 知识点 | 来源视频 |
|--------|---------|
| GraphRAG 定义与核心概念 | Bilibili 简介, YouTube V1-V6 |
| 实体/关系/社区概念 | Bilibili Series P5-P6, P15 |
| Local Search 查询策略 | YouTube V2, Bilibili P7, P16 |
| Global Search 查询策略 | YouTube V2, GraphRAG 0.4.0 |
| DRIFT Search | YouTube V3 (GraphRAG 0.4.0) |
| 知识图谱构建流程 | Bilibili Series P7-P16 |
| 增量更新机制 | YouTube V3 (GraphRAG 0.4.0) |
| Neo4j 可视化 | YouTube V1, V6 |
| LightRAG vs GraphRAG 对比 | YouTube V2 |
| 本地模型集成 | YouTube V4 |
| 成本优化 | YouTube V6 |
| 写真行业实体模型 | 写真行业 RAG 项目 |

---

## 9. 总结

GraphRAG 通过结合知识图谱的结构化表示和大语言模型的推理能力，在以下方面超越传统 RAG：

1. **多跳推理**：能够理解复杂的关系链
2. **全局理解**：通过社区层次把握整体知识脉络
3. **可解释性**：检索路径可追溯
4. **可视化**：支持图谱可视化分析

但也需要注意：
- **成本更高**：需要更多的 LLM 调用和计算资源
- **复杂度高**：需要设计和维护图谱 Schema
- **实时性**：增量更新仍在发展中

对于写真行业这样的结构化业务数据，GraphRAG 特别适合需要多跳推理的场景，如：
- 客户关系分析
- 产品推荐
- 业务洞察
- 决策支持