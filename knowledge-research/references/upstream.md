# 先查找，再改造

核查日期：2026-10-15。先用 GitHub 搜索和 skills.sh／skills CLI 找候选，再读取实际 SKILL.md；不是根据标题直接选用。

| 候选 | 已核对的能力 | 与本次需要的差距 | 决定 |
|---|---|---|---|
| [ByteDance deep-research](https://github.com/bytedance/deer-flow/blob/0bbcccfeb117a73cdeb7a8366f56ba71c25d6f5d/skills/public/deep-research/SKILL.md) | 广泛探索、多角度深入阅读、查引用、核对限制、按缺口迭代；CLI 约 2.7K 安装 | 输出面向内容生成，没有可直接接入教学的知识点、依赖和交接文件 | 作为改造基础，保留研究主线 |
| [research-summarizer](https://github.com/alirezarezvani/claude-skills/blob/19392f7a08264ed00486a251f5b2098321771f94/product-team/research-summarizer/skills/research-summarizer/SKILL.md) | 已有文档总结、比较、引用提取、来源质量检查；CLI 约 1.2K 安装 | 正文明说不做 web search，不能独立从关键词收集 | 参考事实与来源位置的核对，不作检索入口 |
| [standardhuman deep-research](https://github.com/standardhuman/deep-research-skill/blob/80912a2766b1e7055a794ab8725462b6cd02391d/SKILL.md) | 范围、查询日志、事实证据、独立来源和矛盾记录 | 更偏决策研究，默认多轮范围问答、较多代理与完整报告 | 参考证据独立性和查询记录，保留轻量教学交接 |

检索到的这些候选未同时提供“仅关键词输入、来源核对、可教知识点与前置依赖、直接交给 learning-skill”的完整过程，因此在最接近的 deep-research 上改造。这里没有声称 GitHub 上不存在其他实现。

## 相对原 skill 的改动

保留：探索 → 按方向深入 → 阅读重要来源 → 核对多样性、限制与时效 → 发现缺口再查 → 综合。

新增：关键词展开与可调整范围、实际阅读状态、逐项事实证据、可教知识点、前置依赖、覆盖地图、结构验证和 teaching handoff。用户无需另找资料或填长问卷。

调整：把原文面向所有内容生成的宽触发范围收窄到学习资料收集；按可教模块决定检索量，不用固定搜索数量证明质量；允许局部内容先教学，未确认部分保留缺口；不自动新增聊天、代理、服务或项目配置。

新脚本为本次交接格式编写，不依赖候选仓库的 API key 或工具名。未复制第三方程序作为运行依赖。候选的固定 commit、文件 SHA-256 和完整研究快照留在项目的 runs/2026-10-15-keyword-integration/upstream，安装包不带这些研究材料。
