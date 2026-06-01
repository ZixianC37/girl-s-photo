---
name: graph-schema-design
description: 设计Neo4j知识图谱Schema，包括实体类型、关系类型、属性设计和索引约束创建
---

# 图谱Schema设计

## 输入
- Neo4j数据库连接信息（URI、用户名、密码）
- 写真行业业务需求文档
- 数据源结构（飞书表格字段定义）

## 输出
- 完整的Schema定义文件（包含实体类型、关系类型、属性）
- Neo4j约束和索引创建脚本
- Schema验证报告

## 执行步骤
1. **定义实体类型**
   - 根据`/Users/chenzixian/Downloads/写真行业/RAG/docs/knowledge/03-practical-steps.md`步骤3.1，创建6个核心实体：
     - Customer（客户）：customer_id, name, phone, email, gender, age, registration_date, membership_level, total_orders, total_spent, last_order_date, preferences, notes
     - Order（订单）：order_id, customer_id, order_date, total_amount, status, payment_status, payment_method, notes
     - Product（产品/服务）：product_id, name, category, subcategory, price, duration, description, is_active
     - Photographer（摄影师）：photographer_id, name, specialty, rating, experience_years, total_orders, status, bio
     - Studio（工作室）：studio_id, name, location, address, capacity, equipment, is_active
     - Payment（支付记录）：payment_id, order_id, amount, payment_method, payment_date, status

2. **定义关系类型**
   - 根据`03-practical-steps.md`步骤3.1，创建8种关系：
     - PLACED（客户→订单）：timestamp
     - CONTAINS（订单→产品）：quantity, price
     - ASSIGNED_TO（订单→摄影师）：assignment_date, notes
     - SHOT_AT（订单→工作室）：shoot_date, duration
     - PREFERRED（客户→摄影师）：preference_level, last_selected
     - VISITED（客户→工作室）：visit_count, last_visit
     - PAID（订单→支付）：无额外属性
     - WORKS_AT（摄影师→工作室）：start_date, is_primary

3. **创建Schema类**
   ```python
   class PhotoStudioSchema:
       ENTITIES = {...}  # 实体定义
       RELATIONSHIPS = {...}  # 关系定义
   ```

4. **创建约束**
   - 为每个实体的唯一标识字段创建唯一约束：
     - Customer.customer_id
     - Customer.phone
     - Order.order_id
     - Product.product_id
     - Photographer.photographer_id
     - Studio.studio_id
     - Payment.payment_id
   - 使用`CREATE CONSTRAINT IF NOT EXISTS`语句

5. **创建索引**
   - 为常用查询字段创建索引：
     - Customer: name, phone, email
     - Order: customer_id, order_date, status, total_amount
     - Product: name, category, price
     - Photographer: name, specialty, rating
     - Studio: name, location
   - 使用`CREATE INDEX IF NOT EXISTS`语句

6. **创建全文索引**
   - Customer.name（用于模糊搜索）
   - Product.name, Product.description（用于产品搜索）

7. **验证Schema**
   - 查询约束：`SHOW CONSTRAINTS`
   - 查询索引：`SHOW INDEXES`
   - 查询全文索引：`SHOW FULLTEXT INDEXES`

## 检查清单
- [ ] 6个实体类型已完整定义（Customer, Order, Product, Photographer, Studio, Payment）
- [ ] 8种关系类型已完整定义（PLACED, CONTAINS, ASSIGNED_TO, SHOT_AT, PREFERRED, VISITED, PAID, WORKS_AT）
- [ ] 所有实体属性包含类型定义（string, integer, float, date, boolean）
- [ ] 唯一约束已创建（7个约束）
- [ ] 普通索引已创建（至少15个索引）
- [ ] 全文索引已创建（2个全文索引）
- [ ] Schema验证通过（约束和索引数量符合预期）

## 质量验收标准
- 所有唯一约束创建成功（7个约束）
- 所有索引创建成功（15+个索引）
- 全文索引创建成功（2个全文索引）
- 查询性能测试：通过索引查询的响应时间<100ms
- Schema文档完整，包含所有实体、关系、属性的定义和说明

## 常见问题
- **问题1：实体关系歧义**
  - 现象：同一个概念被表示为多个实体，或同一个关系类型用于不同语义
  - 解决：使用唯一标识区分实体，使用明确的关系类型（如PREFERRED vs VISITED）
  - 参考：`/Users/chenzixian/Downloads/写真行业/RAG/docs/knowledge/04-pitfalls-best-practices.md`第1节

- **问题2：索引过多**
  - 现象：创建过多索引导致写入性能下降
  - 解决：只为经常查询的字段创建索引，避免为经常更新的字段创建索引
  - 参考：`04-pitfalls-best-practices.md`第2节"索引策略原则"

- **问题3：约束冲突**
  - 现象：数据导入时违反唯一约束
  - 解决：先使用MERGE语句去重，再导入数据
  - 参考：`03-practical-steps.md`步骤6.1

- **问题4：属性类型不匹配**
  - 现象：查询时类型转换错误
  - 解决：在Schema中明确定义属性类型，导入时使用类型转换函数（toFloat, toInteger, date）
  - 参考：`03-practical-steps.md`步骤2.1"数据类型转换"