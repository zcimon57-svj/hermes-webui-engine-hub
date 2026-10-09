# 内部本地分类/决策模型分析 v1

2026-10-09；状态：SOURCE_REVIEWED / DEPLOYMENT_NOT_RUN。最新要求：工单分类和空间选择在内部运行，不以外部Codex Luna作为生产依赖。Jev是商用对照；Laya及独立实现是本地候选。本轮只下载小型公开源码/模型卡与元数据，没有下载权重、安装依赖或调用模型。版本见[来源账本](research-sources-v1.json)，社媒正反证据见[原帖核查](social-evidence-v1.md)。

## 结论与候选顺序

建议先用 **Laya multilingual 与 GLiClass multilingual 两条 encoder 路线**比较中文/中英混合工单；另外保留 **Kev-0.8B**作不同架构对照，不能从Qwen底座直接推定其英语训练后的中文质量。英文场景可加入Decider-0.8B；有独立GPU预算时再比较Winnow/Clef。以上是研究建议，尚未定选，均没有在本环境部署或测出质量、内存、吞吐。

单纯换成ONNX/C++，只能改变运行方式。它不会自动修复基础模型的零样本泛化、校准、长文截断，也不会提供项目授权或同引擎实例选择。当前Hub默认规则路径、engine-ops默认空间和21条合成Luna题不能作为这些模型已接入的证据。

## 原项目、模型和运行器分别判断

| 项目 / 第一方入口 | 类型与本地条件 | 本任务的价值与限制 |
|---|---|---|
| [Jev / TypeSafe](https://docs.typesafe.ai/introduction) | 商用服务，公开typed decision接口；本轮未找到可直接下载的官方本地权重 | 对照choice/score/noul及置信输出；企业私有部署商务条件UNKNOWN，不能据此断言厂家绝无该产品，也不能默认把内部原文外发 |
| [Laya](https://github.com/NandhaKishorM/laya) / [multilingual权重](https://huggingface.co/convaiinnovations/laya-multilingual) | Apache-2.0；英语421M ModernBERT、多语322M mmBERT；单次前向typed head | 多语为首轮中文候选；默认1024上下文，可显式增到8192，长文质量需测；英语默认512。语言Router不是业务空间Router |
| [receptron/laya](https://github.com/receptron/laya) | MIT Node/ONNX运行封装，权重单独Apache-2.0；推理不需Python | Linux内部服务候选；本地modelDir、线程可控；转换前后概率、校准和多语支持必须逐个artifact核对，不自动把英语导出当多语 |
| [laya.cpp](https://github.com/lkarlslund/laya.cpp) | MIT C++/ggml，CPU及若干GPU后端、HTTP | 减少Python依赖；作者GPU速度与后端支持不是本机保证；量化、截断策略和原始输出一致性待验 |
| [layajev](https://github.com/metalagman/layajev) | MIT，本地CPU/显式准备artifact，Jev接口子集 | 离线artifact验证和部署边界有借鉴价值；须逐项核对实际支持的primitive，不能称完整替换 |
| [laya-mlx](https://github.com/mizorewww/laya-mlx) | Apache-2.0，Apple Silicon MLX独立实现 | Mac验证候选；当前Linux内部路线不优先 |
| [Ollaya](https://github.com/ollaya-dev/ollaya) | Apache-2.0多模型运行器，pull/serve；每个模型保留自身许可 | 便于统一实验接口；不是单一模型或质量提升方案。禁用自动下载、自动多模型常驻和外部fallback后才能做内网方案 |
| [GLiClass第一方](https://github.com/Knowledgator/GLiClass) / [gliclass-x-base](https://huggingface.co/knowledgator/gliclass-x-base) | Apache-2.0动态标签分类，多语mDeBERTa；还有edge/modern变体 | 重要对照：我们的首要需求是分类，不一定需要通用多题决策。x-base需实测中文；edge的英语速度不能直接替代中文多语结论。urchade旧仓是fork，当前主体为Knowledgator |
| [Kev](https://github.com/jaredpalmer/kev) / [0.8B权重](https://huggingface.co/jaredpalmer/kev-0.8b) | Apache-2.0，Qwen3.5底座+LoRA+pointer head，非生成式概率输出 | 有校准和训练/发布证据链，可作架构对照；adapter不是全部内存，还要底座、head、tokenizer；模型卡英语，中文NOT_RUN |
| [Decider-0.8B](https://huggingface.co/Mapika/decider-0.8b) | Apache-2.0，Qwen3.5-0.8B，typed decisions，作者标注English only | 英文对照；模型卡承认条件规则、知识题和分布外校准局限。不能只因底座多语就作为中文生产主选 |
| [Winnow-E4B](https://huggingface.co/EldanRing/Winnow-E4B) | 作者卡Apache-2.0，Gemma4派生，merged GGUF；Q8文件约8.01GB | 有GPU时的质量对照；E4B名称不代表文件只4GB，更不表示可塞进现有1GiB总预算；私有训练数据/流程未开放，榜单为作者报告 |
| [Clef-flash](https://huggingface.co/Cloudflare/clef-flash) | Cloudflare Apache-2.0开权重，9B多模态决策头，Jev接口 | 范围扩大后应纳入的强对照；官方单H200运行说明与自评不是内部部署/领域验收。本地权重与Workers AI托管的数据边界不同 |
| [stuntd](https://github.com/bladedevoff/stuntd) | Apache-2.0，Laya encoder+按站点小head，从流量/teacher学习 | 未来领域分类适配；teacher一致率不等于领域真值，默认外部teacher/fallback须禁用或替换；这属于分类器学习，不是Agent Skill进化 |
| [NanoJev](https://github.com/TianyuCodings/NanoJev) | MIT独立实验与训练路线；Jev式接口/决策结构 | 研究备选；不是官方Jev权重。还需训练、checkpoint和泛化证据，不能因为同名/兼容接口就当成熟产品 |

补充线索：独立OpenJev实现、Ollaya中的Von/Nimble/Decision/JevK5等。已记录为扩展线索，未逐个审查完整源码/权重，不把本轮研究范围说成穷尽生态。不同社区名称不是同一项目的Git fork：本轮多数衍生实现GitHub fork字段为false。

## 社媒热度背后的质量边界

作者发布帖强调速度与通用typed decisions；独立对比帖和HN用户提出提示措辞、截断、标签覆盖和校准敏感性。Laya当前模型卡也列出了基础zero-shot的局限，并区分typed-decisions专门微调结果。该checkpoint在相应训练分布上的提升，不能转写为内部数据库工单质量。作者早期销售模型的泄漏争议也不能未经复核套到当前Laya版本。

没有从不同GPU、不同checkpoint、不同题集的数字拼排行榜。模型输出的概率也必须用本域开发集重新校准；softmax总和为1不证明置信度可靠。

## Hub接入机制：建议，尚未实现

```mermaid
flowchart LR
  A[工单与可信实例标识] --> B[服务端授权候选集合]
  B --> C[规则优先与唯一实例绑定]
  C --> D[本地分类器 engine / space]
  D --> E[拒识与歧义追问]
  E --> F[再次授权校验与固定Run版本]
  F --> G[节点运行]
```

模型只能从服务端许可的engine/project/space候选中选择；不得获得未授权空间描述。明确实例优先于模型推断；同引擎多实例需要单独space判别及可信资产/实例上下文，不只返回engine名称。歧义、多引擎、未知实例、无匹配候选、无权限、低置信都必须有显式结果，不能一律回退engine-ops或越权空间。追问只能补业务选择，不能扩大权限。

建议接口固定返回model/artifact版本、候选集版本、engine_id、space_id或abstain、概率/分差、触发规则和延迟；服务端复核输出的ID属于本次候选。历史记录只存脱敏输入摘要和必要证据，不把全部私有工单写入训练池。

## 离线部署与资源门槛

现有本项目总预算保持1GiB RAM、swap0、192tasks、单核亲和性；宿主Linux与Windows余量不足即停止。FP32仅参数的下限估算：421M约1.68GB、322M约1.29GB，未计tokenizer/框架/activation。这是参数算术估计，不是文件精确大小或RSS实测。上述FP32路径不能被宣称满足当前总预算。

后续只允许一个checkpoint、一个推理进程、一个并发请求开始验收；限制ORT/PyTorch/BLAS线程、上下文、候选数及队列。ONNX INT8、FP16或小模型是否满足预算，需要artifact大小、加载峰值、实际任务峰值和质量差异的证据。不能先放宽预算，也不能通过swap“容纳”模型。预算不满足时保留拒绝启动结果，选择小模型或另有预算的内部分类服务。

离线包必须锁定代码SHA、权重与底座SHA、head/calibration/tokenizer/config文件SHA256、许可证/NOTICE、wheel或binary及平台/运行库版本。预备环境准备后用本地路径运行，禁网、禁首次自动下载、禁外部fallback。先校验artifact再加载；转换artifact需重新登记hash与精度，不沿用原权重hash。

## 验收数据与通过条件

| 维度 | 必须保留的场景/证据 |
|---|---|
| 领域质量 | 四引擎、同引擎多实例、中文/混合语、缩写/别名、否定句、追问、多主题、未知/无权限；专家真值，不用模型自标作为唯一答案 |
| 泛化与泄漏 | train/calibration/test按Issue与时间隔离，同Issue追问不可跨split；最终holdout不反复选参 |
| 质量指标 | engine/space分别报macro-F1、混淆、拒识覆盖率与误路由；高置信错误、校准/Brier或ECE；不以格式合法率代替分类正确率 |
| 稳定性 | 候选顺序、标签描述改写、无正确答案/正确答案存在的成对拒识、长文关键证据在首尾、并发与版本变更 |
| 部署 | 全禁网运行；参数/权重/校准校验；冷加载与热请求峰值、p50/p95、线程/任务数、OOM/超时/断服务降级 |
| 权限 | 候选与响应服务端校验、跨项目/跨引擎拒绝、错误密钥；分类失败不授权执行 |

阈值由业务与领域责任人确认；目前没有可证明达到这些标准的本地结果。F11真实标注/专家阈值依赖外部输入；适配器、离线校验、负例集与预算控制由Core维护者推进。I01脚本凭据隔离与I02同时双节点仍优先，不能用新模型研究替代隔离验收。
