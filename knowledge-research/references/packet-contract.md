# 两个 skill 的交接约定

写知识包、运行工具或与学习教练交接时读取。schema_version 为整数 1。

## knowledge-packet.json 顶层

| 字段 | 内容 |
|---|---|
| schema_version | 1 |
| topic | keyword、resolved_topic、scope、as_of（用户当地日期）、assumptions、excluded |
| queries | id、query、purpose、status（executed／no-results／planned）、source_ids；可用 method 区分 search、open、find |
| sources | id、title、url、publisher、kind、origin_family、accessed_on、published_on（可为空）、read_status、covered_locators、reading_scope、notes_path |
| claims | id、statement、verification、evidence；evidence 含 source_id、locator、note |
| knowledge_points | 知识点数组，字段见下文 |
| coverage | dimension、status（covered／gap／not-needed）、knowledge_point_ids、reason |
| gaps | id、description、affected_knowledge_point_ids、next_query；数组可为空 |
| handoff | teaching_order、first_diagnostic_question；无用户成绩 |

来源 kind 可用 official-docs、original-paper、primary-record、textbook、review、tutorial、secondary、user-material。origin_family 表示共同证据来源，不直接按网站数计独立性。read_status 为 read、partial、unread、failed。notes_path 是相对于知识包的 UTF-8 阅读笔记，要求存在，注明已读范围与限制，不必保存原文。

事实 verification：primary-source 有直接原始依据；corroborated 至少两个不同 origin_family 已读来源支持同一条件；qualified 在 statement 中写限定条件；pending 尚不能教为事实。

证据 locator 必须对应来源 covered_locators 中一项。只读 Abstract 不能引用 Methods。脚本检查范围和引用结构，实际陈述是否受到支持仍需人工核对。

## 每个知识点

```json
{
  "id": "K01",
  "title": "一个可教的概念",
  "objective": "能解释或完成的行为",
  "explanation": "带条件的精简解释",
  "claim_ids": ["CL01"],
  "prerequisites": [],
  "priority": "core",
  "status": "ready",
  "example": "本次教学设计的场景",
  "misconception": "要检查的错误判断",
  "boundary": "适用条件或未覆盖部分",
  "check_question": "一个问题",
  "answer_criteria": ["回答要点"]
}
```

priority 为 core、supporting、later。例子、误区题和顺序默认教学设计；其中新增事实也须引用。ready 知识点关联非 pending 事实，所有前置也 ready，依赖不能成环。teaching_order 按依赖排列全部 ready 知识点。blocked 保留显示缺口，不导出为已确认卡片。

coverage 的 covered 方向关联实际 ready 知识点；gap 和 not-needed 写原因。覆盖地图不等于证明整个领域完整。

## 使用工具

先用环境中的联网工具检索与阅读，再整理 JSON；脚本不会替你搜索或判定事实真伪。

```bash
"$PYTHON_BIN" "$RESEARCH_SKILL_DIR/scripts/knowledge_packet.py" validate "/实际学习目录/research/knowledge-packet.json"
"$PYTHON_BIN" "$RESEARCH_SKILL_DIR/scripts/knowledge_packet.py" export "/实际学习目录/research/knowledge-packet.json" --out "/实际学习目录/research"
```

验证拒绝无效引用、读取范围不符、重复来源、同源转载冒充独立证据、依赖循环和未证实内容进入教学。通过后人工读回再导出资料索引、知识地图、知识点明细、待核对事项、cards.json 与 handoff.json。明细含回答要点，现场不应贴给用户泄露答案。

handoff 指向知识包和卡片，保留范围、排序后的知识点、pending 水平与一道诊断题。教练读取后进入单题反馈、五级阶梯、小成果和复习。用户无需拼接两个 skill。

导出题库的 origin 为 supplement，source_refs 为空数组；另有 knowledge_point_id、external_refs（URL、定位、claim_id）和 answer_criteria，兼容 practice.py。来源由 knowledge_packet.py 核对；practice.py 只管练习状态。

研究更新保留旧包或另建 revision 目录。题目变化后保留旧题库和真实作答状态，不能绕过 practice.py 的 hash 检查覆盖成绩。
