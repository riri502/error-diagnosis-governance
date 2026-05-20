# HARNESS-PROD 权限配置

> 阶段：Phase 10 | 状态：占位

数据读取、台账写入、平台调用、运行权限、人工确认权限

## 证据源访问权限（DOC-08 驱动）
- customer_feedback_read_permission
- ticket_read_permission
- tracking_data_read_permission
- business_knowledge_read_permission
- design_knowledge_read_permission
- historical_case_read_permission
- evidence_export_permission

如某类证据源不可访问，运行结果标记 `evidence_source_unavailable`，不默认"没有相关证据"。
