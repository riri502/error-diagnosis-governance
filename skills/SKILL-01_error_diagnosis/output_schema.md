# SKILL-01 输出 Schema

## 诊断报告字段
experience_problem / journey_impact / customer_impact / experience_standards_violated / severity / priority_score / priority_level / dimension_scores / estimated_effect / estimated_effect_confidence / recommended_path / optimization_direction / verification_plan / confidence_score

## 证据汇总字段
```
evidence_summary:
  total_evidence_count:
  strong_relevance_count:
  medium_relevance_count:
  weak_relevance_count:
  unavailable_sources: []

evidence_items:
  - evidence_id:
    source_type:           # 客户反馈 / 工单 / 埋点 / 业务知识库 / 设计知识库 / 历史案例
    source_name:
    matched_fields: []
    relevance_level:       # 强相关 / 中相关 / 弱相关 / 不相关
    confidence:            # 高 / 中 / 低
    evidence_summary:      # 一句话摘要
    supports: []           # [支撑的结论1, 支撑的结论2]
    limitations: []        # [限制说明1]

evidence_conflict:
  has_conflict:            # true/false
  conflict_type:
  handling_result:

evidence_sufficiency:
  sufficient_for_diagnosis:         # true/false
  sufficient_for_priority_scoring:  # true/false
  sufficient_for_effect_estimation: # true/false
```

## 复核卡字段
governance_id / error_message / ai_summary / recommended_path / priority / evidence_summary / review_conclusion_enum / reviewer / review_time / notes
