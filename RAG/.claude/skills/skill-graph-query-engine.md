---
name: graph-query-engine
description: 构建混合查询引擎（图谱检索+向量检索），集成LLM生成答案
---

# 图谱查询引擎

## 输入
- Neo4j数据库连接（包含已构建的知识图谱）
- 向量数据库（Chroma）
- Claude API密钥
- 测试问题集

## 输出
- 混合查询引擎（Graph + Vector）
- FastAPI服务（提供HTTP接口）
- 查询性能测试报告
- 问答系统示例

## 执行步骤
1. **Cypher查询构建器**
   - 根据`/Users/chenzixian/Downloads/写真行业/RAG/docs/knowledge/03-practical-steps.md`步骤7.1，实现以下查询：
     - 实体查询：`build_entity_query(entity_type, filters)`
     - 关系查询：`build_relationship_query(from_entity, relationship_type, to_entity, filters)`
     - 路径查询：`build_path_query(from_entity, to_entity, max_depth=3)`
     - 全文搜索：`CALL db.index.fulltext.queryNodes('customer_name_fulltext', $query)`

2. **向量检索器**
   - 根据`03-practical-steps.md`步骤7.2，实现向量检索：
     - 初始化Chroma客户端：`chromadb.PersistentClient(path=persist_dir)`
     - 加载嵌入模型：`SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')`
     - 创建集合：`create_collection(name)`
     - 添加文档：`add_documents(collection_name, documents, metadatas)`
     - 搜索：`search(collection_name, query, top_k=10)`

3. **混合检索器**
   - 根据`03-practical-steps.md`步骤7.3，实现混合检索：
     - 图检索：使用全文索引搜索实体
     - 向量检索：使用Chroma搜索相关文档
     - 结果合并：按分数排序，去重
     - 策略：图检索权重0.6，向量检索权重0.4

4. **查询引擎**
   - 根据`03-practical-steps.md`步骤7.4，实现完整查询引擎：
     - 初始化：graph_driver, vector_retriever, llm_client
     - 查询流程：检索→构建上下文→生成答案
     - 上下文构建：格式化图检索和向量检索结果
     - 答案生成：调用Claude API生成答案

5. **上下文构建器**
   - 根据`03-practical-steps.md`步骤8.1，实现上下文构建：
     - 从图谱获取实体信息：属性、标签
     - 从图谱获取关系信息：关系类型、相关实体
     - 格式化上下文：结构化文本格式

6. **LLM客户端**
   - 根据`03-practical-steps.md`步骤8.2，实现LLM调用：
     - 初始化：`anthropic.Anthropic(api_key=api_key)`
     - 生成答案：`generate_answer(question, context)`
     - Prompt优化：写真行业专业提示词

7. **对话管理器**
   - 根据`03-practical-steps.md`步骤8.3，实现对话管理：
     - 对话历史：存储用户和助手消息
     - 多轮对话：保持上下文连贯性
     - 清除历史：支持重置对话

8. **FastAPI服务**
   - 根据`03-practical-steps.md`步骤8.4，实现HTTP接口：
     - POST /chat：问答接口
     - POST /clear_history：清除对话历史
     - GET /health：健康检查
     - 请求/响应模型：QuestionRequest, AnswerResponse

9. **性能优化**
   - 根据`/Users/chenzixian/Downloads/写真行业/RAG/docs/knowledge/04-pitfalls-best-practices.md`第3节，优化查询：
     - 创建索引：为常用查询字段创建索引
     - 使用LIMIT：限制返回结果数量
     - 避免全表扫描：使用WHERE条件过滤
     - 使用参数化查询：提高查询性能

10. **查询测试**
    - 测试简单查询：单实体查询（客户信息）
    - 测试关系查询：多跳查询（客户→订单→产品）
    - 测试复杂查询：聚合查询（客户总消费）
    - 测试性能：查询响应时间<500ms

## 检查清单
- [ ] Cypher查询构建器实现（实体查询、关系查询、路径查询）
- [ ] 向量检索器实现（Chroma初始化、文档添加、搜索）
- [ ] 混合检索器实现（图检索、向量检索、结果合并）
- [ ] 查询引擎实现（检索→上下文→答案）
- [ ] 上下文构建器实现（实体信息、关系信息、格式化）
- [ ] LLM客户端实现（Claude API调用、答案生成）
- [ ] 对话管理器实现（对话历史、多轮对话）
- [ ] FastAPI服务实现（/chat、/clear_history、/health）
- [ ] 性能优化完成（索引创建、LIMIT使用、参数化查询）
- [ ] 查询测试通过（简单查询、关系查询、复杂查询、性能测试）

## 质量验收标准
- 查询响应时间：简单查询<200ms，复杂查询<500ms
- 答案准确率：>85%（基于人工评估）
- 答案完整性：>90%（基于参考答案对比）
- 服务可用性：>99%（健康检查通过率）
- 并发性能：支持10个并发请求，响应时间<1000ms

## 常见问题
- **问题1：查询性能差**
  - 现象：查询响应时间过长，超过1秒
  - 解决：创建索引、使用LIMIT、避免全表扫描、优化查询计划
  - 参考：`/Users/chenzixian/Downloads/写真行业/RAG/docs/knowledge/04-pitfalls-best-practices.md`第3节"查询优化问题"

- **问题2：答案不准确**
  - 现象：LLM生成的答案与实际数据不符
  - 解决：优化上下文构建（提供更完整的相关信息），优化Prompt（增加行业专业提示词），增加检索深度
  - 参考：`03-practical-steps.md`步骤8.1"上下文构建"

- **问题3：向量检索效果差**
  - 现象：向量检索返回不相关文档
  - 解决：优化嵌入模型（使用更好的预训练模型），优化分块策略，调整检索参数（top_k）
  - 参考：`03-practical-steps.md`步骤7.2"向量检索器"

- **问题4：并发性能差**
  - 现象：多个并发请求时响应时间过长
  - 解决：使用连接池，优化查询（使用索引），增加缓存，水平扩展
  - 参考：`04-pitfalls-best-practices.md`第3节"查询优化问题"

- **问题5：LLM调用失败**
  - 现象：Claude API调用超时或失败
  - 解决：增加重试机制（指数退避），添加错误处理，记录日志，使用备用模型
  - 参考：`04-pitfalls-best-practices.md`第4节"错误处理"