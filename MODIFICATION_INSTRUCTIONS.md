# Modification Instructions

修改本项目文件时，遵循以下规范：

- `rules/DOC-*`：规则文档，修改后更新执行清单中的产出状态
- `skills/SKILL-*/SKILL.md`：Skill 定义，修改后同步更新相关的 template 和 schema 文件
- `harness/`：运行控制层，HARNESS-MVP 修改需同步考虑对 state/ 和问题池的影响
- `state/`：台账和登记表模板，字段增删需同步更新相关的 DOC 和 Skill
