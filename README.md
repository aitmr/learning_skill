# 从关键词开始一个月学习

只给一个主题，让 AI 收集核对资料，用五轮、每轮四题的诊断了解当前状态，再给一个月逐日计划。通过每日实践、测试、雷达图、阶段检验和复盘持续学习。

| Skill | 版本 | 职责 |
|---|---|---|
| [learning-skill](learning-skill/SKILL.md) | 2.1.0 | 五轮诊断、月计划、每日教学和测试、雷达图、语音面试、复盘与三遍复习 |
| [knowledge-research](knowledge-research/SKILL.md) | 1.2.0 | 原始资料核对、可教知识点、求职岗位调研、条件式每日更新及豆包补充 |

## 安装

将两个 skill 目录并排放入 `~/.codex/skills/`。首次安装示例：

```bash
git clone https://github.com/aitmr/learning_skill.git
cd learning_skill
mkdir -p ~/.codex/skills
cp -R -n learning-skill knowledge-research ~/.codex/skills/
```

已有同名目录时，先备份比较版本再更新；上面的命令不会替换已有文件。学习记录保留在自己的主题目录，确认 Codex 的可用 skills 中出现两个名称后使用。

配套脚本使用 Python 3 标准库。联网查资料需要当前环境提供检索和网页阅读工具；豆包需要可用登录会话与桌面／浏览器控制工具，附有 macOS 桌面适配说明。真实语音面试需要双向音频会话。脚本负责数据和证据检查，不自行联网、评分、调用豆包、启动语音或发送提醒。

## 开始使用

```text
$learning-skill 我想学习 RAG
```

面向某职业求职时：

```text
$learning-skill 我想为目标职业求职做准备，先查 BOSS 直聘、类似平台和相关大厂官网的岗位，再诊断并制定一个月学习计划。
```

将“目标职业”替换成自己的方向，已有地区、校招／社招、职级、目标公司和时间预算可一并提供。关键条件会在原有第一轮四题中确认，不另加整套问卷。

已有学习意图的对话中可直接发关键词。若希望工作区的新对话也这样处理，可以在其 `AGENTS.md` 中约定：

```text
只给学科、技能或主题关键词时，使用 learning-skill，衔接 knowledge-research 收集核对资料，再按五轮、每轮四题诊断，制定一个月计划。
明确职业求职目标时，先调研 BOSS 直聘、类似平台和相关大厂官网的真实岗位，再结合诊断出计划。
已有资料和记录优先复用；回答上一题时先反馈，说继续时沿用当前主题。
只总结、只收集资料或管理技能的请求按原范围处理，不强制开课。
```

## 学习流程

| 环节 | 做法 |
|---|---|
| 五轮诊断 | 每轮四题，答完反馈再进入下一轮；目标条件不当能力分 |
| 月计划 | 逐日列目标、知识点、实践、日测和验收，包含阶段检验与复习 |
| 每日学习 | 学完出测试题，通过后可当天学下一课；每课分别测验，日期照实记录 |
| 雷达图 | 根据真实表现显示优势、弱项与补练；未测标待测，辅助练习与独立表现分开 |
| 资料更新 | 前沿／就业授新课前先联网，再用豆包补文章、公众号和视频；基础学科跳过每日例行更新 |
| 检验 | 求职每十个日历日做真实语音面试；学科每阶段整体测试 |
| 复盘 | 找错因、缺项，安排补充、练习与变式复测 |
| 三遍复习 | 后续阶段复习旧内容，每部分常规三遍，跨月保留；以后发现遗忘再补缺 |

日常教学逐题反馈，初次诊断按四题成轮。课程进度与日历分开，提前学课不提前结清未来十天面试。月周期按开始日期和下月对应日期计算，不固定假设每月30天。

### 求职：岗位在计划之前

先调研真实岗位 → 五轮诊断 → 能力差距分析 → 月计划 → 学习、作品与模拟面试。

实际尝试 BOSS 直聘、相关同类平台及相关大厂官方招聘站，打开原始职位描述（JD），区分地区、招聘类型和职级；同岗多渠道去重，必备、加分、职责和硬条件分开。岗位要求关联诊断、知识点、练习、作品和验收。学历和年限等条件单列，不承诺短期课程可以消除。

求职状态用 `job_seeking=true`，初始化可用 `--track career --job-seeking`。正式计划需要岗位调研与能力映射记录；只有摘要、没有完整JD时保留暂定计划。普通学科和没有求职目标的在职技能不强制调研岗位。

详见 [岗位调研规范](knowledge-research/references/job-research.md)。豆包输出是候选资料，核对原始来源后才用于教学，不能替代招聘原文。

## 保存与续学

读取用户已有保存偏好，例如 `~/.codex/learning-storage.md`。指定 Obsidian 时，将笔记、回答、反馈、测试、雷达图、复盘、复习、状态和研究结果保存在同一知识库主题目录，资料放 `research/`。没有指定偏好时才使用 `learning-workspace/<主题>/`。阅读内容用 Markdown，所需 JSON、CSV 保留。

`继续` 会读取真实历史和待答项，不重建课程或每月重做五轮。未作答保持待诊断；生成材料、图表或工具测试通过不代表已经掌握。

其他用法：

- 提供已有材料路径，让教练提取并开始诊断。
- `$knowledge-research 只收集这个主题的入门资料和知识点，这次不开始教学。`
- 明确说“只总结”，按总结范围交付。
- 说“看今天的雷达图”“做阶段测试”“复盘这次测试”，沿用当前主题记录。

## 工具与检查

- `extract_material.py`：提取 Word、Markdown、TXT，保留原文定位。
- `practice.py`：题库验证、题级回答和反馈、CSV导出；月度流程采用 `stage-three`，避免并行旧复习计划。
- `learning_cycle.py`：月度状态校验、求职岗位证据检查、每日SVG雷达图与说明。
- `knowledge_packet.py`：核对引用、阅读范围与依赖，导出知识点、卡片和交接。

在仓库根目录运行全部检查：

```bash
python3 -m unittest discover -s learning-skill/scripts -p 'test_*.py' -v
python3 -m unittest discover -s knowledge-research/scripts -p 'test_*.py' -v
```

目前共33项工具检查，模拟数据仅在隔离临时目录。结构检查不证明资料真实、评分准确或学习有效，原文内容与教学映射仍需阅读核对。

详细约定：[月度流程](learning-skill/references/monthly-cycle.md)、[课程状态与雷达图](learning-skill/references/cycle-tools.md)、[题级工具](learning-skill/references/artifacts.md)、[知识包交接](knowledge-research/references/packet-contract.md)、[每日更新](knowledge-research/references/daily-refresh.md)。

## 方法来源

[学习方法依据](learning-skill/references/method-evidence.md)、[学习skill参考](learning-skill/references/github-selection.md)和[研究skill改造](knowledge-research/references/upstream.md)区分原始材料、上游参考和用户定制流程。

仓库只发布可复用skill、工具与说明。原始视频、Word、个人学习记录、知识库配置、真实成绩、客户端截图和运行快照不随仓库发布。来源说明中的原文编号及本地运行目录用于追溯构建过程。
