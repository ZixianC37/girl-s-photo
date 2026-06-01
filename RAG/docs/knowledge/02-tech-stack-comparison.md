# 技术选型对比

## 1. 图数据库对比

### 1.1 Neo4j vs NebulaGraph

| 特性 | Neo4j | NebulaGraph |
|------|-------|-------------|
| **开发语言** | Java | C++ |
| **开源协议** | GPL v3 (Community) / 商业版 | Apache 2.0 |
| **部署方式** | 单机/集群 | 集群为主 |
| **查询语言** | Cypher | nGQL (类 SQL) |
| **生态成熟度** | 高（文档丰富、社区活跃） | 中等（国内发展快） |
| **学习曲线** | 低（Cypher 语法直观） | 中（nGQL 需学习） |
| **性能** | 中等 | 高（C++ 实现优势） |
| **扩展性** | 中等 | 高（分布式原生） |
| **可视化工具** | Neo4j Bloom (官方) | NebulaGraph Studio |
| **Python 客户端** | neo4j-driver, py2neo | nebula3-python |
| **中文支持** | 中等 | 优秀（国产数据库） |
| **适用场景** | 中小规模、快速原型 | 大规模、高性能场景 |
| **成本** | Community 免费 | 开源免费 |
| **文档质量** | 优秀 | 良好（中文文档多） |
| **社区活跃度** | 高 | 中等（国内为主） |

### 1.2 推荐选择

**选择 Neo4j 的理由：**
- ✅ 生态成熟，文档丰富，学习成本低
- ✅ Cypher 语法直观，开发效率高
- ✅ Neo4j Bloom 提供优秀的可视化
- ✅ GraphRAG 社区主要以 Neo4j 为主
- ✅ 适合 PoC 原型和中小规模部署

**选择 NebulaGraph 的理由：**
- ✅ C++ 实现，性能更优
- ✅ 分布式架构，扩展性强
- ✅ 适合大规模图谱（百万级节点以上）
- ✅ 开源协议友好（Apache 2.0）
- ✅ 国内厂商，中文支持好

### 1.3 最终推荐

**本项目推荐：Neo4j Community**

**理由：**
1. PoC 阶段不需要分布式能力
2. Neo4j Bloom 可视化优势明显
3. Cypher 语法学习成本低
4. GraphRAG 生态以 Neo4j 为主
5. 社区活跃，问题解决快

**未来扩展：** 如果数据量增长到百万级以上，可迁移到 NebulaGraph。

---

## 2. RAG 框架对比

### 2.1 LlamaIndex vs LangChain vs 原生实现

| 特性 | LlamaIndex | LangChain | 原生实现 |
|------|------------|-----------|----------|
| **GraphRAG 支持** | 原生支持（LlamaIndex Graph） | 通过插件支持 | 需自行实现 |
| **学习曲线** | 中等 | 陡峭 | 陡峭 |
| **开发效率** | 高 | 中等 | 低 |
| **灵活性** | 中等 | 高 | 最高 |
| **文档质量** | 优秀 | 良好 | - |
| **社区活跃度** | 高 | 高 | - |
| **向量数据库集成** | 丰富（30+） | 丰富（20+） | 需自行集成 |
| **LLM 集成** | 丰富 | 丰富 | 需自行集成 |
| **性能** | 优化好 | 中等 | 可完全优化 |
| **代码量** | 少 | 中等 | 多 |
| **维护成本** | 低 | 中等 | 高 |
| **调试难度** | 低 | 中等 | 高 |
| **GraphRAG 特性** | 丰富 | 基础 | 需自行实现 |

### 2.2 LlamaIndex GraphRAG 特性

**核心功能：**
- ✅ Neo4j 集成（原生支持）
- ✅ 实体提取（基于 LLM）
- ✅ 关系构建（自动推断）
- ✅ 社区检测（层次聚类）
- ✅ Local/Global Search
- ✅ 混合检索（图 + 向量）
- ✅ 可视化支持

**代码示例：**
```python
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.graph_stores import Neo4jGraphStore

# 创建 Neo4j 图存储
graph_store = Neo4jGraphStore(
    url="bolt://localhost:7687",
    username="neo4j",
    password="password"
)

# 创建存储上下文
storage_context = StorageContext.from_defaults(
    graph_store=graph_store
)

# 构建索引
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context,
    show_progress=True
)
```

### 2.3 LangChain GraphRAG 特性

**核心功能：**
- ✅ Neo4j 集成（通过 LangChain-Community）
- ✅ 实体提取（基于 LLM）
- ✅ 关系构建（基础）
- ✅ Cypher 查询生成
- ✅ 混合检索
- ⚠️ 社区检测需自行实现
- ⚠️ Global Search 需自行实现

**代码示例：**
```python
from langchain_community.graphs import Neo4jGraph

# 连接 Neo4j
graph = Neo4jGraph(
    url="bolt://localhost:7687",
    username="neo4j",
    password="password"
)

# 执行 Cypher 查询
result = graph.query("""
    MATCH (n)-[r]->(m)
    RETURN n, r, m
    LIMIT 10
""")
```

### 2.4 原生实现

**优势：**
- ✅ 完全掌控实现细节
- ✅ 性能可极致优化
- ✅ 无依赖，轻量级

**劣势：**
- ❌ 开发成本高
- ❌ 需实现所有功能
- ❌ 维护成本高
- ❌ 调试复杂

### 2.5 推荐选择

**本项目推荐：LlamaIndex**

**理由：**
1. GraphRAG 原生支持，功能完整
2. Neo4j 集成成熟稳定
3. Local/Global Search 开箱即用
4. 社区活跃，文档丰富
5. 适合快速原型开发

**备选：LangChain**
- 如果项目已有 LangChain 基础设施
- 需要更灵活的定制能力

---

## 3. GraphRAG vs LightRAG 对比

### 3.1 索引构建对比

| 特性 | GraphRAG | LightRAG |
|------|----------|----------|
| **LLM 调用次数** | 高 | 低 |
| **Token 消耗** | 高 | 低 |
| **构建时间** | 长 | 短 |
| **索引质量** | 高 | 中等 |
| **社区检测** | 有（层次化） | 无 |
| **关系推断** | 强 | 基础 |
| **实体提取** | LLM 增强 | 规则 + LLM |
| **增量更新** | 有（0.4.0+） | 有 |
| **成本** | 高 | 低 |
| **适用场景** | 高质量检索 | 快速原型 |

### 3.2 检索质量对比

| 检索类型 | GraphRAG | LightRAG |
|----------|----------|----------|
| **Local Search** | 优秀（多跳） | 良好（单跳） |
| **Global Search** | 优秀 | 无 |
| **DRIFT Search** | 有（0.4.0+） | 无 |
| **推理能力** | 强 | 中等 |
| **可解释性** | 高 | 中等 |
| **检索速度** | 中等 | 快 |
| **准确性** | 高 | 中等 |

### 3.3 成本对比（20,000 字符）

| 成本项目 | GraphRAG | LightRAG | 说明 |
|----------|----------|----------|------|
| **LLM 调用** | 约 1.4 元 | 约 0.5 元 | GPT-3.5 |
| **构建时间** | 约 5-10 分钟 | 约 1-2 分钟 | 取决于模型 |
| **索引大小** | 较大 | 较小 | GraphRAG 包含社区信息 |
| **检索成本** | 中等 | 低 | GraphRAG 需要多跳查询 |

### 3.4 Token 消耗对比

| 阶段 | GraphRAG | LightRAG |
|------|----------|----------|
| **索引构建** | 高 | 低 |
| **Local Search** | 中等 | 低 |
| **Global Search** | 高 | 无 |
| **增量更新** | 低 | 低 |

### 3.5 推荐选择

**PoC 阶段：LightRAG**
- 成本低，快速验证
- 适合小规模数据
- 适合原型演示

**生产阶段：GraphRAG**
- 检索质量高
- 支持全局检索
- 支持复杂推理
- 适合核心业务

**本项目推荐：**
- **初期：** LightRAG（快速验证）
- **后期：** GraphRAG（高质量检索）

---

## 4. LLM 选型对比

### 4.1 GPT vs Claude vs 国产模型 vs 本地模型

| 特性 | GPT-4 | Claude Sonnet | 通义千问 | 文心一言 | 智谱 GLM | 讯飞星火 | 本地模型 (Ollama) |
|------|-------|---------------|----------|----------|----------|----------|-------------------|
| **推理能力** | 最强 | 强 | 中等 | 中等 | 中等 | 中等 | 中等 |
| **中文能力** | 强 | 强 | 优秀 | 优秀 | 优秀 | 优秀 | 取决于模型 |
| **上下文长度** | 128K | 200K | 8K-32K | 8K-16K | 8K-32K | 8K-32K | 取决于模型 |
| **成本** | 高 | 中等 | 低 | 低 | 低 | 低 | 免费（硬件成本） |
| **速度** | 快 | 快 | 中等 | 中等 | 中等 | 中等 | 慢（硬件依赖） |
| **稳定性** | 高 | 高 | 中等 | 中等 | 中等 | 中等 | 高（自控） |
| **API 质量** | 优秀 | 优秀 | 良好 | 良好 | 良好 | 良好 | - |
| **速率限制** | 中等 | 高 | 高 | 高 | 高 | 高 | 无 |
| **隐私** | 中等 | 高 | 中等 | 中等 | 中等 | 中等 | 最高 |
| **部署难度** | 低 | 低 | 低 | 低 | 低 | 低 | 高 |

### 4.2 详细对比

#### GPT-4 / GPT-3.5
**优势：**
- ✅ 推理能力最强
- ✅ 上下文理解好
- ✅ 工具使用能力强
- ✅ 多语言支持好

**劣势：**
- ❌ 成本高
- ❌ 数据隐私顾虑
- ❌ 速率限制

**适用场景：**
- 复杂实体提取
- 关系推断
- 知识推理
- 高质量场景

#### Claude Sonnet
**优势：**
- ✅ 推理能力强（接近 GPT-4）
- ✅ 中文能力优秀
- ✅ 上下文长度长（200K）
- ✅ 成本相对较低
- ✅ 速率限制宽松

**劣势：**
- ❌ API 相对新
- ❌ 生态不如 GPT 成熟

**适用场景：**
- 平衡质量和成本
- 长文本处理
- 知识图谱构建

#### 通义千问（阿里云）
**优势：**
- ✅ 中文能力强
- ✅ 成本低
- ✅ 速率限制宽松
- ✅ 国内合规

**劣势：**
- ❌ 推理能力中等
- ❌ 上下文长度较短

**适用场景：**
- 中文实体提取
- 成本敏感场景
- 国内合规要求

#### 文心一言（百度）
**优势：**
- ✅ 中文能力强
- ✅ 成本低
- ✅ 国内合规

**劣势：**
- ❌ 推理能力中等
- ❌ API 稳定性一般

**适用场景：**
- 中文文本处理
- 成本敏感场景

#### 智谱 GLM
**优势：**
- ✅ 中文能力强
- ✅ 成本低
- ✅ GraphRAG 支持好
- ✅ 国内合规

**劣势：**
- ❌ 推理能力中等

**适用场景：**
- GraphRAG 项目
- 中文场景
- 成本敏感

#### 讯飞星火
**优势：**
- ✅ 中文能力强
- ✅ 成本低
- ✅ 国内合规

**劣势：**
- ❌ 推理能力中等

**适用场景：**
- 中文文本处理
- 语音集成场景

#### 本地模型（Ollama）
**支持模型：**
- Qwen2（通义千问开源版）
- Llama3.1
- ChatGLM3
- Baichuan2

**优势：**
- ✅ 免费（仅需硬件成本）
- ✅ 数据隐私最高
- ✅ 无速率限制
- ✅ 可完全控制

**劣势：**
- ❌ 需要硬件（GPU）
- ❌ 推理速度慢
- ❌ 能力不如云端模型
- ❌ 部署复杂

**适用场景：**
- 数据隐私要求高
- 成本敏感
- 长期运行
- 离线场景

### 4.3 推荐选择

**本项目推荐：Claude Sonnet**

**理由：**
1. 推理能力强，适合实体提取和关系推断
2. 中文能力优秀，适合写真行业中文数据
3. 上下文长度长（200K），适合长文本处理
4. 成本相对较低（相比 GPT-4）
5. 速率限制宽松，适合批量处理

**备选方案：**
- **PoC 阶段：** 通义千问 / 智谱 GLM（成本最低）
- **生产阶段：** Claude Sonnet（平衡质量和成本）
- **隐私场景：** Ollama 本地部署（数据不出域）

### 4.4 模型配置示例

```python
# Claude Sonnet 配置
import anthropic

client = anthropic.Anthropic(api_key="your_api_key")

def extract_entities_with_claude(text):
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"""
            从以下文本中提取实体和关系：

            文本：{text}

            请以 JSON 格式返回：
            {{
              "entities": [...],
              "relationships": [...]
            }}
            """
        }]
    )
    return response.content[0].text
```

```python
# 通义千问配置
import dashscope

def extract_entities_with_qwen(text):
    response = dashscope.Generation.call(
        model='qwen-plus',
        messages=[{
            'role': 'user',
            'content': f'从以下文本中提取实体和关系：{text}'
        }]
    )
    return response['output']['text']
```

```python
# Ollama 本地模型配置
import ollama

def extract_entities_with_ollama(text):
    response = ollama.chat(
        model='qwen2',
        messages=[{
            'role': 'user',
            'content': f'从以下文本中提取实体和关系：{text}'
        }]
    )
    return response['message']['content']
```

---

## 5. 向量数据库对比

### 5.1 Chroma vs FAISS vs Milvus vs Qdrant

| 特性 | Chroma | FAISS | Milvus | Qdrant |
|------|--------|-------|--------|--------|
| **开源协议** | Apache 2.0 | MIT | Apache 2.0 | Apache 2.0 |
| **部署方式** | 本地/云端 | 本地 | 本地/集群 | 本地/集群 |
| **开发语言** | Python | C++ | Go | Rust |
| **易用性** | 高 | 中等 | 中等 | 高 |
| **学习曲线** | 低 | 中等 | 中等 | 低 |
| **性能** | 中等 | 高 | 高 | 高 |
| **扩展性** | 中等 | 低（本地） | 高 | 高 |
| **功能丰富度** | 中等 | 低 | 高 | 高 |
| **内存占用** | 中等 | 高 | 中等 | 低 |
| **支持语言** | Python | Python/C++ | 多语言 | 多语言 |
| **索引类型** | HNSW | 多种 | 多种 | HNSW |
| **实时更新** | 支持 | 不支持 | 支持 | 支持 |
| **持久化** | 支持 | 需自行实现 | 支持 | 支持 |
| **监控** | 基础 | 无 | 丰富 | 丰富 |
| **适用场景** | PoC/原型 | 研究/离线 | 生产/大规模 | 生产/中等规模 |
| **集成难度** | 低 | 中等 | 中等 | 低 |

### 5.2 详细对比

#### Chroma
**优势：**
- ✅ API 简洁易用
- ✅ Python 原生支持
- ✅ 开箱即用
- ✅ 持久化支持
- ✅ 适合快速原型

**劣势：**
- ❌ 性能中等
- ❌ 扩展性有限
- ❌ 监控功能少

**适用场景：**
- PoC 原型
- 小规模应用
- 快速开发

#### FAISS（Facebook AI Similarity Search）
**优势：**
- ✅ 性能极高（C++ 实现）
- ✅ 支持多种索引类型
- ✅ Facebook 维护
- ✅ 适合研究

**劣势：**
- ❌ 学习曲线陡峭
- ❌ 需自行实现持久化
- ❌ 不支持实时更新
- ❌ 扩展性差

**适用场景：**
- 离线检索
- 研究实验
- 高性能场景

#### Milvus
**优势：**
- ✅ 性能高
- ✅ 扩展性强（分布式）
- ✅ 功能丰富
- ✅ 监控完善
- ✅ 适合大规模部署

**劣势：**
- ❌ 部署复杂
- ❌ 学习曲线陡峭
- ❌ 资源占用大

**适用场景：**
- 生产环境
- 大规模数据
- 企业级应用

#### Qdrant
**优势：**
- ✅ 性能高（Rust 实现）
- ✅ API 简洁
- ✅ 扩展性好
- ✅ 内存占用低
- ✅ 监控丰富

**劣势：**
- ❌ 社区相对小
- ❌ 文档较少

**适用场景：**
- 生产环境
- 中等规模
- 需要高性能

### 5.3 推荐选择

**PoC 阶段：Chroma**

**理由：**
1. API 简洁，快速上手
2. Python 原生，集成方便
3. 持久化支持，无需额外配置
4. 适合小规模数据验证

**生产阶段：Qdrant**

**理由：**
1. 性能高（Rust 实现）
2. 内存占用低
3. 扩展性好
4. 监控丰富
5. API 简洁易用

**大规模场景：Milvus**

**理由：**
1. 分布式架构
2. 性能极高
3. 功能丰富
4. 适合百万级向量

### 5.4 代码示例

#### Chroma 使用示例
```python
import chromadb

# 创建客户端
client = chromadb.Client()

# 创建集合
collection = client.create_collection(name="documents")

# 添加文档
collection.add(
    documents=["这是文档1", "这是文档2"],
    metadatas=[{"source": "file1"}, {"source": "file2"}],
    ids=["doc1", "doc2"]
)

# 查询
results = collection.query(
    query_texts=["查询文本"],
    n_results=2
)
```

#### Qdrant 使用示例
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 创建客户端
client = QdrantClient(url="http://localhost:6333")

# 创建集合
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# 添加文档
client.upsert(
    collection_name="documents",
    points=[
        PointStruct(id=1, vector=[0.1, 0.2, 0.3], payload={"text": "文档1"}),
        PointStruct(id=2, vector=[0.4, 0.5, 0.6], payload={"text": "文档2"})
    ]
)

# 查询
results = client.search(
    collection_name="documents",
    query_vector=[0.1, 0.2, 0.3],
    limit=2
)
```

---

## 6. Python 客户端对比

### 6.1 py2neo vs neo4j official driver

| 特性 | py2neo | neo4j-driver |
|------|--------|--------------|
| **API 风格** | 对象导向（ORM 风格） | 驱动式（接近原生） |
| **学习曲线** | 低 | 中等 |
| **性能** | 中等 | 高 |
| **功能完整度** | 中等 | 高 |
| **维护状态** | 维护缓慢 | 活跃维护 |
| **文档质量** | 中等 | 优秀 |
| **Cypher 支持** | 好 | 优秀 |
| **事务支持** | 基础 | 强大 |
| **异步支持** | 无 | 有 |
| **类型安全** | 弱 | 强 |
| **错误处理** | 基础 | 完善 |
| **适用场景** | 快速原型 | 生产环境 |

### 6.2 详细对比

#### py2neo
**优势：**
- ✅ API 简洁，对象导向
- ✅ 适合快速原型
- ✅ Python 风格明显
- ✅ 学习成本低

**劣势：**
- ❌ 性能不如官方驱动
- ❌ 维护缓慢
- ❌ 功能不完整
- ❌ 无异步支持

**适用场景：**
- 快速原型
- 学习 Neo4j
- 小规模项目

#### neo4j-driver（官方驱动）
**优势：**
- ✅ 性能高
- ✅ 功能完整
- ✅ 官方维护
- ✅ 异步支持
- ✅ 事务支持强大

**劣势：**
- ❌ API 驱动式，不够直观
- ❌ 学习曲线陡峭

**适用场景：**
- 生产环境
- 高性能需求
- 大规模项目

### 6.3 代码示例

#### py2neo 示例
```python
from py2neo import Graph, Node, Relationship

# 连接 Neo4j
graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))

# 创建节点
customer = Node("Customer", name="张三", phone="13800138000")
graph.create(customer)

# 创建关系
order = Node("Order", order_id="ORD001")
graph.create(order)

rel = Relationship(customer, "PLACED", order)
graph.create(rel)

# 查询
result = graph.run("""
    MATCH (c:Customer)-[:PLACED]->(o:Order)
    WHERE c.name = '张三'
    RETURN c, o
""")
```

#### neo4j-driver 示例
```python
from neo4j import GraphDatabase

class Neo4jHandler:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_entity(self, entity_type, properties):
        with self.driver.session() as session:
            session.run(
                f"CREATE (n:{entity_type} $properties)",
                properties=properties
            )

    def create_relationship(self, node1, rel_type, node2):
        with self.driver.session() as session:
            session.run(
                f"MATCH (a), (b) WHERE a.name = $node1 AND b.name = $node2 "
                f"CREATE (a)-[r:{rel_type}]->(b)",
                node1=node1, node2=node2
            )

    def query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

# 使用
handler = Neo4jHandler("bolt://localhost:7687", "neo4j", "password")
handler.create_entity("Customer", {"name": "张三", "phone": "13800138000"})
handler.close()
```

### 6.4 推荐选择

**本项目推荐：neo4j-driver**

**理由：**
1. 官方驱动，性能最优
2. 功能完整，支持所有 Neo4j 特性
3. 异步支持，适合高性能场景
4. 事务支持强大
5. 文档丰富

**PoC 阶段：py2neo**
- 如果追求开发速度
- 如果项目规模小

---

## 7. 最终技术栈推荐

### 7.1 PoC 阶段

| 组件 | 选择 | 理由 |
|------|------|------|
| **图数据库** | Neo4j Community | 生态成熟，学习成本低 |
| **RAG 框架** | LlamaIndex | GraphRAG 原生支持 |
| **LLM** | 通义千问 / 智谱 GLM | 成本最低，适合验证 |
| **向量数据库** | Chroma | 快速原型，易用性好 |
| **Python 客户端** | py2neo | 快速开发 |
| **GraphRAG 实现** | LightRAG | 成本低，快速验证 |

### 7.2 生产阶段

| 组件 | 选择 | 理由 |
|------|------|------|
| **图数据库** | Neo4j Enterprise / NebulaGraph | 根据规模选择 |
| **RAG 框架** | LlamaIndex | 功能完整，稳定可靠 |
| **LLM** | Claude Sonnet | 平衡质量和成本 |
| **向量数据库** | Qdrant | 性能高，内存占用低 |
| **Python 客户端** | neo4j-driver | 性能最优，功能完整 |
| **GraphRAG 实现** | GraphRAG | 检索质量高，功能完整 |

### 7.3 写真行业特定推荐

**写真行业特点：**
- 数据规模中等（10万级订单）
- 关系复杂但结构清晰
- 需要实时查询
- 成本敏感

**推荐配置：**
```yaml
图数据库: Neo4j Community
RAG 框架: LlamaIndex
LLM: Claude Sonnet
向量数据库: Chroma (PoC) / Qdrant (生产)
Python 客户端: neo4j-driver
GraphRAG: LightRAG (初期) -> GraphRAG (后期)
```

**成本估算：**
- Neo4j: 免费（Community）
- Claude: 约 0.5-1 元/千次调用
- 向量数据库: 免费（Chroma）
- 总体成本: 低

**性能预期：**
- 查询响应: < 2 秒
- 并发处理: 100+ QPS
- 数据规模: 10万级节点