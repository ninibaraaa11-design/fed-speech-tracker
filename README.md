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


## 看板内阅读中文完整演讲稿
- 已取消被美联储官网拦截的 iframe 灰色框，改成站内原生“看板内阅读中文全文”。
- 翻译只针对 Federal Reserve Board 官网正式书面演讲（美国政府公开原文），不自动全文翻译第三方媒体专访。
- 数据保存于 `data/translations.json`；译文逐段与英文段落配对、检查段落数后才显示，标记“AI逐段译稿，非官方译文，待人工审校”。
- `Translate Fed Official Speeches to Chinese` 工作流支持手动运行，`speech_url` 可留空（按日期回填未翻译的官方演讲），也可填写特定官方演讲链接。
- 每天北京时间08:20最多尝试翻译一篇；API会产生额外调用费用。若超出60段的处理预算，会跳过而非发布不完整稿件。
- 新翻译记录提交并重新部署后，点击对应发言的“看板内阅读中文全文”即可展开查看；未翻译场次会明确显示待处理，不会将摘要伪装成全文。
