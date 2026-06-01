# 坑与最佳实践

## 一、常见坑

### 1. 实体关系歧义

#### 问题描述
在构建知识图谱时，实体和关系的语义不清晰，导致：
- 同一个概念被表示为多个实体
- 同一个关系类型被用于不同的语义
- 查询结果不准确

#### 实际案例

**错误示例：**
```python
# 错误："李摄影师" 既是 Customer 又是 Photographer
CREATE (c:Customer {name: '李摄影师', phone: '13800138000'})
CREATE (p:Photographer {name: '李摄影师', specialty: '人像'})

# 错误：同一个关系类型用于不同场景
CREATE (c1:Customer {name: '张三'})-[:CONNECTED]->(p:Photographer {name: '李摄影师'})
CREATE (c2:Customer {name: '王五'})-[:CONNECTED]->(s:Studio {name: '朝阳工作室'})
```

#### 解决方案

**1. 实体唯一标识**
```python
# 正确：使用唯一标识区分实体
CREATE (c:Customer {customer_id: 'CUST001', name: '李明', phone: '13800138000'})
CREATE (p:Photographer {photographer_id: 'PHOTO001', name: '李摄影师', specialty: '人像'})
```

**2. 关系语义明确**
```python
# 正确：使用明确的关系类型
CREATE (c:Customer {name: '张三'})-[:PREFERRED]->(p:Photographer {name: '李摄影师'})
CREATE (c:Customer {name: '王五'})-[:VISITED]->(s:Studio {name: '朝阳工作室'})
```

**3. 建立约束**
```python
# 创建唯一约束防止重复
CREATE CONSTRAINT FOR (n:Customer) REQUIRE n.customer_id IS UNIQUE
CREATE CONSTRAINT FOR (n:Photographer) REQUIRE n.photographer_id IS UNIQUE
```

**4. 使用属性区分**
```python
# 使用属性区分不同角色
CREATE (p:Person {
    person_id: 'P001',
    name: '李明',
    roles: ['customer', 'photographer'],
    customer_id: 'CUST001',
    photographer_id: 'PHOTO001'
})
```

**来源：** Bilibili Series P6, P12

---

### 2. 批量导入性能问题

#### 问题描述
批量导入数据时性能差，主要原因：
- 逐条插入而非批量操作
- 没有使用事务
- 没有禁用索引和约束
- 没有分批处理

#### 实际案例

**错误示例：**
```python
# 错误：逐条插入
for customer in customers:
    driver.run("""
        CREATE (c:Customer {customer_id: $id, name: $name})
    """, id=customer['id'], name=customer['name'])
    # 10000 条数据需要 30+ 分钟
```

#### 解决方案

**1. 使用 UNWIND 批量插入**
```python
# 正确：批量插入
with driver.session() as session:
    session.run("""
        UNWIND $batch AS customer
        MERGE (c:Customer {customer_id: customer.customer_id})
        SET c.name = customer.name, c.phone = customer.phone
    """, batch=customers)
    # 10000 条数据只需要 1-2 分钟
```

**2. 使用事务**
```python
with driver.session() as session:
    with session.begin_transaction() as tx:
        try:
            for batch in batches:
                tx.run(query, batch=batch)
            tx.commit()
        except Exception as e:
            tx.rollback()
            raise
```

**3. 分批处理**
```python
def batch_import(data, driver, batch_size=1000):
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        import_batch(batch, driver)
        print(f"已导入 {i + len(batch)}/{len(data)}")
```

**4. 禁用索引和约束（导入后重建）**
```python
# 导入前
driver.run("CALL apoc.schema.assert({}, {})")

# 导入数据
import_data(driver)

# 导入后重建索引
create_indexes(driver)
```

**5. 使用 APOC Load CSV（最快）**
```python
driver.run("""
    CALL apoc.load.csv('file:///customers.csv') YIELD row
    MERGE (c:Customer {customer_id: row.customer_id})
    SET c.name = row.name, c.phone = row.phone
""")
```

**来源：** Bilibili Series P14

---

### 3. 查询优化问题

#### 问题描述
查询性能差，主要原因：
- 没有使用索引
- 全表扫描
- 没有使用 LIMIT
- 查询计划不优

#### 实际案例

**错误示例：**
```python
# 错误：全表扫描
result = driver.run("MATCH (n) RETURN n")

# 错误：没有使用索引
result = driver.run("""
    MATCH (c:Customer)
    WHERE c.phone = '13800138000'
    RETURN c
""")

# 错误：没有使用 LIMIT
result = driver.run("""
    MATCH (c:Customer)-[:PLACED]->(o:Order)
    RETURN c, o
""")
```

#### 解决方案

**1. 创建索引**
```python
# 为常用查询字段创建索引
driver.run("CREATE INDEX FOR (n:Customer) ON (n.phone)")
driver.run("CREATE INDEX FOR (n:Customer) ON (n.customer_id)")
driver.run("CREATE INDEX FOR (n:Order) ON (n.order_date)")
```

**2. 使用索引提示**
```python
# 使用 USING INDEX 提示
result = driver.run("""
    USING INDEX c:Customer(phone)
    MATCH (c:Customer {phone: '13800138000'})
    RETURN c
""")
```

**3. 使用 LIMIT**
```python
# 始终使用 LIMIT
result = driver.run("""
    MATCH (c:Customer)-[:PLACED]->(o:Order)
    RETURN c, o
    LIMIT 100
""")
```

**4. 优化查询计划**
```python
# 使用 EXPLAIN 分析查询计划
result = driver.run("""
    EXPLAIN
    MATCH (c:Customer)-[:PLACED]->(o:Order)
    WHERE c.phone = '13800138000'
    RETURN c, o
""")

# 检查是否有全表扫描
for record in result:
    print(record)
```

**5. 避免使用通配符**
```python
# 错误：返回所有属性
result = driver.run("MATCH (n:Customer) RETURN n")

# 正确：只返回需要的属性
result = driver.run("MATCH (n:Customer) RETURN n.name, n.phone")
```

**来源：** Bilibili Series P10

---

### 4. 成本控制问题

#### 问题描述
LLM 调用成本过高，主要原因：
- 频繁调用 LLM
- 上下文过长
- 没有使用缓存
- 没有增量更新

#### 实际案例

**错误示例：**
```python
# 错误：每个实体都调用 LLM
for entity in entities:
    result = llm.extract_entities(entity)  # 10000 个实体 = 10000 次调用

# 错误：上下文过长
context = build_context(100_documents)  # 超过 token 限制
result = llm.generate(query, context)
```

#### 解决方案

**1. 批量处理**
```python
# 正确：批量处理
batch_size = 100
for i in range(0, len(entities), batch_size):
    batch = entities[i:i + batch_size]
    results = llm.extract_entities_batch(batch)  # 100 次调用
```

**2. 使用缓存**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def extract_entity_cached(entity_text: str):
    return llm.extract_entity(entity_text)
```

**3. 上下文压缩**
```python
def compress_context(documents: List[str], max_tokens: int = 4000) -> str:
    """压缩上下文"""
    context = ""
    current_tokens = 0

    for doc in documents:
        doc_tokens = len(doc.split())
        if current_tokens + doc_tokens > max_tokens:
            break
        context += doc + "\n"
        current_tokens += doc_tokens

    return context
```

**4. 增量更新**
```python
def incremental_update(new_data, existing_graph):
    """增量更新"""
    # 只处理新数据
    new_entities = detect_new_entities(new_data, existing_graph)

    # 只对新数据调用 LLM
    for entity in new_entities:
        llm.extract_entity(entity)

    # 更新图谱
    update_graph(new_entities, existing_graph)
```

**5. 使用本地模型**
```python
# 对于简单任务使用本地模型
import ollama

def extract_simple_entities(text):
    """使用本地模型提取简单实体"""
    response = ollama.chat(
        model='qwen2',
        messages=[{
            'role': 'user',
            'content': f'提取实体：{text}'
        }]
    )
    return response['message']['content']
```

**来源：** YouTube Video 2, 3, 6

---

### 5. 数据质量问题

#### 问题描述
数据质量差导致图谱质量差，主要原因：
- 数据不完整
- 数据不一致
- 数据重复
- 数据格式混乱

#### 实际案例

**错误示例：**
```python
# 错误：直接使用原始数据
raw_data = pd.read_csv('data.csv')
import_to_graph(raw_data)  # 包含重复、缺失、格式错误
```

#### 解决方案

**1. 数据清洗**
```python
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """数据清洗"""
    # 删除重复记录
    df = df.drop_duplicates()

    # 删除关键字段缺失的记录
    df = df.dropna(subset=['customer_id', 'order_id'])

    # 填充可选字段
    df['phone'] = df['phone'].fillna('')

    # 标准化数据格式
    df['phone'] = df['phone'].apply(normalize_phone)
    df['email'] = df['email'].apply(normalize_email)

    return df
```

**2. 数据质量检查**
```python
def check_data_quality(df: pd.DataFrame) -> Dict:
    """数据质量检查"""
    report = {
        'total_records': len(df),
        'missing_values': df.isnull().sum().to_dict(),
        'duplicate_records': df.duplicated().sum(),
        'data_types': df.dtypes.to_dict(),
        'unique_values': {col: df[col].nunique() for col in df.columns}
    }

    # 检查关键字段完整性
    for col in ['customer_id', 'order_id']:
        if col in df.columns:
            missing_rate = df[col].isnull().sum() / len(df)
            report[f'{col}_completeness'] = 1 - missing_rate

    return report
```

**3. 数据验证**
```python
def validate_data(df: pd.DataFrame) -> List[str]:
    """数据验证"""
    errors = []

    # 验证电话号码格式
    invalid_phones = df[~df['phone'].str.match(r'^1[3-9]\d{9}$', na=False)]
    if not invalid_phones.empty:
        errors.append(f"无效电话号码: {len(invalid_phones)} 条")

    # 验证邮箱格式
    invalid_emails = df[~df['email'].str.match(r'^[^@]+@[^@]+\.[^@]+$', na=False)]
    if not invalid_emails.empty:
        errors.append(f"无效邮箱: {len(invalid_emails)} 条")

    # 验证日期格式
    try:
        pd.to_datetime(df['order_date'])
    except Exception:
        errors.append("无效日期格式")

    return errors
```

**4. 数据质量报告**
```python
def generate_quality_report(df: pd.DataFrame) -> str:
    """生成数据质量报告"""
    quality = check_data_quality(df)
    errors = validate_data(df)

    report = f"""
    数据质量报告
    ============
    总记录数: {quality['total_records']}
    重复记录: {quality['duplicate_records']}

    缺失值:
    """
    for col, count in quality['missing_values'].items():
        if count > 0:
            rate = count / quality['total_records']
            report += f"  {col}: {count} ({rate:.2%})\n"

    if errors:
        report += "\n数据错误:\n"
        for error in errors:
            report += f"  - {error}\n"

    return report
```

**来源：** Bilibili Series P8

---

## 二、最佳实践

### 1. 参数化查询

#### 最佳实践
始终使用参数化查询，避免 SQL/Cypher 注入，提高查询性能。

#### 代码示例

**错误示例：**
```python
# 错误：字符串拼接
query = f"MATCH (c:Customer {{name: '{customer_name}'}}) RETURN c"
result = driver.run(query)
```

**正确示例：**
```python
# 正确：参数化查询
query = "MATCH (c:Customer {name: $name}) RETURN c"
result = driver.run(query, name=customer_name)
```

**批量参数化查询：**
```python
# 正确：批量参数化
query = """
UNWIND $batch AS item
MATCH (c:Customer {customer_id: item.customer_id})
RETURN c
"""
result = driver.run(query, batch=[{'customer_id': 'C001'}, {'customer_id': 'C002'}])
```

**好处：**
- ✅ 防止注入攻击
- ✅ 提高查询性能（查询计划缓存）
- ✅ 代码更清晰

**来源：** Bilibili Series P5, P6

---

### 2. 索引策略

#### 最佳实践
为常用查询字段创建索引，避免全表扫描。

#### 代码示例

**1. 创建唯一约束**
```python
# 为实体唯一标识创建约束
constraints = [
    "CREATE CONSTRAINT FOR (n:Customer) REQUIRE n.customer_id IS UNIQUE",
    "CREATE CONSTRAINT FOR (n:Order) REQUIRE n.order_id IS UNIQUE",
    "CREATE CONSTRAINT FOR (n:Product) REQUIRE n.product_id IS UNIQUE",
    "CREATE CONSTRAINT FOR (n:Photographer) REQUIRE n.photographer_id IS UNIQUE",
    "CREATE CONSTRAINT FOR (n:Studio) REQUIRE n.studio_id IS UNIQUE"
]

for constraint in constraints:
    driver.run(constraint)
```

**2. 创建普通索引**
```python
# 为常用查询字段创建索引
indexes = [
    "CREATE INDEX FOR (n:Customer) ON (n.phone)",
    "CREATE INDEX FOR (n:Customer) ON (n.name)",
    "CREATE INDEX FOR (n:Order) ON (n.order_date)",
    "CREATE INDEX FOR (n:Order) ON (n.customer_id)",
    "CREATE INDEX FOR (n:Order) ON (n.status)",
    "CREATE INDEX FOR (n:Product) ON (n.category)",
    "CREATE INDEX FOR (n:Photographer) ON (n.specialty)",
    "CREATE INDEX FOR (n:Studio) ON (n.location)"
]

for index in indexes:
    driver.run(index)
```

**3. 创建全文索引**
```python
# 为文本搜索创建全文索引
fulltext_indexes = [
    "CREATE FULLTEXT INDEX customer_name_fulltext FOR (n:Customer) ON EACH [n.name]",
    "CREATE FULLTEXT INDEX product_name_fulltext FOR (n:Product) ON EACH [n.name, n.description]"
]

for index in fulltext_indexes:
    driver.run(index)
```

**4. 查询索引状态**
```python
# 查询所有索引
result = driver.run("SHOW INDEXES")
for record in result:
    print(f"{record['name']}: {record['state']}")

# 查询所有约束
result = driver.run("SHOW CONSTRAINTS")
for record in result:
    print(f"{record['name']}: {record['entityType']}")
```

**索引策略原则：**
- ✅ 为经常查询的字段创建索引
- ✅ 为 WHERE、JOIN 条件字段创建索引
- ✅ 为排序字段创建索引
- ❌ 避免为经常更新的字段创建索引（影响写入性能）
- ❌ 避免创建过多索引（占用存储空间）

**来源：** Bilibili Series P10

---

### 3. 增量更新

#### 最佳实践
使用增量更新机制，只处理变化的数据，降低成本和提高效率。

#### 代码示例

**1. 检测新实体**
```python
def detect_new_entities(new_data, graph_driver):
    """检测新实体"""
    existing_entities = set()

    with graph_driver.session() as session:
        result = session.run("MATCH (n:Customer) RETURN n.customer_id AS id")
        for record in result:
            existing_entities.add(record['id'])

    new_entities = [
        entity for entity in new_data
        if entity['customer_id'] not in existing_entities
    ]

    return new_entities
```

**2. 检测修改的实体**
```python
def detect_modified_entities(new_data, old_data, graph_driver):
    """检测修改的实体"""
    modified_entities = []

    for new_entity in new_data:
        customer_id = new_entity['customer_id']

        with graph_driver.session() as session:
            result = session.run("""
                MATCH (c:Customer {customer_id: $id})
                RETURN c.name AS name, c.phone AS phone
            """, id=customer_id)

            record = result.single()
            if record:
                # 比较字段
                if (record['name'] != new_entity['name'] or
                    record['phone'] != new_entity['phone']):
                    modified_entities.append(new_entity)

    return modified_entities
```

**3. 增量更新实体**
```python
def incremental_update_entities(new_data, graph_driver):
    """增量更新实体"""
    new_entities = detect_new_entities(new_data, graph_driver)
    modified_entities = detect_modified_entities(new_data, old_data, graph_driver)

    with graph_driver.session() as session:
        # 创建新实体
        for entity in new_entities:
            session.run("""
                MERGE (c:Customer {customer_id: $customer_id})
                SET c.name = $name, c.phone = $phone
            """, **entity)

        # 更新修改的实体
        for entity in modified_entities:
            session.run("""
                MATCH (c:Customer {customer_id: $customer_id})
                SET c.name = $name, c.phone = $phone
            """, **entity)

    print(f"创建新实体: {len(new_entities)}")
    print(f"更新实体: {len(modified_entities)}")
```

**4. 增量更新关系**
```python
def incremental_update_relationships(new_data, graph_driver):
    """增量更新关系"""
    with graph_driver.session() as session:
        for item in new_data:
            # 检查关系是否已存在
            result = session.run("""
                MATCH (c:Customer {customer_id: $customer_id})-[:PLACED]->(o:Order {order_id: $order_id})
                RETURN r
            """, customer_id=item['customer_id'], order_id=item['order_id'])

            if not result.single():
                # 创建新关系
                session.run("""
                    MATCH (c:Customer {customer_id: $customer_id})
                    MATCH (o:Order {order_id: $order_id})
                    MERGE (c)-[r:PLACED]->(o)
                    SET r.timestamp = $timestamp
                """, **item)
```

**5. 定期全量同步**
```python
def periodic_full_sync(graph_driver, interval_days=7):
    """定期全量同步"""
    last_sync_date = get_last_sync_date()

    if (datetime.now() - last_sync_date).days >= interval_days:
        print("执行全量同步...")
        full_sync(graph_driver)
        update_last_sync_date()
```

**增量更新好处：**
- ✅ 降低 LLM 调用成本
- ✅ 提高更新效率
- ✅ 支持近实时更新
- ✅ 减少系统负载

**来源：** YouTube Video 3 (GraphRAG 0.4.0)

---

### 4. 错误处理

#### 最佳实践
完善的错误处理机制，提高系统稳定性。

#### 代码示例

**1. 数据库连接错误处理**
```python
from neo4j import GraphDatabase, ServiceUnavailable

class Neo4jHandler:
    def __init__(self, uri, user, password, max_retries=3):
        self.uri = uri
        self.user = user
        self.password = password
        self.max_retries = max_retries
        self.driver = None

    def connect(self):
        """连接数据库，带重试机制"""
        for attempt in range(self.max_retries):
            try:
                self.driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password)
                )
                self.driver.verify_connectivity()
                print("✓ Neo4j 连接成功")
                return True
            except ServiceUnavailable as e:
                print(f"连接失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    raise

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
```

**2. 查询错误处理**
```python
def safe_query(driver, query, parameters=None, retry_on_failure=True):
    """安全查询，带错误处理和重试"""
    max_retries = 3 if retry_on_failure else 1

    for attempt in range(max_retries):
        try:
            with driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except ServiceUnavailable as e:
            print(f"查询失败 (尝试 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise
        except Exception as e:
            print(f"查询错误: {e}")
            raise
```

**3. 数据导入错误处理**
```python
def import_with_error_handling(data, driver):
    """带错误处理的数据导入"""
    success_count = 0
    error_count = 0
    errors = []

    with driver.session() as session:
        with session.begin_transaction() as tx:
            try:
                for item in data:
                    try:
                        tx.run("""
                            MERGE (c:Customer {customer_id: $customer_id})
                            SET c.name = $name
                        """, **item)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        errors.append({
                            'item': item,
                            'error': str(e)
                        })
                        print(f"导入失败: {item.get('customer_id')}: {e}")

                tx.commit()

                print(f"导入完成: 成功 {success_count}, 失败 {error_count}")

                # 保存错误日志
                if errors:
                    save_errors_to_log(errors)

            except Exception as e:
                tx.rollback()
                print(f"事务回滚: {e}")
                raise
```

**4. LLM 调用错误处理**
```python
def safe_llm_call(llm_client, prompt, max_retries=3):
    """安全的 LLM 调用"""
    for attempt in range(max_retries):
        try:
            response = llm_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except anthropic.APIError as e:
            print(f"LLM 调用失败 (尝试 {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise
        except Exception as e:
            print(f"未知错误: {e}")
            raise
```

**5. 日志记录**
```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def query_with_logging(driver, query, parameters=None):
    """带日志记录的查询"""
    logger.info(f"执行查询: {query}")
    logger.debug(f"参数: {parameters}")

    try:
        result = driver.run(query, parameters or {})
        data = [record.data() for record in result]
        logger.info(f"查询成功，返回 {len(data)} 条记录")
        return data
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
        raise
```

**错误处理原则：**
- ✅ 捕获所有可能的异常
- ✅ 提供有意义的错误信息
- ✅ 实现重试机制（对于可恢复错误）
- ✅ 记录详细的日志
- ✅ 优雅降级（对于非关键功能）

**来源：** Bilibili Series P14, P16

---

### 5. 监控与运维

#### 最佳实践
完善的监控和运维体系，确保系统稳定运行。

#### 代码示例

**1. 性能监控**
```python
import time
from functools import wraps

def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time

            logger.info(f"{func.__name__} 执行成功，耗时: {duration:.2f}s")

            # 记录到监控系统
            record_metric(
                name=f"{func.__name__}_duration",
                value=duration,
                tags={"status": "success"}
            )

            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            logger.error(f"{func.__name__} 执行失败，耗时: {duration:.2f}s, 错误: {e}")

            # 记录失败指标
            record_metric(
                name=f"{func.__name__}_duration",
                value=duration,
                tags={"status": "error"}
            )

            raise

    return wrapper

@monitor_performance
def import_data(data, driver):
    """导入数据（带性能监控）"""
    # ... 导入逻辑 ...
    pass
```

**2. 健康检查**
```python
def health_check():
    """健康检查"""
    checks = {
        'neo4j': check_neo4j(),
        'llm': check_llm(),
        'vector_db': check_vector_db()
    }

    all_healthy = all(checks.values())

    return {
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': checks,
        'timestamp': datetime.now().isoformat()
    }

def check_neo4j():
    """检查 Neo4j 连接"""
    try:
        with driver.session() as session:
            session.run("RETURN 1 AS num")
        return True
    except Exception as e:
        logger.error(f"Neo4j 健康检查失败: {e}")
        return False

def check_llm():
    """检查 LLM 连接"""
    try:
        response = llm_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}]
        )
        return True
    except Exception as e:
        logger.error(f"LLM 健康检查失败: {e}")
        return False
```

**3. 告警机制**
```python
def check_and_alert():
    """检查并告警"""
    # 检查 Neo4j 性能
    query_duration = measure_query_time("MATCH (n) RETURN count(n)")

    if query_duration > 5:  # 超过 5 秒
        send_alert(
            title="Neo4j 查询性能告警",
            message=f"查询耗时 {query_duration:.2f}s，超过阈值",
            severity="warning"
        )

    # 检查 LLM 成本
    daily_cost = calculate_daily_cost()

    if daily_cost > 100:  # 超过 100 元
        send_alert(
            title="LLM 成本告警",
            message=f"今日成本 {daily_cost:.2f} 元，超过阈值",
            severity="warning"
        )

    # 检查数据质量
    quality_score = calculate_data_quality()

    if quality_score < 0.9:  # 质量分数低于 0.9
        send_alert(
            title="数据质量告警",
            message=f"数据质量分数 {quality_score:.2f}，低于阈值",
            severity="error"
        )
```

**4. 数据统计**
```python
def generate_statistics(driver):
    """生成统计信息"""
    stats = {}

    with driver.session() as session:
        # 实体统计
        stats['entities'] = {}
        for entity_type in ['Customer', 'Order', 'Product', 'Photographer', 'Studio']:
            result = session.run(f"MATCH (n:{entity_type}) RETURN count(n) AS count")
            stats['entities'][entity_type] = result.single()['count']

        # 关系统计
        stats['relationships'] = {}
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) AS rel_type, count(r) AS count
            ORDER BY count DESC
        """)
        for record in result:
            stats['relationships'][record['rel_type']] = record['count']

        # 图谱密度
        result = session.run("""
            MATCH (n)
            WITH count(n) AS node_count
            MATCH ()-[r]->()
            WITH node_count, count(r) AS rel_count
            RETURN (2.0 * rel_count) / (node_count * (node_count - 1)) AS density
        """)
        stats['density'] = result.single()['density']

    return stats
```

**5. 定期维护**
```python
def periodic_maintenance():
    """定期维护任务"""
    logger.info("开始定期维护...")

    # 1. 清理孤儿节点
    cleanup_orphan_nodes()

    # 2. 重建索引
    rebuild_indexes()

    # 3. 更新统计信息
    update_statistics()

    # 4. 备份数据
    backup_data()

    logger.info("定期维护完成")

def cleanup_orphan_nodes():
    """清理孤儿节点"""
    with driver.session() as session:
        result = session.run("""
            MATCH (n)
            WHERE NOT (n)-[:PLACED|CONTAINS|ASSIGNED_TO|SHOT_AT|PREFERRED|VISITED|PAID|WORKS_AT]-()
            AND NOT ()-[:PLACED|CONTAINS|ASSIGNED_TO|SHOT_AT|PREFERRED|VISITED|PAID|WORKS_AT]-(n)
            DETACH DELETE n
            RETURN count(n) AS deleted_count
        """)
        deleted_count = result.single()['deleted_count']
        logger.info(f"删除孤儿节点: {deleted_count}")
```

**监控与运维原则：**
- ✅ 实时监控关键指标
- ✅ 自动告警机制
- ✅ 定期健康检查
- ✅ 完善的日志记录
- ✅ 定期维护和优化

**来源：** YouTube Video 4, Bilibili Series P16

---

## 三、写真行业特定的注意事项

### 1. 客户隐私保护

**问题：**
- 客户个人信息（电话、邮箱）需要保护
- 拍摄照片需要授权管理

**解决方案：**
```python
# 1. 数据脱敏
def mask_customer_data(customer):
    """脱敏客户数据"""
    masked = customer.copy()

    # 电话号码脱敏
    if 'phone' in masked and masked['phone']:
        phone = masked['phone']
        masked['phone'] = phone[:3] + '****' + phone[-4:]

    # 邮箱脱敏
    if 'email' in masked and masked['email']:
        email = masked['email']
        parts = email.split('@')
        masked['email'] = parts[0][:2] + '***@' + parts[1]

    return masked

# 2. 访问控制
def check_permission(user_id, customer_id):
    """检查访问权限"""
    # 只有授权用户才能查看客户详细信息
    with driver.session() as session:
        result = session.run("""
            MATCH (u:User {user_id: $user_id})-[:HAS_PERMISSION]->(p:Permission)
            WHERE p.type = 'view_customer_details'
            RETURN count(p) > 0 AS has_permission
        """, user_id=user_id)

        return result.single()['has_permission']
```

### 2. 订单状态管理

**问题：**
- 订单状态复杂，需要准确跟踪
- 状态转换需要业务规则

**解决方案：**
```python
# 1. 状态定义
ORDER_STATUS = {
    'pending': '待确认',
    'confirmed': '已确认',
    'shooting': '拍摄中',
    'editing': '后期制作中',
    'completed': '已完成',
    'cancelled': '已取消'
}

# 2. 状态转换规则
def can_transition(current_status, new_status):
    """检查状态转换是否合法"""
    valid_transitions = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['shooting', 'cancelled'],
        'shooting': ['editing', 'cancelled'],
        'editing': ['completed'],
        'completed': [],
        'cancelled': []
    }

    return new_status in valid_transitions.get(current_status, [])

# 3. 状态更新
def update_order_status(order_id, new_status, user_id):
    """更新订单状态"""
    with driver.session() as session:
        # 获取当前状态
        result = session.run("""
            MATCH (o:Order {order_id: $order_id})
            RETURN o.status AS current_status
        """, order_id=order_id)

        current_status = result.single()['current_status']

        # 检查转换是否合法
        if not can_transition(current_status, new_status):
            raise ValueError(f"不能从 {current_status} 转换到 {new_status}")

        # 更新状态
        session.run("""
            MATCH (o:Order {order_id: $order_id})
            SET o.status = $new_status,
                o.updated_at = $timestamp,
                o.updated_by = $user_id
        """, order_id=order_id, new_status=new_status,
           timestamp=datetime.now(), user_id=user_id)

        # 记录状态历史
        session.run("""
            MATCH (o:Order {order_id: $order_id})
            CREATE (h:OrderStatusHistory {
                order_id: $order_id,
                from_status: $from_status,
                to_status: $to_status,
                timestamp: $timestamp,
                user_id: $user_id
            })
            CREATE (o)-[:HAS_HISTORY]->(h)
        """, order_id=order_id, from_status=current_status,
           to_status=new_status, timestamp=datetime.now(), user_id=user_id)
```

### 3. 产品推荐

**问题：**
- 基于客户历史推荐产品
- 考虑季节性和流行趋势

**解决方案：**
```python
def recommend_products(customer_id, limit=5):
    """推荐产品"""
    with driver.session() as session:
        # 1. 查询客户历史订单
        result = session.run("""
            MATCH (c:Customer {customer_id: $customer_id})-[:PLACED]->(o:Order)-[:CONTAINS]->(p:Product)
            RETURN p.category AS category, count(p) AS count
            ORDER BY count DESC
        """, customer_id=customer_id)

        preferred_categories = [record['category'] for record in result]

        # 2. 查询相关产品
        if preferred_categories:
            query = """
            MATCH (p:Product)
            WHERE p.category IN $categories AND p.is_active = true
            AND NOT EXISTS {
                MATCH (c:Customer {customer_id: $customer_id})-[:PLACED]->(o:Order)-[:CONTAINS]->(p)
            }
            RETURN p
            ORDER BY p.rating DESC
            LIMIT $limit
            """
            result = session.run(
                query,
                categories=preferred_categories,
                customer_id=customer_id,
                limit=limit
            )
        else:
            # 如果没有历史，推荐热门产品
            query = """
            MATCH (o:Order)-[:CONTAINS]->(p:Product)
            WHERE p.is_active = true
            RETURN p, count(o) AS order_count
            ORDER BY order_count DESC
            LIMIT $limit
            """
            result = session.run(query, limit=limit)

        products = [record['p'] for record in result]
        return products
```

### 4. 摄影师排班

**问题：**
- 摄影师工作安排
- 避免时间冲突

**解决方案：**
```python
def check_photographer_availability(photographer_id, start_time, end_time):
    """检查摄影师可用性"""
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Photographer {photographer_id: $photographer_id})<-[:ASSIGNED_TO]-(o:Order)
            WHERE o.status IN ['confirmed', 'shooting']
            AND (
                (o.shoot_start_time < $end_time AND o.shoot_end_time > $start_time)
            )
            RETURN count(o) AS conflict_count
        """, photographer_id=photographer_id,
           start_time=start_time, end_time=end_time)

        conflict_count = result.single()['conflict_count']
        return conflict_count == 0

def assign_photographer(order_id, photographer_id, shoot_start_time, shoot_end_time):
    """分配摄影师"""
    # 1. 检查可用性
    if not check_photographer_availability(photographer_id, shoot_start_time, shoot_end_time):
        raise ValueError("摄影师在该时间段不可用")

    # 2. 分配摄影师
    with driver.session() as session:
        session.run("""
            MATCH (o:Order {order_id: $order_id})
            MATCH (p:Photographer {photographer_id: $photographer_id})
            MERGE (o)-[r:ASSIGNED_TO]->(p)
            SET r.assigned_at = $timestamp,
                r.shoot_start_time = $start_time,
                r.shoot_end_time = $end_time
        """, order_id=order_id, photographer_id=photographer_id,
           timestamp=datetime.now(), start_time=shoot_start_time, end_time=shoot_end_time)

        print(f"✓ 订单 {order_id} 已分配给摄影师 {photographer_id}")
```

### 5. 工作室容量管理

**问题：**
- 工作室容量限制
- 避免超载

**解决方案：**
```python
def check_studio_capacity(studio_id, shoot_time, duration):
    """检查工作室容量"""
    with driver.session() as session:
        # 获取工作室容量
        result = session.run("""
            MATCH (s:Studio {studio_id: $studio_id})
            RETURN s.capacity AS capacity
        """, studio_id=studio_id)

        capacity = result.single()['capacity']

        # 计算时间段
        end_time = shoot_time + timedelta(hours=duration)

        # 查询同时段的订单
        result = session.run("""
            MATCH (s:Studio {studio_id: $studio_id})<-[:SHOT_AT]-(o:Order)
            WHERE o.status IN ['confirmed', 'shooting']
            AND (
                (o.shoot_start_time < $end_time AND o.shoot_end_time > $shoot_time)
            )
            RETURN count(o) AS current_count
        """, studio_id=studio_id, shoot_time=shoot_time, end_time=end_time)

        current_count = result.single()['current_count']

        return current_count < capacity

def assign_studio(order_id, studio_id, shoot_time, duration):
    """分配工作室"""
    # 1. 检查容量
    if not check_studio_capacity(studio_id, shoot_time, duration):
        raise ValueError("工作室在该时间段已满")

    # 2. 分配工作室
    with driver.session() as session:
        session.run("""
            MATCH (o:Order {order_id: $order_id})
            MATCH (s:Studio {studio_id: $studio_id})
            MERGE (o)-[r:SHOT_AT]->(s)
            SET r.assigned_at = $timestamp,
                r.shoot_time = $shoot_time,
                r.duration = $duration
        """, order_id=order_id, studio_id=studio_id,
           timestamp=datetime.now(), shoot_time=shoot_time, duration=duration)

        print(f"✓ 订单 {order_id} 已分配到工作室 {studio_id}")
```

---

## 四、总结

### 常见坑总结
1. **实体关系歧义** → 使用唯一标识和明确的关系类型
2. **批量导入性能** → 使用 UNWIND、事务、分批处理
3. **查询优化** → 创建索引、使用 LIMIT、避免全表扫描
4. **成本控制** → 批量处理、使用缓存、增量更新
5. **数据质量** → 数据清洗、质量检查、验证机制

### 最佳实践总结
1. **参数化查询** → 防止注入、提高性能
2. **索引策略** → 为常用查询字段创建索引
3. **增量更新** → 只处理变化的数据
4. **错误处理** → 完善的异常处理和重试机制
5. **监控运维** → 实时监控、自动告警、定期维护

### 写真行业特定注意事项
1. **客户隐私保护** → 数据脱敏、访问控制
2. **订单状态管理** → 状态转换规则、历史记录
3. **产品推荐** → 基于历史、考虑趋势
4. **摄影师排班** → 可用性检查、避免冲突
5. **工作室容量** → 容量限制、避免超载

通过遵循这些坑和最佳实践，可以构建一个稳定、高效、可维护的 GraphRAG 系统。

**来源：** 综合 YouTube 和 Bilibili 视频内容，以及写真行业实际需求