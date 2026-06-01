# 实战落地步骤

## 步骤 1: 环境配置

### 1.1 Neo4j 安装

#### 方式 1: Docker 安装（推荐）

```bash
# 拉取 Neo4j 镜像
docker pull neo4j:5.15.0

# 运行 Neo4j 容器
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -v $PWD/neo4j/data:/data \
  -v $PWD/neo4j/logs:/logs \
  -v $PWD/neo4j/import:/import \
  -v $PWD/neo4j/plugins:/plugins \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:5.15.0

# 查看日志
docker logs -f neo4j

# 停止 Neo4j
docker stop neo4j

# 启动 Neo4j
docker start neo4j
```

#### 方式 2: macOS 安装

```bash
# 使用 Homebrew 安装
brew install neo4j

# 启动 Neo4j
neo4j start

# 停止 Neo4j
neo4j stop

# 重启 Neo4j
neo4j restart
```

#### 方式 3: Ubuntu 安装

```bash
# 添加 Neo4j 仓库
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list

# 更新包列表
sudo apt-get update

# 安装 Neo4j
sudo apt-get install neo4j

# 启动 Neo4j
sudo systemctl start neo4j

# 设置开机自启
sudo systemctl enable neo4j
```

### 1.2 Python 环境配置

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 升级 pip
pip install --upgrade pip

# 安装核心依赖
pip install neo4j>=5.0.0
pip install py2neo>=2021.2.3
pip install llama-index>=0.10.0
pip install llama-index-graph-stores-neo4j
pip install chromadb>=0.4.0
pip install anthropic>=0.18.0
pip install openai>=1.0.0

# 安装数据处理依赖
pip install pandas>=2.0.0
pip install numpy>=1.24.0
pip install python-dotenv>=1.0.0

# 安装 NLP 依赖
pip install spacy>=3.7.0
python -m spacy download zh_core_web_sm

# 安装可视化依赖
pip install matplotlib>=3.7.0
pip install seaborn>=0.12.0
pip install networkx>=3.1.0

# 创建 requirements.txt
pip freeze > requirements.txt
```

### 1.3 环境变量配置

创建 `.env` 文件：

```bash
# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# LLM 配置（Claude）
ANTHROPIC_API_KEY=your_claude_api_key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# LLM 配置（OpenAI - 备用）
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo

# 向量数据库配置
CHROMA_PERSIST_DIR=./chroma_db

# 数据路径
DATA_DIR=./data
MEDICAL_DATA_PATH=./data/medical_records.csv
PHOTO_STUDIO_DATA_PATH=./data/photo_studio.csv

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

加载环境变量：

```python
from dotenv import load_dotenv
import os

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
```

### 1.4 验证安装

```python
# 验证 Neo4j 连接
from neo4j import GraphDatabase

def test_neo4j_connection():
    try:
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        driver.verify_connectivity()
        print("✓ Neo4j 连接成功")

        # 测试查询
        with driver.session() as session:
            result = session.run("RETURN 1 AS num")
            print("✓ Neo4j 查询测试通过")

        driver.close()
    except Exception as e:
        print(f"✗ Neo4j 连接失败: {e}")

test_neo4j_connection()

# 验证 LLM 连接
import anthropic

def test_claude_connection():
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL"),
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}]
        )
        print("✓ Claude 连接成功")
    except Exception as e:
        print(f"✗ Claude 连接失败: {e}")

test_claude_connection()

# 验证 Chroma
import chromadb

def test_chroma_connection():
    try:
        client = chromadb.PersistentClient(path=os.getenv("CHROMA_PERSIST_DIR"))
        collection = client.create_collection(name="test")
        print("✓ Chroma 连接成功")
    except Exception as e:
        print(f"✗ Chroma 连接失败: {e}")

test_chroma_connection()
```

**来源：** Bilibili Series P10, YouTube Video 4

---

## 步骤 2: 数据准备

### 2.1 数据清洗

```python
import pandas as pd
import numpy as np
from typing import Dict, List, Any
import re

def clean_photo_studio_data(csv_path: str) -> pd.DataFrame:
    """清洗写真行业数据"""
    df = pd.read_csv(csv_path, encoding='utf-8')

    # 1. 删除重复记录
    initial_count = len(df)
    df = df.drop_duplicates()
    print(f"删除重复记录: {initial_count - len(df)} 条")

    # 2. 处理缺失值
    critical_columns = ['customer_id', 'order_id', 'order_date']
    for col in critical_columns:
        if col in df.columns:
            df = df.dropna(subset=[col])
            print(f"删除 {col} 为空的记录")

    # 3. 填充可选字段的默认值
    df['phone'] = df['phone'].fillna('')
    df['email'] = df['email'].fillna('')
    df['notes'] = df['notes'].fillna('')

    # 4. 数据类型转换
    if 'order_date' in df.columns:
        df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')

    if 'total_amount' in df.columns:
        df['total_amount'] = pd.to_numeric(df['total_amount'], errors='coerce').fillna(0)

    if 'customer_id' in df.columns:
        df['customer_id'] = df['customer_id'].astype(str)

    # 5. 去除字符串字段的前后空格
    string_columns = df.select_dtypes(include=['object']).columns
    for col in string_columns:
        df[col] = df[col].astype(str).str.strip()

    # 6. 标准化电话号码格式
    def normalize_phone(phone):
        if pd.isna(phone) or phone == '':
            return ''
        # 移除所有非数字字符
        phone = re.sub(r'[^\d]', '', str(phone))
        # 保留中国大陆手机号格式
        if len(phone) == 11 and phone.startswith('1'):
            return phone
        return phone

    if 'phone' in df.columns:
        df['phone'] = df['phone'].apply(normalize_phone)

    # 7. 标准化邮箱格式
    def normalize_email(email):
        if pd.isna(email) or email == '':
            return ''
        email = str(email).lower().strip()
        # 简单验证邮箱格式
        if '@' in email and '.' in email.split('@')[-1]:
            return email
        return ''

    if 'email' in df.columns:
        df['email'] = df['email'].apply(normalize_email)

    return df

# 使用示例
df = clean_photo_studio_data('./data/photo_studio.csv')
print(f"清洗后数据量: {len(df)} 条")
print(df.head())
```

### 2.2 字段提取

```python
def extract_key_fields(df: pd.DataFrame) -> Dict[str, List[Any]]:
    """提取关键字段信息"""

    # 提取客户信息
    customers = df[['customer_id', 'name', 'phone', 'email', 'registration_date']].drop_duplicates()

    # 提取订单信息
    orders = df[['order_id', 'customer_id', 'order_date', 'total_amount', 'status']].drop_duplicates()

    # 提取产品信息
    products = df[['product_id', 'product_name', 'category', 'price', 'duration']].drop_duplicates()

    # 提取摄影师信息
    photographers = df[['photographer_id', 'photographer_name', 'specialty', 'rating']].drop_duplicates()

    # 提取工作室信息
    studios = df[['studio_id', 'studio_name', 'location', 'capacity']].drop_duplicates()

    # 提取订单产品关联
    order_products = df[['order_id', 'product_id']].drop_duplicates()

    # 提取订单摄影师关联
    order_photographers = df[['order_id', 'photographer_id']].drop_duplicates()

    # 提取订单工作室关联
    order_studios = df[['order_id', 'studio_id']].drop_duplicates()

    return {
        'customers': customers.to_dict('records'),
        'orders': orders.to_dict('records'),
        'products': products.to_dict('records'),
        'photographers': photographers.to_dict('records'),
        'studios': studios.to_dict('records'),
        'order_products': order_products.to_dict('records'),
        'order_photographers': order_photographers.to_dict('records'),
        'order_studios': order_studios.to_dict('records')
    }

# 使用示例
key_fields = extract_key_fields(df)
print(f"客户数量: {len(key_fields['customers'])}")
print(f"订单数量: {len(key_fields['orders'])}")
print(f"产品数量: {len(key_fields['products'])}")
```

### 2.3 数据质量检查

```python
def data_quality_check(df: pd.DataFrame) -> Dict[str, Any]:
    """数据质量检查"""
    quality_report = {
        'total_records': len(df),
        'columns': list(df.columns),
        'missing_values': {},
        'duplicate_records': df.duplicated().sum(),
        'data_types': {},
        'unique_values': {},
        'value_ranges': {}
    }

    # 1. 缺失值检查
    for col in df.columns:
        missing_count = df[col].isnull().sum()
        missing_rate = missing_count / len(df)
        quality_report['missing_values'][col] = {
            'count': int(missing_count),
            'rate': round(missing_rate, 4)
        }

    # 2. 数据类型检查
    for col in df.columns:
        quality_report['data_types'][col] = str(df[col].dtype)

    # 3. 唯一值数量
    for col in df.columns:
        quality_report['unique_values'][col] = df[col].nunique()

    # 4. 数值字段范围检查
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    for col in numeric_columns:
        quality_report['value_ranges'][col] = {
            'min': float(df[col].min()),
            'max': float(df[col].max()),
            'mean': float(df[col].mean()),
            'std': float(df[col].std())
        }

    # 5. 关键字段完整性检查
    critical_columns = ['customer_id', 'order_id', 'product_id']
    for col in critical_columns:
        if col in df.columns:
            missing_rate = df[col].isnull().sum() / len(df)
            quality_report[f'{col}_completeness'] = round(1 - missing_rate, 4)

    return quality_report

# 使用示例
quality_report = data_quality_check(df)
print("数据质量报告:")
print(f"总记录数: {quality_report['total_records']}")
print(f"重复记录: {quality_report['duplicate_records']}")
print("\n缺失值率:")
for col, info in quality_report['missing_values'].items():
    if info['rate'] > 0:
        print(f"  {col}: {info['rate']:.2%}")
```

### 2.4 数据导出

```python
import json

def export_processed_data(df: pd.DataFrame, key_fields: Dict, output_dir: str = './data/processed'):
    """导出处理后的数据"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    # 导出清洗后的数据
    df.to_csv(f'{output_dir}/photo_studio_cleaned.csv', index=False, encoding='utf-8')

    # 导出关键字段
    for key, data in key_fields.items():
        # 导出为 JSON
        with open(f'{output_dir}/{key}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 导出为 CSV
        pd.DataFrame(data).to_csv(f'{output_dir}/{key}.csv', index=False, encoding='utf-8')

    print(f"数据已导出到 {output_dir}")

# 使用示例
export_processed_data(df, key_fields)
```

**来源：** Bilibili Series P8, P11

---

## 步骤 3: 图谱 Schema 设计

### 3.1 写真行业实体定义

```python
class PhotoStudioSchema:
    """写真行业知识图谱 Schema 定义"""

    # 实体类型定义
    ENTITIES = {
        'Customer': {
            'description': '客户',
            'properties': {
                'customer_id': {'type': 'string', 'unique': True, 'required': True},
                'name': {'type': 'string', 'indexed': True},
                'phone': {'type': 'string', 'unique': True, 'indexed': True},
                'email': {'type': 'string'},
                'gender': {'type': 'string'},
                'age': {'type': 'integer'},
                'registration_date': {'type': 'date'},
                'membership_level': {'type': 'string'},
                'total_orders': {'type': 'integer'},
                'total_spent': {'type': 'float'},
                'last_order_date': {'type': 'date'},
                'preferences': {'type': 'string'},
                'notes': {'type': 'string'}
            },
            'indexes': ['customer_id', 'phone', 'name'],
            'constraints': ['customer_id', 'phone']
        },
        'Order': {
            'description': '订单',
            'properties': {
                'order_id': {'type': 'string', 'unique': True, 'required': True},
                'customer_id': {'type': 'string', 'indexed': True, 'required': True},
                'order_date': {'type': 'date', 'indexed': True},
                'total_amount': {'type': 'float', 'indexed': True},
                'status': {'type': 'string', 'indexed': True},
                'payment_status': {'type': 'string'},
                'payment_method': {'type': 'string'},
                'notes': {'type': 'string'}
            },
            'indexes': ['order_id', 'customer_id', 'order_date', 'status'],
            'constraints': ['order_id']
        },
        'Product': {
            'description': '产品/服务',
            'properties': {
                'product_id': {'type': 'string', 'unique': True, 'required': True},
                'name': {'type': 'string', 'indexed': True},
                'category': {'type': 'string', 'indexed': True},
                'subcategory': {'type': 'string'},
                'price': {'type': 'float', 'indexed': True},
                'duration': {'type': 'integer'},
                'description': {'type': 'string'},
                'is_active': {'type': 'boolean'}
            },
            'indexes': ['product_id', 'name', 'category'],
            'constraints': ['product_id']
        },
        'Photographer': {
            'description': '摄影师',
            'properties': {
                'photographer_id': {'type': 'string', 'unique': True, 'required': True},
                'name': {'type': 'string', 'indexed': True},
                'specialty': {'type': 'string', 'indexed': True},
                'rating': {'type': 'float', 'indexed': True},
                'experience_years': {'type': 'integer'},
                'total_orders': {'type': 'integer'},
                'status': {'type': 'string'},
                'bio': {'type': 'string'}
            },
            'indexes': ['photographer_id', 'name', 'specialty', 'rating'],
            'constraints': ['photographer_id']
        },
        'Studio': {
            'description': '工作室',
            'properties': {
                'studio_id': {'type': 'string', 'unique': True, 'required': True},
                'name': {'type': 'string', 'indexed': True},
                'location': {'type': 'string', 'indexed': True},
                'address': {'type': 'string'},
                'capacity': {'type': 'integer'},
                'equipment': {'type': 'string'},
                'is_active': {'type': 'boolean'}
            },
            'indexes': ['studio_id', 'name', 'location'],
            'constraints': ['studio_id']
        },
        'Payment': {
            'description': '支付记录',
            'properties': {
                'payment_id': {'type': 'string', 'unique': True, 'required': True},
                'order_id': {'type': 'string', 'indexed': True, 'required': True},
                'amount': {'type': 'float'},
                'payment_method': {'type': 'string'},
                'payment_date': {'type': 'date'},
                'status': {'type': 'string'}
            },
            'indexes': ['payment_id', 'order_id'],
            'constraints': ['payment_id']
        }
    }

    # 关系类型定义
    RELATIONSHIPS = {
        'PLACED': {
            'from': 'Customer',
            'to': 'Order',
            'description': '客户下单',
            'properties': {
                'timestamp': {'type': 'date'}
            }
        },
        'CONTAINS': {
            'from': 'Order',
            'to': 'Product',
            'description': '订单包含产品',
            'properties': {
                'quantity': {'type': 'integer'},
                'price': {'type': 'float'}
            }
        },
        'ASSIGNED_TO': {
            'from': 'Order',
            'to': 'Photographer',
            'description': '订单分配给摄影师',
            'properties': {
                'assignment_date': {'type': 'date'},
                'notes': {'type': 'string'}
            }
        },
        'SHOT_AT': {
            'from': 'Order',
            'to': 'Studio',
            'description': '订单在工作室拍摄',
            'properties': {
                'shoot_date': {'type': 'date'},
                'duration': {'type': 'integer'}
            }
        },
        'PREFERRED': {
            'from': 'Customer',
            'to': 'Photographer',
            'description': '客户偏好摄影师',
            'properties': {
                'preference_level': {'type': 'integer'},
                'last_selected': {'type': 'date'}
            }
        },
        'VISITED': {
            'from': 'Customer',
            'to': 'Studio',
            'description': '客户访问过工作室',
            'properties': {
                'visit_count': {'type': 'integer'},
                'last_visit': {'type': 'date'}
            }
        },
        'PAID': {
            'from': 'Order',
            'to': 'Payment',
            'description': '订单支付',
            'properties': {}
        },
        'WORKS_AT': {
            'from': 'Photographer',
            'to': 'Studio',
            'description': '摄影师在工作室工作',
            'properties': {
                'start_date': {'type': 'date'},
                'is_primary': {'type': 'boolean'}
            }
        }
    }
```

### 3.2 Schema 创建脚本

```python
from neo4j import GraphDatabase

class SchemaCreator:
    """Neo4j Schema 创建器"""

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_constraints(self):
        """创建约束"""
        with self.driver.session() as session:
            # 为每个实体创建唯一约束
            for entity_type, config in PhotoStudioSchema.ENTITIES.items():
                for prop in config.get('constraints', []):
                    query = f"""
                    CREATE CONSTRAINT IF NOT EXISTS FOR (n:{entity_type})
                    REQUIRE n.{prop} IS UNIQUE
                    """
                    session.run(query)
                    print(f"✓ 创建约束: {entity_type}.{prop}")

    def create_indexes(self):
        """创建索引"""
        with self.driver.session() as session:
            for entity_type, config in PhotoStudioSchema.ENTITIES.items():
                for prop in config.get('indexes', []):
                    # 跳过约束字段（已创建唯一约束）
                    if prop not in config.get('constraints', []):
                        query = f"""
                        CREATE INDEX IF NOT EXISTS FOR (n:{entity_type})
                        ON (n.{prop})
                        """
                        session.run(query)
                        print(f"✓ 创建索引: {entity_type}.{prop}")

    def create_fulltext_indexes(self):
        """创建全文索引"""
        with self.driver.session() as session:
            # 为客户姓名创建全文索引
            query = """
            CREATE FULLTEXT INDEX IF NOT EXISTS customer_name_fulltext
            FOR (n:Customer) ON EACH [n.name]
            """
            session.run(query)
            print("✓ 创建全文索引: Customer.name")

            # 为产品名称创建全文索引
            query = """
            CREATE FULLTEXT INDEX IF NOT EXISTS product_name_fulltext
            FOR (n:Product) ON EACH [n.name, n.description]
            """
            session.run(query)
            print("✓ 创建全文索引: Product.name, Product.description")

    def create_schema(self):
        """创建完整 Schema"""
        print("开始创建 Schema...")
        self.create_constraints()
        self.create_indexes()
        self.create_fulltext_indexes()
        print("Schema 创建完成!")

# 使用示例
creator = SchemaCreator(
    uri=os.getenv("NEO4J_URI"),
    user=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD")
)
creator.create_schema()
creator.close()
```

### 3.3 Schema 验证

```python
def verify_schema():
    """验证 Schema 创建是否成功"""
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )

    with driver.session() as session:
        # 查询约束
        constraints_query = "SHOW CONSTRAINTS"
        constraints = session.run(constraints_query).data()
        print(f"✓ 约束数量: {len(constraints)}")

        # 查询索引
        indexes_query = "SHOW INDEXES"
        indexes = session.run(indexes_query).data()
        print(f"✓ 索引数量: {len(indexes)}")

        # 查询全文索引
        fulltext_query = "SHOW FULLTEXT INDEXES"
        fulltext_indexes = session.run(fulltext_query).data()
        print(f"✓ 全文索引数量: {len(fulltext_indexes)}")

    driver.close()

verify_schema()
```

**来源：** Bilibili Series P7, P13

---

## 步骤 4: 实体提取

### 4.1 正则匹配提取

```python
import re
from typing import Dict, List

def extract_entities_regex(text: str) -> Dict[str, List[str]]:
    """使用正则表达式提取实体"""
    entities = {
        'phone_numbers': [],
        'emails': [],
        'dates': [],
        'order_ids': [],
        'customer_ids': []
    }

    # 提取电话号码
    phone_pattern = r'1[3-9]\d{9}'
    entities['phone_numbers'] = list(set(re.findall(phone_pattern, text)))

    # 提取邮箱
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    entities['emails'] = list(set(re.findall(email_pattern, text)))

    # 提取日期
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    entities['dates'] = list(set(re.findall(date_pattern, text)))

    # 提取订单ID
    order_id_pattern = r'ORD\d{6,10}'
    entities['order_ids'] = list(set(re.findall(order_id_pattern, text)))

    # 提取客户ID
    customer_id_pattern = r'CUST\d{6,10}'
    entities['customer_ids'] = list(set(re.findall(customer_id_pattern, text)))

    return entities

# 使用示例
text = """
客户张三（电话：13800138000，邮箱：zhangsan@example.com）
于 2024-01-15 下单，订单号：ORD2024011501
客户ID：CUST001234
"""
entities = extract_entities_regex(text)
print(entities)
```

### 4.2 NLP 实体识别

```python
import spacy
from typing import Dict, List, Tuple

# 加载中文模型
nlp = spacy.load("zh_core_web_sm")

def extract_entities_nlp(text: str) -> List[Dict[str, Any]]:
    """使用 spaCy 提取实体"""
    doc = nlp(text)

    entities = []
    for ent in doc.ents:
        entities.append({
            'text': ent.text,
            'label': ent.label_,
            'start': ent.start_char,
            'end': ent.end_char,
            'description': spacy.explain(ent.label_)
        })

    return entities

# 使用示例
text = "张三在2024年1月15日下单购买了个人写真套餐，订单号为ORD2024011501"
entities = extract_entities_nlp(text)
for ent in entities:
    print(f"{ent['text']}: {ent['label']} - {ent['description']}")
```

### 4.3 LLM 辅助提取

```python
import anthropic
import json
from typing import Dict, List, Any

class EntityExtractor:
    """使用 LLM 提取实体"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract_entities(self, text: str, entity_types: List[str]) -> Dict[str, List[Dict]]:
        """提取实体"""
        prompt = f"""
        从以下文本中提取指定类型的实体：

        文本：
        {text}

        需要提取的实体类型：
        {', '.join(entity_types)}

        请以 JSON 格式返回，格式如下：
        {{
            "实体类型1": [
                {{"name": "实体名称", "properties": {{"属性1": "值1", ...}}}}
            ],
            "实体类型2": [...]
        }}

        只返回 JSON，不要其他说明。
        """

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            # 解析 JSON 响应
            content = response.content[0].text
            entities = json.loads(content)
            return entities

        except Exception as e:
            print(f"实体提取失败: {e}")
            return {}

# 使用示例
extractor = EntityExtractor(api_key=os.getenv("ANTHROPIC_API_KEY"))

text = """
客户张三（电话：13800138000）于2024年1月15日下单购买了个人写真套餐，
订单号：ORD2024011501，由李摄影师负责拍摄，工作地点在朝阳区工作室。
"""

entities = extractor.extract_entities(
    text,
    entity_types=['Customer', 'Order', 'Product', 'Photographer', 'Studio']
)

print(json.dumps(entities, ensure_ascii=False, indent=2))
```

### 4.4 批量实体提取

```python
def batch_extract_entities(data: List[Dict], extractor: EntityExtractor) -> Dict[str, List[Dict]]:
    """批量提取实体"""
    all_entities = {}

    for item in data:
        # 构建文本
        text = f"""
        客户: {item.get('name', '')}
        电话: {item.get('phone', '')}
        订单号: {item.get('order_id', '')}
        产品: {item.get('product_name', '')}
        摄影师: {item.get('photographer_name', '')}
        工作室: {item.get('studio_name', '')}
        """

        # 提取实体
        entities = extractor.extract_entities(
            text,
            entity_types=['Customer', 'Order', 'Product', 'Photographer', 'Studio']
        )

        # 合并实体
        for entity_type, entity_list in entities.items():
            if entity_type not in all_entities:
                all_entities[entity_type] = []
            all_entities[entity_type].extend(entity_list)

    return all_entities

# 使用示例
data = df.to_dict('records')
all_entities = batch_extract_entities(data, extractor)

for entity_type, entities in all_entities.items():
    print(f"{entity_type}: {len(entities)} 个实体")
```

**来源：** Bilibili Series P11, P15, YouTube Video 5

---

## 步骤 5: 关系构建

### 5.1 关系类型定义

```python
class RelationshipBuilder:
    """关系构建器"""

    def __init__(self, driver):
        self.driver = driver

    def close(self):
        self.driver.close()

    def create_relationship(
        self,
        from_entity_type: str,
        from_entity_id: str,
        from_id_field: str,
        to_entity_type: str,
        to_entity_id: str,
        to_id_field: str,
        relationship_type: str,
        properties: Dict = None
    ):
        """创建关系"""
        with self.driver.session() as session:
            query = f"""
            MATCH (a:{from_entity_type} {{{from_id_field}: $from_id}})
            MATCH (b:{to_entity_type} {{{to_id_field}: $to_id}})
            MERGE (a)-[r:{relationship_type}]->(b)
            SET r += $properties
            RETURN r
            """
            result = session.run(
                query,
                from_id=from_entity_id,
                to_id=to_entity_id,
                properties=properties or {}
            )
            return result.single()
```

### 5.2 批量创建关系

```python
def create_customer_order_relationships(data: List[Dict], driver):
    """批量创建客户-订单关系"""
    with driver.session() as session:
        # 使用 UNWIND 批量创建
        query = """
        UNWIND $batch AS row
        MATCH (c:Customer {customer_id: row.customer_id})
        MATCH (o:Order {order_id: row.order_id})
        MERGE (c)-[r:PLACED]->(o)
        SET r.timestamp = row.order_date
        """

        # 分批处理
        batch_size = 1000
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            session.run(query, batch=batch)
            print(f"✓ 处理 {i + len(batch)}/{len(data)} 条关系")

def create_order_product_relationships(data: List[Dict], driver):
    """批量创建订单-产品关系"""
    with driver.session() as session:
        query = """
        UNWIND $batch AS row
        MATCH (o:Order {order_id: row.order_id})
        MATCH (p:Product {product_id: row.product_id})
        MERGE (o)-[r:CONTAINS]->(p)
        SET r.quantity = row.quantity
        SET r.price = row.price
        """

        batch_size = 1000
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            session.run(query, batch=batch)
            print(f"✓ 处理 {i + len(batch)}/{len(data)} 条关系")
```

### 5.3 数据一致性保证

```python
def validate_relationships(driver):
    """验证关系一致性"""
    with driver.session() as session:
        # 1. 检查孤儿节点
        orphan_nodes_query = """
        MATCH (n)
        WHERE NOT (n)-[:PLACED|CONTAINS|ASSIGNED_TO|SHOT_AT|PREFERRED|VISITED|PAID|WORKS_AT]-()
        AND NOT ()-[:PLACED|CONTAINS|ASSIGNED_TO|SHOT_AT|PREFERRED|VISITED|PAID|WORKS_AT]-(n)
        RETURN labels(n) AS labels, count(n) AS count
        """
        orphan_nodes = session.run(orphan_nodes_query).data()
        print("孤儿节点统计:")
        for node in orphan_nodes:
            print(f"  {node['labels']}: {node['count']}")

        # 2. 检查重复关系
        duplicate_relationships_query = """
        MATCH (a)-[r]->(b)
        WITH a, b, type(r) AS rel_type, count(r) AS count
        WHERE count > 1
        RETURN a.name AS from, rel_type, b.name AS to, count
        LIMIT 10
        """
        duplicate_relationships = session.run(duplicate_relationships_query).data()
        if duplicate_relationships:
            print("警告: 发现重复关系!")
            for rel in duplicate_relationships:
                print(f"  {rel['from']} -[{rel['rel_type']}]-> {rel['to']}: {rel['count']}")

        # 3. 检查关系完整性
        customer_without_orders_query = """
        MATCH (c:Customer)
        WHERE NOT (c)-[:PLACED]->(:Order)
        RETURN count(c) AS count
        """
        result = session.run(customer_without_orders_query).single()
        print(f"没有订单的客户: {result['count']}")

        # 4. 统计关系数量
        relationship_stats_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS relationship_type, count(r) AS count
        ORDER BY count DESC
        """
        relationship_stats = session.run(relationship_stats_query).data()
        print("\n关系统计:")
        for stat in relationship_stats:
            print(f"  {stat['relationship_type']}: {stat['count']}")
```

**来源：** Bilibili Series P6, P12

---

## 步骤 6: 图谱数据导入

### 6.1 批量导入

```python
def import_customers_batch(customers: List[Dict], driver, batch_size=1000):
    """批量导入客户数据"""
    with driver.session() as session:
        query = """
        UNWIND $batch AS customer
        MERGE (c:Customer {customer_id: customer.customer_id})
        SET c.name = customer.name,
            c.phone = customer.phone,
            c.email = customer.email,
            c.gender = customer.gender,
            c.age = customer.age,
            c.registration_date = customer.registration_date,
            c.membership_level = customer.membership_level
        """

        for i in range(0, len(customers), batch_size):
            batch = customers[i:i + batch_size]
            session.run(query, batch=batch)
            print(f"✓ 导入客户 {i + len(batch)}/{len(customers)}")

def import_orders_batch(orders: List[Dict], driver, batch_size=1000):
    """批量导入订单数据"""
    with driver.session() as session:
        query = """
        UNWIND $batch AS order
        MERGE (o:Order {order_id: order.order_id})
        SET o.customer_id = order.customer_id,
            o.order_date = order.order_date,
            o.total_amount = order.total_amount,
            o.status = order.status,
            o.payment_status = order.payment_status,
            o.payment_method = order.payment_method
        """

        for i in range(0, len(orders), batch_size):
            batch = orders[i:i + batch_size]
            session.run(query, batch=batch)
            print(f"✓ 导入订单 {i + len(batch)}/{len(orders)}")
```

### 6.2 事务管理

```python
def import_with_transaction(data: List[Dict], driver):
    """使用事务导入数据"""
    with driver.session() as session:
        with session.begin_transaction() as tx:
            try:
                # 导入客户
                for customer in data:
                    tx.run("""
                        MERGE (c:Customer {customer_id: $customer_id})
                        SET c.name = $name, c.phone = $phone
                    """, customer)

                # 导入订单
                for order in data:
                    tx.run("""
                        MERGE (o:Order {order_id: $order_id})
                        SET o.customer_id = $customer_id, o.total_amount = $total_amount
                    """, order)

                # 提交事务
                tx.commit()
                print("✓ 事务提交成功")

            except Exception as e:
                # 回滚事务
                tx.rollback()
                print(f"✗ 事务回滚: {e}")
                raise
```

### 6.3 性能优化

```python
def optimize_import_performance(driver):
    """优化导入性能"""
    with driver.session() as session:
        # 1. 禁用约束检查（如果数据已验证）
        session.run("CALL apoc.schema.assert({}, {})")

        # 2. 禁用索引
        session.run("CALL apoc.cypher.run('CALL db.indexes() YIELD name CALL db.index.drop(name) RETURN name', {})")

        # 3. 导入数据
        # ... 执行导入操作 ...

        # 4. 重新创建索引
        # ... 重新创建索引 ...

        # 5. 启用约束检查
        session.run("CALL apoc.schema.assert({}, {})")

def use_apoc_load_csv(driver, csv_path):
    """使用 APOC 加载 CSV（最高性能）"""
    with driver.session() as session:
        query = """
        CALL apoc.load.csv('file:///customers.csv') YIELD row
        MERGE (c:Customer {customer_id: row.customer_id})
        SET c.name = row.name,
            c.phone = row.phone,
            c.email = row.email
        """
        session.run(query)
        print("✓ 使用 APOC 导入完成")
```

### 6.4 Cypher 导入示例

```python
# 导入客户
create_customers_cypher = """
LOAD CSV WITH HEADERS FROM 'file:///customers.csv' AS row
MERGE (c:Customer {customer_id: row.customer_id})
SET c.name = row.name,
    c.phone = row.phone,
    c.email = row.email,
    c.gender = row.gender,
    c.age = toInteger(row.age),
    c.registration_date = date(row.registration_date),
    c.membership_level = row.membership_level
"""

# 导入订单
create_orders_cypher = """
LOAD CSV WITH HEADERS FROM 'file:///orders.csv' AS row
MERGE (o:Order {order_id: row.order_id})
SET o.customer_id = row.customer_id,
    o.order_date = date(row.order_date),
    o.total_amount = toFloat(row.total_amount),
    o.status = row.status
"""

# 导入产品
create_products_cypher = """
LOAD CSV WITH HEADERS FROM 'file:///products.csv' AS row
MERGE (p:Product {product_id: row.product_id})
SET p.name = row.name,
    p.category = row.category,
    p.price = toFloat(row.price),
    p.duration = toInteger(row.duration)
"""

# 创建客户-订单关系
create_customer_order_relationships_cypher = """
LOAD CSV WITH HEADERS FROM 'file:///orders.csv' AS row
MATCH (c:Customer {customer_id: row.customer_id})
MATCH (o:Order {order_id: row.order_id})
MERGE (c)-[r:PLACED]->(o)
SET r.timestamp = date(row.order_date)
"""

# 创建订单-产品关系
create_order_product_relationships_cypher = """
LOAD CSV WITH HEADERS FROM 'file:///order_products.csv' AS row
MATCH (o:Order {order_id: row.order_id})
MATCH (p:Product {product_id: row.product_id})
MERGE (o)-[r:CONTAINS]->(p)
SET r.quantity = toInteger(row.quantity),
    r.price = toFloat(row.price)
"""
```

**来源：** Bilibili Series P14

---

## 步骤 7: 查询引擎搭建

### 7.1 Cypher 查询生成

```python
class CypherQueryBuilder:
    """Cypher 查询构建器"""

    @staticmethod
    def build_entity_query(entity_type: str, filters: Dict = None) -> str:
        """构建实体查询"""
        query = f"MATCH (n:{entity_type})"
        if filters:
            conditions = []
            params = {}
            for key, value in filters.items():
                conditions.append(f"n.{key} = ${key}")
                params[key] = value
            query += f" WHERE {' AND '.join(conditions)}"
        query += " RETURN n"
        return query

    @staticmethod
    def build_relationship_query(
        from_entity: str,
        relationship_type: str,
        to_entity: str,
        filters: Dict = None
    ) -> str:
        """构建关系查询"""
        query = f"MATCH (a:{from_entity})-[r:{relationship_type}]->(b:{to_entity})"
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(f"r.{key} = ${key}")
            query += f" WHERE {' AND '.join(conditions)}"
        query += " RETURN a, r, b"
        return query

    @staticmethod
    def build_path_query(
        from_entity: str,
        to_entity: str,
        max_depth: int = 3
    ) -> str:
        """构建路径查询"""
        query = f"""
        MATCH path = (a:{from_entity})-[*1..{max_depth}]-(b:{to_entity})
        RETURN path
        """
        return query
```

### 7.2 向量检索

```python
import chromadb
from sentence_transformers import SentenceTransformer

class VectorRetriever:
    """向量检索器"""

    def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    def create_collection(self, name: str):
        """创建集合"""
        collection = self.client.get_or_create_collection(name=name)
        return collection

    def add_documents(self, collection_name: str, documents: List[str], metadatas: List[Dict]):
        """添加文档"""
        collection = self.client.get_collection(collection_name)
        embeddings = self.embedder.encode(documents).tolist()
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=[str(i) for i in range(len(documents))]
        )

    def search(self, collection_name: str, query: str, top_k: int = 10):
        """搜索"""
        collection = self.client.get_collection(collection_name)
        query_embedding = self.embedder.encode([query]).tolist()
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )
        return results
```

### 7.3 混合检索（Graph + Vector）

```python
class HybridRetriever:
    """混合检索器（图检索 + 向量检索）"""

    def __init__(self, graph_driver, vector_retriever):
        self.graph_driver = graph_driver
        self.vector_retriever = vector_retriever

    def search(self, query: str, collection_name: str = "documents", top_k: int = 10):
        """混合检索"""
        # 1. 图检索
        graph_results = self._graph_search(query)

        # 2. 向量检索
        vector_results = self.vector_retriever.search(collection_name, query, top_k)

        # 3. 合并结果
        merged_results = self._merge_results(graph_results, vector_results)

        return merged_results[:top_k]

    def _graph_search(self, query: str):
        """图检索"""
        with self.graph_driver.session() as session:
            # 使用全文索引搜索
            query_cypher = """
            CALL db.index.fulltext.queryNodes('customer_name_fulltext', $query) YIELD node, score
            RETURN node, score
            LIMIT 10
            """
            results = session.run(query_cypher, query=query)
            return [record for record in results]

    def _merge_results(self, graph_results, vector_results):
        """合并结果"""
        # 简单合并，实际应用中可以根据需要实现更复杂的合并策略
        merged = []
        for result in graph_results:
            merged.append({
                'source': 'graph',
                'data': result['node'],
                'score': result['score']
            })
        for result in vector_results:
            merged.append({
                'source': 'vector',
                'data': result,
                'score': result.get('distances', [0])[0]
            })
        return merged
```

### 7.4 完整查询引擎

```python
class QueryEngine:
    """查询引擎"""

    def __init__(self, graph_driver, vector_retriever, llm_client):
        self.graph_driver = graph_driver
        self.vector_retriever = vector_retriever
        self.llm_client = llm_client
        self.hybrid_retriever = HybridRetriever(graph_driver, vector_retriever)

    def query(self, question: str) -> str:
        """查询"""
        # 1. 检索相关内容
        retrieved_data = self.hybrid_retriever.search(question)

        # 2. 构建上下文
        context = self._build_context(retrieved_data)

        # 3. 生成答案
        answer = self._generate_answer(question, context)

        return answer

    def _build_context(self, retrieved_data) -> str:
        """构建上下文"""
        context = "相关信息：\n"
        for item in retrieved_data:
            if item['source'] == 'graph':
                context += f"- 实体: {item['data']}\n"
            else:
                context += f"- 文档: {item['data']}\n"
        return context

    def _generate_answer(self, question: str, context: str) -> str:
        """生成答案"""
        prompt = f"""
        基于以下信息回答问题：

        问题：{question}

        上下文：
        {context}

        请给出准确、简洁的回答。
        """

        response = self.llm_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text
```

**来源：** Bilibili Series P16, YouTube Video 4

---

## 步骤 8: 问答系统集成

### 8.1 上下文构建

```python
class ContextBuilder:
    """上下文构建器"""

    def __init__(self, graph_driver):
        self.graph_driver = graph_driver

    def build_context_from_graph(self, entities: List[str]) -> str:
        """从图谱构建上下文"""
        context = ""

        with self.graph_driver.session() as session:
            # 获取实体信息
            for entity in entities:
                query = """
                MATCH (n)
                WHERE n.name CONTAINS $entity OR n.customer_id = $entity
                    OR n.order_id = $entity OR n.product_id = $entity
                RETURN n
                LIMIT 10
                """
                results = session.run(query, entity=entity)
                for result in results:
                    node = result['n']
                    context += f"实体: {node.get('name', node.get('customer_id', ''))}\n"
                    context += f"类型: {', '.join(node.labels)}\n"
                    for key, value in node.items():
                        if key not in ['name', 'customer_id']:
                            context += f"  {key}: {value}\n"
                    context += "\n"

            # 获取关系信息
            for entity in entities:
                query = """
                MATCH (n)-[r]-(m)
                WHERE n.name CONTAINS $entity OR n.customer_id = $entity
                RETURN n, type(r) AS rel_type, m
                LIMIT 20
                """
                results = session.run(query, entity=entity)
                for result in results:
                    n = result['n']
                    rel_type = result['rel_type']
                    m = result['m']
                    context += f"关系: {n.get('name', '')} -[{rel_type}]-> {m.get('name', '')}\n"

        return context
```

### 8.2 LLM 调用

```python
class LLMClient:
    """LLM 客户端"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_answer(self, question: str, context: str) -> str:
        """生成答案"""
        prompt = f"""
        你是一个写真行业的知识问答助手。请基于以下上下文信息回答用户的问题。

        上下文信息：
        {context}

        用户问题：
        {question}

        请给出准确、专业、友好的回答。如果上下文中没有相关信息，请诚实告知。
        """

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text
```

### 8.3 对话管理

```python
class ChatManager:
    """对话管理器"""

    def __init__(self, query_engine):
        self.query_engine = query_engine
        self.conversation_history = []

    def chat(self, message: str) -> str:
        """对话"""
        # 添加用户消息到历史
        self.conversation_history.append({
            "role": "user",
            "content": message
        })

        # 生成回答
        answer = self.query_engine.query(message)

        # 添加助手回答到历史
        self.conversation_history.append({
            "role": "assistant",
            "content": answer
        })

        return answer

    def clear_history(self):
        """清除对话历史"""
        self.conversation_history = []

    def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history
```

### 8.4 FastAPI 服务

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="写真行业 GraphRAG 问答系统")

class QuestionRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class AnswerResponse(BaseModel):
    answer: str
    conversation_id: str
    timestamp: str

# 初始化组件
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
vector_retriever = VectorRetriever(os.getenv("CHROMA_PERSIST_DIR"))
llm_client = LLMClient(os.getenv("ANTHROPIC_API_KEY"))
query_engine = QueryEngine(driver, vector_retriever, llm_client)
chat_manager = ChatManager(query_engine)

@app.post("/chat", response_model=AnswerResponse)
async def chat(request: QuestionRequest):
    """问答接口"""
    try:
        answer = chat_manager.chat(request.question)

        return AnswerResponse(
            answer=answer,
            conversation_id=request.conversation_id or "default",
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear_history")
async def clear_history(conversation_id: str = "default"):
    """清除对话历史"""
    chat_manager.clear_history()
    return {"message": "对话历史已清除"}

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**来源：** Bilibili Series P16, YouTube Video 4

---

## 总结

本实战指南涵盖了从环境配置到问答系统部署的完整流程，每个步骤都包含了详细的代码示例和最佳实践。关键要点：

1. **环境配置**：使用 Docker 快速部署 Neo4j，Python 环境隔离
2. **数据准备**：严格的数据清洗和质量检查流程
3. **Schema 设计**：清晰的实体和关系定义，合理的索引策略
4. **实体提取**：结合正则、NLP 和 LLM 的混合提取方法
5. **关系构建**：批量创建和事务管理保证数据一致性
6. **图谱导入**：高性能的批量导入和优化策略
7. **查询引擎**：混合检索（图 + 向量）提升检索质量
8. **问答系统**：完整的上下文构建和对话管理

通过这 8 个步骤，可以快速构建一个功能完整的 GraphRAG 问答系统。