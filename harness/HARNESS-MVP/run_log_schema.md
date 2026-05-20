# HARNESS-MVP 运行记录

记录每条报错是否成功跑完，以及各步骤状态。

## 执行状态字段
- run_id / error_id / timestamp
- step_01_input_ok
- step_02_feature_ok
- step_03_keyword_gen_ok
- step_04_evidence_search_ok
- step_05_evidence_relevance_ok
- step_06_experience_ok
- step_07_priority_ok
- step_08_effect_ok
- step_09_path_ok
- step_10_report_ok
- step_11_review_card_ok

## 证据检索运行状态
- evidence_search_status
- evidence_sources_checked: []
- evidence_sources_available: []
- evidence_sources_unavailable: []
- evidence_total_count
- strong_relevance_count
- medium_relevance_count
- weak_relevance_count
- irrelevant_count
- evidence_conflict_detected
- evidence_sufficiency_status

## 异常
- exception_type（缺字段/低置信/无证据/规则冲突/证据冲突/证据不足）
- current_status
