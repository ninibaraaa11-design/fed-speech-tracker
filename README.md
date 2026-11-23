# Fed Warsh & Waller Speech Tracker

在线网页： https://ninibaraaa11-design.github.io/fed-speech-tracker/

## 当前功能
- 白底双人物研究看板：历史事件、AI与生产率、货币政策、具体加降息基点、观点演变、原文链接
- GitHub Actions每日北京时间07:30（UTC前一天23:30）扫描美联储**官方演讲目录**
- 对新记录去重，写入 `data/official_updates.json`；官网演讲默认标记“待核验”
- 新闻RSS检索可能的采访/发言**线索**，写入 `data/media_candidates.json`，与正式发言分开
- **可选AI分析**：当仓库设置了 `OPENAI_API_KEY` Secret 后，程序获取官方英文原文、整理中文详细要点、AI观点、利率幅度、短引文证据，与同一人物上次记录比较；结果写入 `data/analyses.json`，标记“AI初稿，建议人工复核”
- `index.html` 自动读取新增官方记录、AI研究结果以及媒体线索；GitHub Pages自动发布

## 开启AI分析（需自行付费的API账户）
1. 在 https://platform.openai.com/api-keys 创建API Key。ChatGPT Plus订阅**不等于**OpenAI API余额。
2. 在GitHub仓库打开 **Settings → Secrets and variables → Actions → New repository secret**
3. **Name** 输入 `OPENAI_API_KEY`，**Secret** 填写密钥原文，保存。**不要把密钥上传为文件，也不要发在聊天中。**
4. 返回 **Actions → Update Fed Speeches → Run workflow** 运行一次。
5. 不设置密钥时，官方发现和媒体线索仍可运行，AI分析将跳过。新发言不会被伪造为已分析。

可选变量：`OPENAI_MODEL`（默认 `gpt-4.1-mini`）、`MAX_AI_PER_RUN`（默认每次最多6篇；限制成本）。工作流已配置默认值，无需设置。

## 数据质量与限制
- 新闻RSS仅为**发现线索**，不能证明某篇新闻是独立专访，也不能代替逐字稿；目前不对媒体线索自动进行AI分析。
- 不会储存第三方新闻/媒体的完整版权文本。完整书面演讲可从原始官方链接阅读。
- AI只分析新发现的官方演讲，引用英文短句经过简单字面比对，但**不代表人工核查**；重点市场判断需回读原文。
- 本项目不是覆盖所有FOMC记者会、国会听证、媒体视频、未发布的现场问答的完整实时系统。
- GitHub定时任务可能延后，并非绝对保证07:30整点执行。
- 现有历史看板的内容是先前研究摘要；未在此项目中逐篇重新核验。
- 出于透明度，仓库是Public，网页及存储的研究数据均公开可见。API Key存放于GitHub Secrets，不应出现在网页代码中。

## 排错
- 查看 **Actions → Update Fed Speeches**，选择运行记录，再打开 `update` 查看每一步日志。
- `data/official_updates.json` 为 `[]`，可能是自2026-11-23以来无新增官方演讲。
- 官方页面打不开时，检索会报错并保留旧数据，不会把错误结果写入。
- AI API未配置或额度不足时，官方发现可以正常运行，AI初稿不产生。
- GitHub Pages URL保持不变。


## 全体官员发言与鹰鸽立场板块（2026-09-01起）
- 看板顶部新增19人预设观察名单（美联储理事会与地区联储主席）；原沃什、沃勒详细档案不变。
- 数据文件：`data/all_fed_officials.json`。已提供9月起地区联储官方页面的初始索引。
- 自动发现：美联储理事会演讲目录，以及12个地区联储演讲索引；每天北京时间07:50增量抓取。不同地区网站结构不同，部分来源可能失败或有遗漏，**不能声称穷尽所有采访和现场问答**。
- 每次记录展示日期、发言人、官方标题与链接、实际抽取到的英文关键原句、中文主题索引；发言倾向仅做关键词证据的**规则初判**（并非人工审核或FOMC投票判断）。
- 顶部鹰鸽总结按照同一官员过去45天最新一条**可明确分类的政策表态**计算；样本不足时直接显示证据不足。不同官员近期未发言、或发言不讨论政策时，不强行归类。
- 新模块不调用OpenAI API；不产生该模块的AI Token费用。原有双人物高级分析独立运行，可能继续消耗API额度。
- 每天更新任务入口： https://github.com/ninibaraaa11-design/fed-speech-tracker/actions/workflows/track-all-fed.yml
- 起始日期不代表目前全部历史已完成回填；初次执行可扩展官方目录中的9月1日以来相关记录，并逐步提取正文。新增记录如需精确中文释义、是否赞成25/50bp的语境判断，必须结合原始逐字稿复核。
