---
name: entity-extraction-pipeline
description: 从飞书数据中提取实体和关系，构建完整的实体提取管道
---

# 实体提取管道

## 输入
- 飞书导出的CSV/Excel数据文件
- Neo4j数据库连接
- Claude API密钥（用于LLM辅助提取）

## 输出
- 清洗后的数据文件
- 提取的实体数据（JSON/CSV格式）
- 提取的关系数据（JSON/CSV格式）
- 数据质量报告

## 执行步骤
1. **数据清洗**
   - 根据`/Users/chenzixian/Downloads/写真行业/RAG/docs/knowledge/03-practical-steps.md`步骤2.1，执行以下操作：
     - 删除重复记录：`df.drop_duplicates()`
     - 处理缺失值：删除关键字段缺失的记录（customer_id, order_id, product_id）
     - 填充可选字段：phone, email, notes填充空字符串
     - 数据类型转换：order_date转datetime, total_amount转float
     - 去除前后空格：所有字符串字段
     - 标准化电话号码：`1[3-9]\d{9}`格式
     - 标准化邮箱格式：转换为小写，验证格式

2. **字段提取**
   - 根据`03-practical-steps.md`步骤2.2，提取关键字段：
     - 客户信息：customer_id, name, phone, email, registration_date
     - 订单信息：order_id, customer_id, order_date, total_amount, status
     - 产品信息：product_id, product_name, category, price, duration
     - 摄影师信息：photographer_id, photographer_name, specialty, rating
     - 工作室信息：studio_id, studio_name, location, capacity
     - 关联信息：order_products, order_photographers, order_studios

3. **正则匹配提取**
   - 根据`03-practical-steps.md`步骤4.1，提取以下实体：
     - 电话号码：`1[3-9]\d{9}`
     - 邮箱：`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
     - 日期：`\d{4}-\d{2}-\d{2}`
     - 订单ID：`ORD\d{6,10}`
     - 客户ID：`CUST\d{6,10}`

4. **NLP实体识别**
   - 根据`03-practical-steps.md`步骤4.2，使用spaCy提取实体：
     - 安装中文模型：`python -m spacy download zh_core_web_sm`
     - 提取人名（PERSON）、组织（ORG）、地点（GPE）等实体
     - 识别实体类型和边界

5. **LLM辅助提取**
   - 根据`03-practical-steps.md`步骤4.3，使用Claude API提取复杂实体：
     - 构建包含客户、订单、产品、摄影师、工作室信息的文本
     - 调用Claude API提取结构化实体（JSON格式）
     - 实体类型：Customer, Order, Product, Photographer, Studio

6. **批量处理**
   - 根据`03-practical-steps.md`步骤4.4，批量提取实体：
     - 批量大小：100条记录/批次
     - 使用缓存避免重复提取：`@lru_cache(maxsize=1000)`
     - 合并去重：相同实体ID只保留一条记录

7. **数据质量验证**
   - 根据`03-practical-steps.md`步骤2.3，执行质量检查：
     - 缺失值率：关键字段缺失率<1%
     - 重复记录率：重复记录率<0.1%
     - 数据类型验证：电话号码格式、邮箱格式、日期格式
     - 唯一值数量：检查ID字段的唯一性
     - 数值范围：total_amount>0, rating在0-5之间

8. **数据导出**
   - 根据`03-practical-steps.md`步骤2.4，导出处理后的数据：
     - 导出清洗后的数据：`photo_studio_cleaned.csv`
     - 导出实体数据：`customers.json`, `orders.json`, `products.json`, `photographers.json`, `studios.json`
     - 导出关系数据：`order_products.json`, `order_photographers.json`, `order_studios.json`
     - 导出数据质量报告：`data_quality_report.txt`

## 检查清单
- [ ] 数据清洗完成（去重、缺失值处理、类型转换、格式标准化）
- [ ] 正则匹配提取完成（电话、邮箱、日期、订单ID、客户ID）
- [ ] NLP实体识别完成（人名、组织、地点）
- [ ] LLM辅助提取完成（Customer, Order, Product, Photographer, Studio）
- [ ] 批量处理完成（分批处理、缓存优化、去重合并）
- [ ] 数据质量验证通过（缺失率<1%、重复率<0.1%、格式正确）
- [ ] 数据导出完成（清洗数据、实体数据、关系数据、质量报告）

## 质量验收标准
- 数据清洗率：>95%（去重和缺失值处理）
- 实体提取准确率：>90%（基于样本验证）
- LLM调用次数：不超过原始记录数的5%（使用批量处理和缓存）
- 数据质量分数：>0.9（基于质量检查报告）
- 导出文件完整：所有必需的CSV和JSON文件都已生成

## 常见问题
- **问题1：批量导入性能差**
  - 现象：逐条插入导致性能差，10000条数据需要30+分钟
  - 解决：使用UNWIND批量插入，分批处理（batch_size=1000），使用事务
  - 参考：`/Users/chenzixian/Downloads/写真行业/RAG/docs/knowledge/04-pitfalls-best-practices.md`第2节

- **问题2：LLM调用成本过高**
  - 现象：每个实体都调用LLM，导致成本过高
  - 解决：批量处理（batch_size=100），使用缓存（@lru_cache），使用本地模型处理简单任务
  - 参考：`04-pitfalls-best-practices.md`第4节"成本控制问题"

- **问题3：数据质量差**
  - 现象：数据不完整、不一致、重复、格式混乱
  - 解决：数据清洗（去重、缺失值处理、格式标准化），数据质量检查（缺失率、重复率、格式验证）
  - 参考：`04-pitfalls-best-practices.md`第5节"数据质量问题"

- **问题4：实体提取不准确**
  - 现象：NLP提取的实体类型错误或边界不准确
  - 解决：结合正则匹配、NLP识别、LLM辅助三种方法，人工验证样本数据，调整提取规则
  - 参考：`03-practical-steps.md`步骤4

- **问题5：数据类型转换错误**
  - 现象：导入时类型转换失败（如日期格式不统一）
  - 解决：使用`errors='coerce'`参数，处理异常值，标准化数据格式
  - 参考：`03-practical-steps.md`步骤2.1"数据类型转换"