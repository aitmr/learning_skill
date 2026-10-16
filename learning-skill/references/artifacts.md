# 学习成果与工具约定

生成学习包、提取材料、保存进度或导出复习卡时读本文件。

## 轻量学习目录

普通教学只维护实际需要的文件：

- `学习入口.md`：目标、假设、当前水平、待答题、下一步和文件链接。
- `学习路径.md`：阶梯、关键内容和候选课次；尚未诊断时标为暂定。
- `第一课.md` 或后续课：一个目标、简短解释、一个实践任务和验收。
- `速查表.md`：简短结构和五个无答案的自测题。
- `source/`：提取原文与定位记录；不重复复制大视频。
- `cards.json`、`learning-state.json`：需要复习或续学时建立。
- `flashcards.csv`、`review_schedule.csv`：需要离线复习时导出。

一次生成完整学习包时还应交付材料方法总结和来源核对说明。不要为普通一句话解释创建整套目录。练习答案放到单独的 `参考答案.md`，学习入口提示先作答再打开。

## 提取本地材料

以下路径均为调用时的示例。将 `SKILL_DIR` 设为实际 skill 安装目录，`PYTHON_BIN` 设为环境中可用的 Python 3；Word 文件优先使用工作区依赖加载器提供的 Python。变量使用 shell 的标准双引号，保证中文和空格路径有效。

```bash
"$PYTHON_BIN" "$SKILL_DIR/scripts/extract_material.py" "/实际路径/原文.docx" --out "/实际路径/本次学习/source"
```

输出 `source.json` 与 `source.md`，含原文件 SHA-256、稳定段落编号、文稿时间戳和覆盖限制。表格文字也进入段落遍历，但脚本不保存表格版式。Word 图片、页眉、批注的文字不会自动识别。重复运行用新目录，防止旧证据被覆盖。UTF-8 的 `.md`、`.txt` 使用原始行号 `L0001` 等定位。

## 题库

`cards.json` 是一个数组。每张卡对应一个可回答的问题；`origin` 标记原文知识 `material`、补充内容 `supplement` 或教学设计 `design`。

```json
[
  {
    "id": "C01",
    "concept": "学习前诊断",
    "question": "为什么在选择课程之前先做小测试？",
    "answer": "先观察当前能力与缺口，才能安排合适的起点和练习。",
    "origin": "material",
    "source_refs": [{"paragraph_id": "P0054", "timestamp": "07:30"}],
    "tags": ["学习方法", "诊断"]
  }
]
```

验证程序检查字段、唯一 ID 与原文段落／时间戳是否存在；内容是否忠实仍需逐张阅读核对。来自其他文档时分别使用它的提取结果验证，不把多个文档的同名段落混在一个题库内。补充内容另记官方链接和查阅日期。

```bash
"$PYTHON_BIN" "$SKILL_DIR/scripts/practice.py" validate --cards "/实际路径/cards.json" --source "/实际路径/source/source.json"
"$PYTHON_BIN" "$SKILL_DIR/scripts/practice.py" init --cards "/实际路径/cards.json" --state "/实际路径/learning-state.json" --topic "当前主题" --goal "可验证的成果" --date "2026-10-14"
```

`init` 不覆盖已有状态。它将能力设为 `unknown`、诊断设为 `pending`；所有题目未测试，没有成绩，也没有到期日期。不要手工将空记录补成通过。

## 保存真实反馈

用户实际回答后，将回答原文和教练反馈保存成 UTF-8 文本。按教学评分约定给 0–4 分，再记录。`support` 必须标记独立完成、使用提示、参考答案或 AI 辅助。

```bash
"$PYTHON_BIN" "$SKILL_DIR/scripts/practice.py" record --cards "/实际路径/cards.json" --state "/实际路径/learning-state.json" --card C01 --date "2026-10-14" --score 2 --kind explanation --support independent --answer-file "/实际路径/用户回答.txt" --feedback-file "/实际路径/本次反馈.txt"
```

脚本追加历史并原子替换状态文件，避免写到一半损坏。不会替用户回答或评分，不会自动把 `learner_level` 改为已掌握。诊断结束后的整体级别、待答题、作品和下一步由教练依据证据维护。

分数不足 3 时下次安排在翌日；独立完成且分数至少 3 时沿 1、3、7、14、30 天间隔推进。同一天重复答对不扩大间隔。使用提示、参考答案或 AI 辅助的结果保留为练习记录，待独立复测。日期必须显式传入用户当地日期，不依赖运行主机时区。

## 导出复习卡

```bash
"$PYTHON_BIN" "$SKILL_DIR/scripts/practice.py" export --cards "/实际路径/cards.json" --state "/实际路径/learning-state.json" --out "/实际路径/复习导出"
```

`flashcards.csv` 使用 UTF-8 BOM 和三列无表头的 `问题,答案,标签`；在 Anki 导入时将三列映射到 Front、Back、Tags，字段中出现逗号或换行时保持 CSV 引号。CSV 包含答案，不在现场诊断前打开。

`review_schedule.csv` 有表头，按题列出状态、下次日期、作答次数。未测试题的日期为空；日期是计划，不能算复习已完成。文件导出会更新这两个结果文件，真实作答历史留在状态文件里。
