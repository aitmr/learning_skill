# 月度状态与每日雷达图工具

需要保存课程进度、检查五轮证据、导出每日雷达图时读取。scripts/learning_cycle.py 仅使用 Python 标准库，不联网、不自动评分、不调用豆包、不发提醒、不启动语音。先用 skill 指定的可用工具完成对应动作，再把真实结果保存给脚本核对。

## 位置与命令

先读 ~/.codex/learning-storage.md。下例的 TOPIC_DIR 替换为已确认的 Obsidian `学习记录/<主题>/`，SKILL_DIR 为当前安装位置，日期为用户当地实际日期。program.json 放主题根目录，它管理月计划和课程状态；旧 learning-state.json 保存题级历史，stage-three 模式不另排复习时间。

```bash
python3 "$SKILL_DIR/scripts/learning_cycle.py" init --topic "用户实际主题" --track career --date 2026-10-23 --out "$TOPIC_DIR/program.json"
python3 "$SKILL_DIR/scripts/learning_cycle.py" validate "$TOPIC_DIR/program.json" --date 2026-10-23
python3 "$SKILL_DIR/scripts/learning_cycle.py" report "$TOPIC_DIR/program.json" --date 2026-10-23 --out "$TOPIC_DIR/每日/2026-10-23/雷达-01"
```

分类 foundational、frontier、career。初始文件只有待诊断状态、月份日历与默认六轴，没有任何作答、成绩、完成项。初始化拒绝覆盖已有状态；报告拒绝覆盖目录，同日新证据用雷达-02 等新快照。每天在学习笔记嵌入实际图像，并给图下注释和下一项行动。

## program.json 数据约定

schema_version=2。所有 ID 稳定且唯一。原始回答和反馈用真实 Markdown 文件，相对路径不得逃出主题目录；已有旧记录在续学需要时依保存约定保留历史地带入。先保存原话和反馈，再添加证据。工具验证结构和现存文件，**不能证明文件内容是真实回答，也不判断教练评分是否准确**。

| 字段 | 内容 |
|---|---|
| topic、track、recording_started_on、anchor_date | 主题、学习用途、最早记录日期、最初正式授课日期；anchor_date 跨月保留，面试不重置十天间隔 |
| cycle | start、end、planned_on（实际出计划／修订日期）、plan_status（provisional／final）、days；日历脚本生成，正式计划补全每日目标与课程关联 |
| axes | 六个 id、label、rubric（0–4 五个文字锚点）；按目标校准后同月保持固定，不拿不同维度直接比较 |
| job_seeking | 是否明确面向某职业求职，布尔值；求职用 true，普通在职技能学习不强制调研 JD |
| career_research | 仅 job_seeking=true 的求职正式计划必需：真实岗位调研与要求映射摘要，详见下节 |
| diagnosis | status=pending／complete、rounds；每轮 number、questions 恰好四项、完成后的 summary |
| parts | id、stage_id；用于每部分三遍与遗忘补缺，粒度为知识点或小单元 |
| lessons | id、stage_id、objective、knowledge_point_ids、practice、minutes、pass_score（默认 3）；正式计划把这些写清 |
| stages | id、title、lesson_ids、assessment_id、completed_on；尚未完成日期为 null |
| evidence | id、date、kind、support、score、answer_path、feedback_path、dimensions |
| daily | date、refresh、completed_lessons；按实际日期记录，不按计划课程号伪造日期 |
| assessments | 阶段统测和十天音频面试的计划、实际日期、证据、复盘和执行状态 |
| reviews | 每部分常规三遍或额外遗忘补缺的真实完成记录 |
| gaps | 错误证据、原因、补充内容、练习、复测及 open／resolved |

questions 每项含 id、prompt、kind（profile／ability）和 evidence_id（未答为 null）。profile 是目标条件回答，不给能力分；ability 使用任务或知识证据。前轮未答完不能新增下一轮；二十题均有关联回答与轮次反馈才 complete，未完成月计划保持 provisional。实际回答“不知道”可以记 0 分；明确跳过仍无答题证据，记录理由但不虚构分数。

evidence 的 support 为 independent、hinted、reference、ai-assisted；score 为 0–4 或 null；dimensions 如 {"A1":3,"A5":2}，只能填此任务确实观察的维度，不测不填。profile 的 dimensions 为空。kind 常用 profile、diagnostic、daily-test、stage-test、interview、review、remediation。每天雷达图取每轴最近一个有独立证据日期的均值；旧分标日期，辅助表现单列。若不是全部六轴有独立证据，不画闭合面积。

daily.completed_lessons 项为 lesson_id、test_evidence_ids；要有当天独立日测达到通过分才可记完成，同日可记录多课。基础学科 refresh={"status":"not-required"}；其他分类记录 status（complete／partial／failed）、checked_on、web_log_path、doubao_status、doubao_log_path；受限写 reason 与可继续的稳定范围。complete 要求豆包真实返回并有日志，不代表每个渠道一定找到材料，未找到原因写进日志。

assessments 每项：id、type=interview／stage、due_date、status=planned／overdue／ready-for-voice／completed、actual_date、evidence_ids、retrospective_path。interview 完成另需 mode=audio、voice_observed=true、session_ref；必须实际观察双向音频，转写只能证明内容，不能据此判断声学表现。stage 完成需 stage-test 证据；阶段 completed_on 与检验实际日期一致，必要课程先结束。错过的十天面试保留 due_date，补做时另记 actual_date。

reviews 每项：id、part_id、date、kind=routine／remedial、evidence_ids；routine 还含 pass_number=1／2／3，按日期顺序累计，同日同部分最多一遍；remedial 还含 trigger_gap_id，不增加或清空常规次数。复习要在初学阶段完成之后。gaps 每项含 id、part_id、trigger_evidence_ids、reason、supplement、practice、retest_evidence_ids、status；只有独立 remediation 证据达到 3 分才记 resolved。

## 求职计划的岗位调研检查

```bash
python3 "$SKILL_DIR/scripts/learning_cycle.py" init --topic "用户确认的目标职业" --track career --job-seeking --date 2026-10-27 --out "$TOPIC_DIR/program.json"
```


用户于 2026-10-27 要求先调研岗位再出计划。明确求职时采用 --track career --job-seeking，状态记录 job_seeking=true，正式计划另需 career_research；初始化只是 status=pending，没有查询或读取记录。普通就业技能提升若没有职业求职目标，不加 --job-seeking，不额外要求岗位调研。教练按 knowledge-research 的 job-research.md 实际查完，再填写：

```json
{
  "status": "ready",
  "target_role": "用户目标职业",
  "researched_on": "实际核对日期 YYYY-MM-DD",
  "report_path": "research/jobs/实际日期/岗位调研.md",
  "requirements_map_path": "research/jobs/实际日期/岗位能力映射.md",
  "channels": {"boss": "read", "peer": "read", "official": "read"},
  "read_job_ids": ["公司与原始岗位ID的稳定组合"],
  "limitations": "样本范围与限制；未覆盖渠道及下一步"
}
```

这是格式说明，不是可直接当真实数据执行的调研。status 在准备时可为 pending／partial，正式计划要求 ready。渠道可为 read／partial／blocked／no-results：read 表示该渠道实际打开过至少一条完整 JD，不表示读完所有搜索结果；partial 仅列表或读取不完整，不能单独证明完整岗位要求。三渠道必须实际尝试，任何一个非 read 要写 limitations；不能填未执行的状态。read_job_ids 只记完整阅读并去重的 JD，在报告中逐个对应原始链接与范围。

cycle.planned_on 是实际出计划或修订日期；缺失时兼容为 cycle.start。researched_on 不得晚于 planned_on，两者不得在用户当前日期之后。report_path 与 requirements_map_path 是已有的非空主题内 Markdown 文件。正式课次在知识点、作品和验收处引用要求 ID，具体对应关系保存于岗位能力映射。脚本只核对结构、日期与文件存在，真实岗位内容、匹配程度和映射合理性仍需阅读核对。

续学先根据用户已表达的用途确认 job_seeking，缺字段时默认 false，不从“职业相关”推断用户求职。旧课程明确为职业求职且缺少岗位摘要时，设置 job_seeking=true 并保留所有真实历史与旧计划快照，为后续课程补查岗位并修订计划；资料不足先标 provisional。不重建学习状态、不编造过去做过的调研、不重做已经完成的五轮。普通学科和前沿研究的正式计划无需此字段。

## 诊断跨日与正式开始

初始化时的 anchor_date 和月计划先是暂定。若五轮诊断跨了几天，首次正式授课前将 anchor_date 调为实际正式开始日期，并重新生成 cycle 日历；recording_started_on 保留最早诊断日期，原始回答日期不改。一旦已有正式课程进度，继续复用原 anchor_date，不为重排计划重置面试计时。

## 续学、换月与旧状态

日常先读而不初始化。每次更新前保存必要的旧版本快照或依现有知识库版本机制保留修改；新增实际事件，不把历史数组重置。换月先保存上一月计划快照，再更新 cycle 的开始、结束和每日计划；用 calendar_days(new_start, original_anchor, track) 生成下一月日历，**anchor_date、已做诊断、稳定 parts ID、全部真实证据、阶段、复习与未解缺口均保留**。按旧状态计算尚欠的三遍复习，新课程和阶段用新 ID。无需每月再答五轮，用户目标显著改变再做针对校准。

旧题级初始化时显式用：

```bash
python3 "$SKILL_DIR/scripts/practice.py" init --cards "$TOPIC_DIR/research/cards.json" --state "$TOPIC_DIR/learning-state.json" --topic "当前主题" --goal "可验证成果" --date 2026-10-23 --review-policy stage-three
```

已经存在的 learning-state.json 不重建。下一次真实 record 加 --review-policy stage-three，脚本归档旧政策及各题旧 next_due，然后清除旧活动到期日期，保留全部回答、成绩和历史。不要为完成迁移编造一次作答；迁移前也以本月 program.json 为复习安排的依据。未标新政策的旧调用保持兼容，旧间隔只供历史流程使用，不与月度计划并行。
