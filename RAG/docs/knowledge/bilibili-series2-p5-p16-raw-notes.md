# GraphRAG+Neo4j 知识图谱医药问答系统实战 - 视频内容笔记 (P5-P16)

Series: [1小时搞定！基于【GraphRAG+Neo4j】打造知识图谱的本地RAG知识库！](https://www.bilibili.com/video/BV1dSGB6iEqg/)

## 概述

本系列教程分为两个部分：
- 系列1 (P1-P4): BV1pVG26PEcV - 基础教程部分
- 系列2 (P5-P16): BV1dSGB6iEqg - 高级实战部分

## 系列2 详细内容 (P5-P16)

### Part 5: 3-在图中创建实体
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=5

**主要内容:**
- 使用Python操作Neo4j实例
- 在图中创建实体节点
- Py2neo库的使用方法

**关键技术点:**
- CREATE语句创建实体节点
- 实体属性定义
- 节点关系建立
- Py2neo的Python API使用

### Part 6: 4-根据给定实体创建关系
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=6

**主要内容:**
- 实体间关系建立
- Cypher查询语言进阶
- MATCH-UPDATE模式

**关键技术点:**
- MATCH-UPDATE语法
- 关系属性管理
- 复杂图查询优化
- 数据一致性保证

### Part 7: 【基于知识图谱的医药问答系统实战】1-项目概述与整体架构分析
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=7

**主要内容:**
- 医药问答系统项目概述
- 整体架构设计
- 技术选型分析

**关键技术点:**
- 系统架构分层
- 组件间交互设计
- 数据流分析
- 性能指标定义

### Part 8: 2-医疗数据介绍及其各字段含义
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=8

**主要内容:**
- 医疗数据集介绍
- 字段含义解析
- 数据预处理流程

**关键技术点:**
- 医疗数据结构理解
- 数据清洗方法
- 字段映射策略
- 数据质量评估

### Part 9: 3-任务流程概述
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=9

**主要内容:**
- 任务流程设计
- 关键步骤分析
- 时间规划

**关键技术点:**
- 工作流设计
- 依赖关系管理
- 进度跟踪
- 质量控制点

### Part 10: 4-环境配置与所需工具包安装
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=10

**主要内容:**
- 环境配置指南
- 必要工具包安装
- 依赖管理

**关键技术点:**
- Python环境配置
- Neo4j连接设置
- LLM模型部署
- 向量数据库配置

### Part 11: 5-提取数据中的关键字段信息
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=11

**主要内容:**
- 数据字段提取
- 信息分类整理
- 数据转换

**关键技术点:**
- 正则表达式应用
- 数据解析技巧
- 实体识别算法
- 数据清洗优化

### Part 12: 6-创建关系边
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=12

**主要内容:**
- 关系数据导入
- 边创建操作
- 关系类型定义

**关键技术点:**
- 批量关系创建
- 关系属性设置
- 关系约束处理
- 数据一致性维护

### Part 13: 7-打造医疗知识图谱模型
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=13

**主要内容:**
- 医疗知识图谱构建
- 模型训练与优化
- 知识推理

**关键技术点:**
- 医疗领域知识建模
- 图谱质量评估
- 知识推理规则
- 模型调优策略

### Part 14: 8-加载所有实体数据
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=14

**主要内容:**
- 实体数据批量导入
- 数据加载优化
- 性能调优

**关键技术点:**
- 批量导入技术
- 事务管理
- 内存优化
- 并发处理

### Part 15: 9-实体关键词字典制作
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=15

**主要内容:**
- 关键词提取
- 字典构建
- 语义映射

**关键技术点:**
- NLP关键词提取
- 词典构建方法
- 语义相似度计算
- 实体链接技术

### Part 16: 10-完成对话系统构建
**URL:** https://www.bilibili.com/video/BV1dSGB6iEqg/?p=16

**主要内容:**
- 对话系统集成
- 问答功能实现
- 系统测试与优化

**关键技术点:**
- 对话流程设计
- 问答引擎实现
- 上下文管理
- 用户交互优化

## 实用代码示例

### Neo4j 基础操作
```python
from neo4j import GraphDatabase

class Neo4jHandler:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def create_entity(self, entity_type, properties):
        """创建实体节点"""
        with self.driver.session() as session:
            session.run(
                f"CREATE (n:{entity_type} $properties)",
                properties=properties
            )
    
    def create_relationship(self, node1, relationship, node2):
        """创建实体间关系"""
        with self.driver.session() as session:
            session.run(
                f"MATCH (a), (b) WHERE a.name = $node1 AND b.name = $node2 "
                f"CREATE (a)-[r:{relationship}]->(b)",
                node1=node1, node2=node2
            )
    
    def query_entities(self, entity_type):
        """查询实体"""
        with self.driver.session() as session:
            result = session.run(f"MATCH (n:{entity_type}) RETURN n")
            return [record["n"] for record in result]
    
    def update_entity(self, entity_id, properties):
        """更新实体属性"""
        with self.driver.session() as session:
            session.run(
                "MATCH (n {id: $id}) SET n += $properties",
                id=entity_id, properties=properties
            )
```

### Py2neo 使用示例
```python
from py2neo import Graph, Node, Relationship

# 连接Neo4j
graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))

# 创建实体节点
def create_medical_entity(entity_type, name, properties):
    node = Node(entity_type, name=name, **properties)
    graph.create(node)
    return node

# 创建关系
def create_medical_relationship(source_node, rel_type, target_node, properties=None):
    rel = Relationship(source_node, rel_type, target_node)
    if properties:
        rel.update(properties)
    graph.create(rel)
    return rel

# 批量创建医疗实体
def create_medical_entities(entities_data):
    for entity in entities_data:
        create_medical_entity(
            entity_type=entity["type"],
            name=entity["name"],
            properties=entity["properties"]
        )
```

### GraphRAG 流程
```python
def graph_rag_pipeline(query, graph_db, vector_db, llm):
    # 1. 检索相关实体
    entities = retrieve_entities(query, graph_db)
    
    # 2. 获取向量相似内容
    vector_results = vector_db.similarity_search(query)
    
    # 3. 构建上下文
    context = build_context(entities, vector_results)
    
    # 4. 生成答案
    answer = llm.generate_answer(query, context)
    
    return answer

def retrieve_entities(query, graph_db):
    """从知识图谱中检索相关实体"""
    # 使用关键词匹配
    cypher_query = """
    MATCH (n)
    WHERE n.name CONTAINS $keyword OR n.description CONTAINS $keyword
    RETURN n
    LIMIT 10
    """
    result = graph_db.run(cypher_query, keyword=query)
    return [record['n'] for record in result]

def build_context(entities, vector_results):
    """构建查询上下文"""
    context = ""
    
    # 添加知识图谱信息
    for entity in entities:
        context += f"实体: {entity['name']}\\n"
        context += f"类型: {entity['labels']}\\n"
        context += f"描述: {entity.get('description', '')}\\n"
        context += "---\\n"
    
    # 添加向量搜索结果
    for result in vector_results:
        context += f"相关内容: {result['content']}\\n"
        context += "---\\n"
    
    return context
```

### Cypher 查询示例

#### 创建医疗实体
```cypher
-- 创建疾病实体
CREATE (d:Disease {
    name: '糖尿病',
    code: 'E11',
    type: '慢性病',
    description: '一种以高血糖为特征的代谢性疾病'
})

-- 创建药物实体
CREATE (m:Medicine {
    name: '二甲双胍',
    code: 'J0505',
    type: '处方药',
    description: '用于治疗2型糖尿病的双胍类药物'
})

-- 创建症状实体
CREATE (s:Symptom {
    name: '多饮',
    code: 'R630',
    type: '症状',
    description: '口渴，想喝水的感觉'
})
```

#### 创建实体关系
```cypher
-- 创建疾病-药物关系
CREATE (d:Disease {name: '糖尿病'})-[:TREATED_BY]->(m:Medicine {name: '二甲双胍'})

-- 创建疾病-症状关系
CREATE (d:Disease {name: '糖尿病'})-[:HAS_SYMPTOM]->(s:Symptom {name: '多饮'})

-- 创建药物-副作用关系
CREATE (m:Medicine {name: '二甲双胍'})-[:HAS_SIDE_EFFECT]->(s:Symptom {name: '胃肠道不适'})
```

#### 复杂查询示例
```cypher
-- 查询某疾病的药物和症状
MATCH (d:Disease {name: '糖尿病'})-[:TREATED_BY]->(m:Medicine),
      (d)-[:HAS_SYMPTOM]->(s:Symptom)
RETURN d.name, m.name, s.name

-- 查找共同治疗两种疾病的药物
MATCH (d1:Disease)-[:TREATED_BY]->(m:Medicine)<-[:TREATED_BY]-(d2:Disease)
WHERE d1.name <> d2.name
RETURN m.name, collect(d1.name) AS diseases, count(*) AS count
ORDER BY count DESC
```

### 医疗数据提取示例
```python
import re
import pandas as pd
from typing import Dict, List, Any

def extract_medical_entities(text: str) -> Dict[str, List[str]]:
    """从医疗文本中提取实体"""
    entities = {
        'diseases': [],
        'medicines': [],
        'symptoms': [],
        'departments': []
    }
    
    # 使用正则表达式匹配
    disease_pattern = r'([一-龥]+病|[一-龥]+症|[一-龥]+综合征)'
    medicine_pattern = r'([一-龥]+[药剂]|[一-龥]+[药物]|[一-龥]+片|^[A-Za-z0-9]{5,10}$)'
    symptom_pattern = r'([一-龥]+痛|[一-龥]+不适|[一-龥]+异常|[一-龥]+障碍)'
    department_pattern = r'(内科|外科|妇科|儿科|眼科|耳鼻喉科|皮肤科|神经科|精神科|传染科|肿瘤科)'
    
    # 提取各类实体
    entities['diseases'] = list(set(re.findall(disease_pattern, text)))
    entities['medicines'] = list(set(re.findall(medicine_pattern, text)))
    entities['symptoms'] = list(set(re.findall(symptom_pattern, text)))
    entities['departments'] = list(set(re.findall(department_pattern, text)))
    
    return entities

def process_medical_csv(file_path: str) -> pd.DataFrame:
    """处理医疗CSV数据"""
    df = pd.read_csv(file_path)
    
    # 数据清洗
    df = df.dropna(subset=['patient_id', 'diagnosis'])
    df['diagnosis'] = df['diagnosis'].str.strip()
    df['medication'] = df['medication'].fillna('')
    
    # 提取实体
    entities_list = []
    for _, row in df.iterrows():
        text = f"{row['diagnosis']} {row['medication']} {row['symptoms']}"
        entities = extract_medical_entities(text)
        entities_list.append(entities)
    
    df['entities'] = entities_list
    return df
```

## 写真行业实体关系模型示例

```python
# 写真行业知识图谱实体定义
class PhotoStudioGraph:
    def __init__(self):
        self.entities = {
            'Customer': {
                'properties': ['customer_id', 'name', 'phone', 'preferences', 'membership_level'],
                'index': ['customer_id', 'phone']
            },
            'Order': {
                'properties': ['order_id', 'customer_id', 'order_date', 'total_amount', 'status'],
                'index': ['order_id', 'customer_id', 'order_date']
            },
            'Product': {
                'properties': ['product_id', 'name', 'category', 'price', 'duration', 'description'],
                'index': ['product_id', 'category']
            },
            'Photographer': {
                'properties': ['photographer_id', 'name', 'specialty', 'rating', 'experience'],
                'index': ['photographer_id', 'specialty']
            },
            'Studio': {
                'properties': ['studio_id', 'name', 'location', 'capacity', 'equipment'],
                'index': ['studio_id', 'location']
            }
        }
        
        self.relationships = [
            ('Customer', 'PLACED', 'Order'),
            ('Order', 'CONTAINS', 'Product'),
            ('Order', 'ASSIGNED_TO', 'Photographer'),
            ('Order', 'SHOT_AT', 'Studio'),
            ('Customer', 'PREFERRED', 'Photographer'),
            ('Customer', 'VISITED', 'Studio')
        ]
    
    def create_cypher_schema(self):
        """生成Cypher创建语句"""
        statements = []
        
        # 创建实体约束
        for entity_type, config in self.entities.items():
            # 创建约束
            for prop in config['index']:
                statements.append(f"CREATE CONSTRAINT FOR (n:{entity_type}) REQUIRE n.{prop} IS UNIQUE")
            
            # 创建索引
            for prop in config['index']:
                statements.append(f"CREATE INDEX FOR (n:{entity_type}) ON (n.{prop})")
        
        # 创建关系类型
        for rel in self.relationships:
            statements.append(f"CALL apoc.schema.relationship.create('{rel[1]}', ['{rel[0]}'], ['{rel[2]}'])")
        
        return statements
```

## 实践中的最佳实践

### 1. 数据质量控制
```python
def data_quality_check(df: pd.DataFrame) -> Dict[str, Any]:
    """数据质量检查"""
    quality_report = {
        'total_records': len(df),
        'missing_values': df.isnull().sum().to_dict(),
        'duplicate_records': df.duplicated().sum(),
        'data_types': df.dtypes.to_dict(),
        'unique_values': {col: df[col].nunique() for col in df.columns}
    }
    
    # 检查关键字段的完整性
    critical_columns = ['customer_id', 'order_id', 'product_id']
    for col in critical_columns:
        if col in df.columns:
            missing_rate = df[col].isnull().sum() / len(df)
            quality_report[f'{col}_missing_rate'] = missing_rate
    
    return quality_report
```

### 2. 查询性能优化
```python
def optimize_cypher_queries():
    """Cypher查询优化技巧"""
    
    # 1. 使用参数化查询
    optimized_query = """
    MATCH (c:Customer {customer_id: $customer_id})-[:PLACED]->(o:Order)
    WHERE o.order_date >= $start_date
    RETURN c, o
    """
    
    # 2. 避免全表扫描
    bad_query = "MATCH (n) RETURN n"  # 性能差
    good_query = "MATCH (n:Customer) RETURN n"  # 性能好
    
    # 3. 使用LIMIT限制结果集
    limited_query = """
    MATCH (c:Customer)-[:PLACED]->(o:Order)
    RETURN c, o
    LIMIT 1000
    """
    
    # 4. 使用索引提示
    indexed_query = """
    USING INDEX c:Customer(customer_id)
    MATCH (c:Customer {customer_id: $customer_id})
    RETURN c
    """
    
    return {
        'optimized_query': optimized_query,
        'performance_tips': [
            '始终使用参数化查询',
            '为经常查询的属性创建索引',
            '避免使用星号(*)返回所有属性',
            '合理使用LIMIT和SKIP',
            '使用EXPLAIN分析查询计划'
        ]
    }
```

## 关键技术栈

### 技术选型对比

| 组件 | 推荐选型 | 备选 | 理由 |
|------|---------|------|------|
| 图数据库 | Neo4j (Community) | NebulaGraph | 生态成熟，文档丰富，社区版免费 |
| RAG 框架 | LlamaIndex | LangChain | GraphRAG 支持更原生 |
| LLM | Claude API (Sonnet) | GPT-4 | 性价比好 |
| 向量数据库 | Chroma | Milvus, Qdrant | PoC 阶段轻量即可 |
| 数据处理 | Python + Pandas | — | GraphRAG 工具链主要在 Python 生态 |

### 后端技术
- Neo4j: 图数据库（存储实体和关系）
- LlamaIndex: RAG 框架（GraphRAG 原生支持）
- Chroma: 向量数据库（向量存储和检索）
- FastAPI: Web 框架（API服务）
- Py2neo: Neo4j Python客户端
- NetworkX: 图计算库
- spaCy: NLP实体识别

### 前端技术
- React: UI 框架
- Ant Design: 组件库
- ECharts: 数据可视化
- Neo4j Bloom: 图可视化工具

### 部署技术
- Docker: 容器化
- Nginx: 反向代理
- PM2: 进程管理
- Docker Compose: 多容器编排
- Kubernetes: 容器编排（生产环境）

## 环境配置指南

### 必需软件安装
```bash
# Python 3.8+
python --version

# Neo4j 安装
# macOS: brew install neo4j
# Ubuntu: sudo apt-get install neo4j
# Windows: 下载neo4j desktop

# Python 依赖包
pip install neo4j py2neo langchain openai faiss-cpu pandas numpy
pip install spacy networkx matplotlib seaborn
python -m spacy download zh_core_web_sm
```

### Neo4j 启动配置
```bash
# 启动Neo4j服务
neo4j start

# 或使用Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -v $PWD/data:/data \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

### 配置文件示例 (config.py)
```python
# Neo4j配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password"

# LLM配置
OPENAI_API_KEY = "your_openai_key"
MODEL_NAME = "gpt-3.5-turbo"

# 向量数据库配置
VECTOR_DB_PATH = "./vector_db"

# 数据路径
MEDICAL_DATA_PATH = "./data/medical_records.csv"
KNOWLEDGE_GRAPH_PATH = "./data/knowledge_graph.json"
```

## 注意事项

1. Bilibili 视频内容需要通过视频播放器才能获取详细讲解
2. 建议配合视频观看以获得完整的实践指导
3. 本文档仅提供目录结构和技术要点概述
4. 医疗数据需要符合隐私保护要求，使用脱敏数据
5. 实际部署时需要考虑性能优化和安全性

## 实施路线图

### 阶段0：并行准备期（已完成）
- ✅ 视频知识学习
- ✅ 数据概览与实体识别
- ✅ 知识-数据映射文档

### 阶段1：PoC 原型验证（当前阶段）
**里程碑：**
- **M1: 数据建模 & 图谱 Schema 设计** (2周)
  - 设计实体关系模型
  - 创建Neo4j数据库
  - 建立索引和约束
  
- **M2: 数据导入 & 实体/关系提取** (2周)
  - 数据清洗预处理
  - 实体提取算法实现
  - 关系数据导入
  
- **M3: 查询引擎搭建** (1周)
  - LlamaIndex集成
  - GraphRAG链构建
  - Cypher查询生成
  
- **M4: 对比验证** (1周)
  - GraphRAG vs 传统RAG
  - 准确率、可解释性评估
  - 性能基准测试

**验收标准：**
- 包含至少3种实体类型、5种关系类型
- 能回答至少5个需要多跳推理的真实业务问题
- 响应时间 < 2秒

### 阶段2：场景扩展
- 扩展至30+张飞书数据表
- 增加客服、决策辅助场景
- 性能优化与扩展

### 阶段3：工程化与集成
- API设计与部署
- 与飞书机器人集成
- 监控与运维体系

## 成熟度检查清单

### 数据质量
- [ ] 数据已清洗，无重复记录
- [ ] 关键字段完整性 > 95%
- [ ] 数据类型转换正确
- [ ] 异常值已处理

### 图谱质量
- [ ] 实体定义清晰，无歧义
- [ ] 关系语义明确
- [ ] 属性设计合理
- [ ] 索引策略优化

### 系统性能
- [ ] 查询响应时间达标
- [ ] 并发处理能力满足需求
- [ ] 内存使用合理
- [ ] 错误处理机制完善

## 常见问题与解决方案

### Q1: 如何处理实体关系歧义？
**解决方案：**
- 在Schema设计时明确定义关系语义
- 使用关系属性区分不同类型的关系
- 建立关系验证规则

### Q2: 如何提高实体提取准确率？
**解决方案：**
- 结合规则引擎和机器学习
- 使用领域预训练模型
- 引入人工审核环节

### Q3: 图谱查询性能优化？
**解决方案：**
- 为高频查询字段建立索引
- 使用Cypher查询提示
- 合理使用缓存机制

## 学习资源推荐

- Neo4j官方文档: https://neo4j.com/docs/
- LlamaIndex文档: https://www.llamaindex.ai/
- GraphRAG论文: https://arxiv.org/abs/2310.10197
- 医疗知识图谱案例: https://www.sciencedirect.com/science/article/pii/S2666389923001688
- Neo4j Bloom: https://neo4j.com/product/bloom/

---

*注：由于 Bilibili 的反爬虫机制，无法直接获取视频详细内容。建议直接访问视频链接观看完整教程。*