# 从关键词开始学习

输入一个想学的主题，让 AI 先查资料、核对知识点，再用一道诊断题确定起点。后续通过单题反馈、小任务、自己复述和复习记录推进学习。

本仓库包含两个配套 skill：

| Skill | 版本 | 职责 |
|---|---|---|
| [learning-skill](learning-skill/SKILL.md) | 1.1.0 | 学习教练：诊断水平、安排学习阶梯、单题反馈、实践和复习 |
| [knowledge-research](knowledge-research/SKILL.md) | 1.0.0 | 知识检索：阅读原始资料、核对证据、提取知识点并交给教练 |

## 安装到 Codex

需要能使用 skills 的 Codex 环境。联网查资料需要环境提供搜索与网页阅读工具；配套文件工具需要 Python 3，只使用标准库，无需额外 Python 包。脚本不会自行联网检索。

下载仓库：

```bash
git clone https://github.com/aitmr/learning_skill.git
cd learning_skill
```

将 `learning-skill` 和 `knowledge-research` 两个目录并排放入 `~/.codex/skills/`。如果尚未安装同名 skill，可以执行：

```bash
mkdir -p ~/.codex/skills
cp -R -n learning-skill knowledge-research ~/.codex/skills/
```

若已有同名目录，先备份并比较版本，再更新；上面的复制命令不会替换已有文件。确认 Codex 的可用 skills 列表中出现这两个名称后使用。

## 开始使用

明确调用学习教练：

```text
$learning-skill 我想学习 RAG
```

也可以说：

```text
用 learning-skill 教我学习 Agent 与 Harness，每次只问一道题。
```

在已经表达学习意图的对话中，可以继续只发主题关键词。若希望在某个工作区的新对话中也把单个关键词直接作为学习请求，可在该工作区的 `AGENTS.md` 中约定：

```text
用户仅给出学科、技能或主题关键词时，按学习请求处理：
使用 learning-skill，以 knowledge-research 收集并核对资料，再进入一道诊断题。
已有资料和学习记录优先复用；用户回答上一题时先反馈，用户说继续时沿用当前主题。
```

其他用法：

- **用已有材料学习**：提供材料路径，要求教练提取内容并开始诊断。
- **只收集资料**：`$knowledge-research 收集 RAG 入门资料并提取知识点，这次不开始教学。`
- **继续学习**：让教练读取当前主题的学习记录，从待答题或复习继续。
- **只做总结**：明确说“只总结”，不会强制进入测验。

## 学习过程与记录

关键词 → 检索并阅读资料 → 核对证据和前置知识 → 一道诊断题 → 根据真实回答反馈 → 小成果与复述 → 保存进度与复习计划。

学习结果默认保存在当前工作区的 `learning-workspace/<主题>/`，研究材料放在其中的 `research/`。记录留在自己的学习目录中，不放入全局 skill 安装目录。

没有真实作答时，水平保持待诊断。生成材料和通过工具测试不代表已经掌握。复习日期由工具记录；工具本身不发送提醒。

## 配套工具与检查

- `learning-skill/scripts/extract_material.py`：提取 Word、Markdown、TXT，并保留原文定位。
- `learning-skill/scripts/practice.py`：验证题库、保存回答和反馈、计算复习日期、导出 CSV。
- `knowledge-research/scripts/knowledge_packet.py`：验证知识包的引用与依赖，导出知识点、卡片和教学交接文件。

在仓库根目录运行已有测试：

```bash
python3 learning-skill/scripts/test_helpers.py
python3 -m unittest discover -s knowledge-research/scripts -p 'test_*.py' -v
```

参数与数据格式见 [学习工具约定](learning-skill/references/artifacts.md) 和 [知识包交接约定](knowledge-research/references/packet-contract.md)。结构检查不能代替人工核对事实与原始证据。

## 方法与来源

学习方法、第三方参考与新增设计的区别，见 [学习方法依据](learning-skill/references/method-evidence.md)、[学习 skill 参考说明](learning-skill/references/github-selection.md) 和 [研究 skill 改造说明](knowledge-research/references/upstream.md)。

仓库仅包含可复用的 skill 文件与工具，不包含原始视频、Word 文稿、个人学习记录或研究运行快照。来源说明中的原文段落编号和本地运行路径用于追溯作者的构建过程，对应材料未随仓库发布。
