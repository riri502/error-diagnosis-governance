# SKILL-01 单条验证测试

选取 5 条覆盖不同大类的真实报错：
- 权限类 1 条
- 系统异常类 1 条
- 数据校验类 1 条
- 业务状态类 1 条
- 业务规则限制类 1 条

## 验收标准
- 特征提取准确率 > 90%
- 体验判断与人判一致
- 路径判定与人判一致
- 是否输出 evidence_items？
- 是否标注 evidence relevance_level？
- 是否标注 evidence confidence？
- 是否说明 supports 和 limitations？
- 证据不足时是否降级判断？
- 证据冲突时是否进入正确问题池？
