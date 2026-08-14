# 澄岳智造企业知识库测试包

这是一套完全虚构的中文企业知识库样例，用于测试本项目的文档解析、分块、向量检索、版本管理、引用与回答约束。所有公司、产品、人员、项目、事件和金额均为测试数据。

## 目录

- `knowledge_base_files/`：可直接上传到知识库的现行文件，格式均在项目默认白名单 `md/docx/pdf` 中。
- `version_seed/`：历史版本种子，不应与现行版作为两个独立现行文档同时长期保留。
- `_test_guide/`：测试题、期望答案与验证说明。不要上传到知识库，否则模型会直接检索到答案。

## 推荐导入方式

1. 新建知识库“澄岳智造企业知识中心”。
2. 上传 `knowledge_base_files/` 中全部文件并等待索引完成。
3. 检查 DOCX 是否按标题层级产生 `heading_path`，PDF 是否保留 `page_number`，Markdown 是否按章节拆分。
4. 使用 `_test_guide/test_questions.md` 做基础测试。
5. 做版本测试时，先上传 `version_seed/05_customer_support_sla_v2.1_legacy.md`，标题填写“客户支持服务等级说明”；随后在该文档上创建新版本，上传 `knowledge_base_files/10_customer_support_sla_v2.2.pdf`，然后重新索引最新版本。

## 语料设计

样例刻意包含以下难点：

- 同一概念的近义词：P1、严重事件、关键业务支持、内部 SEV 分级。
- 容易混淆的实体：苏州 `CN-SZ` 与深圳 `CN-SHEN`；AtlasOps Enterprise 与企业支持计划。
- 跨文档关系：远程办公需要同时满足员工手册与信息安全规范；SaaS 采购同时受金额门槛和数据风险控制。
- 版本变化：支持 SLA 2.1 与 2.2 的响应/恢复目标不同，历史事件不能按新版本追溯评价。
- 条件计算：酒店上限、含餐扣减、采购报价数量和服务抵扣比例。
- 内部目标与客户权利边界：`BCP-RTO-042` 与关键业务支持的 4 小时目标数值相同，但含义不同。
- “没有答案”问题：测试集包含公司材料未提供的事实，理想回答应明确知识库不足。

## 建议的文档标签

| 文件 | 建议标签 |
|---|---|
| `01_company_operating_model.md` | 公司治理、组织、授权 |
| `02_employee_handbook_2026.md` | 人力、员工、休假、远程办公 |
| `03_information_security_and_data_classification.md` | 安全、数据分类、事件 |
| `04_product_service_catalog.md` | 产品、保修、订阅、RMA |
| `05_travel_and_expense_policy.docx` | 财务、差旅、报销 |
| `06_procurement_and_supplier_management.md` | 采购、供应商、合同 |
| `07_customer_success_and_escalation_playbook.md` | 客户成功、升级、上线 |
| `08_incident_postmortem_atlasops_2026_02_18.md` | 事件复盘、AtlasOps、遥测 |
| `09_change_release_and_rollback_sop.md` | 研发、变更、发布、回滚 |
| `10_customer_support_sla_v2.2.pdf` | 支持、SLA、服务抵扣 |

## 验收提示

回答应优先引用现行权威文档，保留条件与例外，不要把内部目标说成客户承诺。对于计算题，建议检查回答是否展示关键中间值；对于版本题，检查引用是否来自正确版本；对于跨文档题，检查是否引用了至少两个必要来源。
