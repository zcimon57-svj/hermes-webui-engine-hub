# 社媒与社区原帖证据 v1

2026-10-09检索。搜索覆盖Reddit（LocalLLaMA、LocalLLM、hermesagent、LLMDevs）、Hacker News、X公开网页索引及GitHub/Hugging Face项目入口。**Reddit/HN已打开原帖；X检索没有核实到可直接引用的相关原始status帖，不声称完成X内部/登录搜索。** 未访问私有Discord、付费群或内部账号。

检索式包括Jev Laya local decision classifier、Laya calibration benchmark、Laya C++ ONNX MLX、Kev/Decider/Winnow以及Hermes self-evolution/curator/EvoSkill；扩展线索必须回到第一方仓库/模型卡才进入技术比较。热门程度、点赞/星数没有作为质量验收。

| ID | 原帖 | 看到什么 / 反面意见 / 如何使用 |
|---|---|---|
| S01 | [Laya作者发布](https://www.reddit.com/r/LocalLLaMA/comments/1wjieap/made_the_horizontal_opensource_model_for_jev_with/) | 本地模型、checkpoint和社区实现入口；超过Jev的标题不是领域验收。 日期：2026-09-18（search/page indication, not API timestamp）。证据类型：AUTHOR_REPORT。 |
| S02 | [Jev/Laya独立对比](https://www.reddit.com/r/LocalLLM/comments/1wmm8ql/jev_vs_laya_head_to_head_benchmark/) | 合成题集/版本/硬件与本任务不同，不能直接迁移准确率。 日期：2026-09-21（search/page indication, not API timestamp）。证据类型：COMMUNITY_EXPERIMENT_NOT_REPRODUCED。 |
| S03 | [Laya作者HN讨论](https://news.ycombinator.com/item?id=49765348) | 用户讨论措辞敏感和校准；早期销售模型泄漏争议须区分当前Laya。 日期：UNKNOWN（page relative date, exact timestamp not verified）。证据类型：AUTHOR_THREAD_WITH_OPPOSING_FEEDBACK。 |
| S04 | [laya.cpp作者发布](https://www.reddit.com/r/LocalLLaMA/comments/1wlmkm9/layacpp_optimized_laya_nearinstant_decision_making/) | C++/后端/速度线索，作者大显存GPU并非当前本机。 日期：2026-09-20（search/page indication, not API timestamp）。证据类型：AUTHOR_REPORT。 |
| S05 | [stuntd作者发布](https://www.reddit.com/r/LocalLLaMA/comments/1wnt7kv/stuntd_a_local_jevcompatible_server_on_laya_that/) | 作者承认使用规则/oracle等teacher，teacher一致率不等于真实领域正确。 日期：UNKNOWN（search date and relative page age disagree）。证据类型：AUTHOR_REPORT。 |
| S06 | [Nous self-evolution社区讨论](https://www.reddit.com/r/hermesagent/comments/1t5ifvg/nous_research_just_dropped_hermes_agent/) | Skill变长不是效果；旧讨论的提交数/阶段不能替代当前源码。 日期：2026-05-06（search/page indication, not API timestamp）。证据类型：COMMUNITY_REPORT_WITH_OPPOSING_FEEDBACK。 |
| S07 | [Curator Evolver作者发布](https://www.reddit.com/r/hermesagent/comments/1t7wzy6/i_built_a_localfirst_hermes_plugin_that_evolves/) | 候选/来源/rollback线索，回到README核对默认与bootstrap行为。 日期：UNKNOWN（exact publish timestamp not verified）。证据类型：AUTHOR_REPORT。 |
| S08 | [EvoSkill发布讨论](https://www.reddit.com/r/LLMDevs/comments/1sugu5z/evoskill_automatic_selfimprovement_tool_for_ai/) | 基于benchmark的自动Skill发现线索，回到Sentient第一方仓库核对。 日期：UNKNOWN（exact publish timestamp not verified）。证据类型：PROJECT_DISCUSSION。 |

## 如何处理互相冲突的说法

Laya作者标题与独立比较帖的强弱结论不同；其checkpoint、训练分布、题集、提示措辞和硬件没有保持一致。两边都保留为待复现线索，不能取有利数字。当前模型卡承认base zero-shot局限，且把专用微调分开，更支持“需要本域实测”而不是笼统全胜/全败。

HN包含早期销售模型输入泄漏的技术指控和链接，也包含品牌/先发争议。未在本轮复现那个历史模型，不将指控写成当前Laya checkpoint已证实泄漏，更不裁定Jev抄袭。和本任务有关的是：训练来源/独立holdout必须检查，结构相似不保证质量相同。

Nous讨论里“Skill行数增加”与“真正效果”有明显分歧；当前固定源码的Phase1与正文数据流问题单独列入[自进化分析](self-evolution-analysis-v1.md)。没有把社媒案例当内部数据库任务的性能证据。Curator Evolver和EvoSkill的能力也以其当前第一方说明为准，未宣称社区成功反馈等于我们的上线验收。

精确发布时间多数没有取得API时间戳；检索日期和页面relative age可能不一致，尤其stuntd。账本同时存储检索日期、展示日期依据和UNKNOWN，避免制造严格先后顺序。重复转载/同一作者跨平台发帖不算独立验证，讨论中的自报硬件/性能保留AUTHOR_REPORT或COMMUNITY_EXPERIMENT_NOT_REPRODUCED。

所有模型运行、对比复现、社区案例复现均NOT_RUN。来源SHA和第一方材料入口见[账本](research-sources-v1.json)，本地方案见[分类分析](local-classifier-analysis-v1.md)。
