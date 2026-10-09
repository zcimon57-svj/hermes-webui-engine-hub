# 六个功能目标、三个执行要求：严格审查 v2

2026-10-09。审查代码 `74437cb77829c7b301cdab8d92722315e4ebbab4`。**整体目标未完成；撤回“本地功能全部完成”的过宽表述。原29 PASS是有范围的历史检查，不是目标完成率。**

当前入口服务已因Windows余量保护停止；本轮不重启、不部署模型、不跑重型验证。

## 用户确认：原生自进化简单改造设计

状态：**路线已确认、设计已记录；代码改造与业务验收待完成**。采用Hermes原生反思/Memory/Skill能力，接已有工单、告警、war room最终RCA与Manager/WeKnora。不引入独立自进化或评测项目；此前项目仅作参考。此决定针对R03/R06自进化，不改变R02本地分类模型要求。

**流程：原生私有候选 → 等待确认RCA → 静态与领域评测 → 定期领域人审 → CAS发布 → 同引擎新Run消费。**

| 最小改造点 | 设计 |
|---|---|
| 业务结果关联 | 用同一incident关联工单/告警/war room、Run和报告，保存经责任人确认的RCA版本/时间/证据；未确认或冲突RCA不进入参考答案集 |
| 原生候选写入 | 前台/后台反思的业务Memory/Skill改动先进入私有pending；候选不进入正式检索或Skill发现。统一受管写口及approve路径，正式资产只读、发布身份独立 |
| 轻量内部评测 | 在已有执行链中检查包/引用/权限、根因与因果链/适用条件、旧新版本正反例。答案仅给评测器；按事件/时间分离开发与验收样本。缺工具快照只能报告文本评测，不能标完整回放通过 |
| 周期人审合入 | 领域维护者审核diff、RCA依据、正反例结果、前提/例外与风险；绑定候选hash、基线和评测版本后批准。评审周期待团队确定，合入前必须批准；生成者不能自批 |
| 发布与纠正 | 复用已有CAS、读回、版本固定、撤回/回退；批准成果仅同引擎共享，私有草稿不共享。RCA纠正时失效关联评测，相关资产待复核并暂停新Run使用，保留旧版本证据 |

最小候选记录：incident/Run/报告关联、engine/project/instance、RCA版本、旧版本与候选hash、拟改内容和前提/例外、评测结果、审核人/决定、发布版本。状态使用`WAIT_RCA → WAIT_EVAL → WAIT_REVIEW → APPROVED → PUBLISHED`，失败/拒绝停在未发布状态；审批后内容或基线变化重新评测/审核。生效以发布读回为准。

实现次序：先修I01脚本/管理凭据隔离；Core接原生pending与统一写口；业务接入/MCP维护者关联确认RCA；Core/领域维护者补实际评测，替代客户端`passed=true`；Manager/知识维护者接人审与现有发布链。继续遵守3GiB总硬上限、2.5GiB高水位和宿主准入，任务串行受限；本轮仅记录设计。

通过条件：格式合法但业务结论错误的候选被拒绝；无RCA/评测失败/无人批准不生效；回放不泄漏最终答案；根因正确但动作越权也拒绝；审批hash变化/CAS冲突拒绝旧审批；RCA纠正可追溯撤回；同引擎两节点消费一致获批hash、跨引擎与私有候选拒绝共享。这些均为待验证条件，不能代替I02真实双节点验收。

责任：Core负责候选/隔离/评测接入；业务接入与MCP负责RCA关联；领域维护者负责真值、反例和人审；Manager负责审批状态/身份；知识维护者负责正式版本/消费/回退。实际RCA接口、关联字段与确认状态尚未核查，F11/F30继续保留。

| 目标 | 当前判定 | 已做到 | 未做到 / 原因 |
|---|---|---|---|
| R01 多引擎/节点隔离与统一入口/UI | PARTIAL_ISOLATION_NOT_ACCEPTED | 统一目录/会话/Run/报告；节点级Home/工作区/凭据；六节点各自运行过、错误密钥和路径检查 | 现版本两节点同时运行的隔离/并发/故障实测；Skill脚本与管理控制目录的权限分离。事故后单热节点策略和串行验证缩小了范围；脚本继承伴随服务权限。不是缺外部主机。 |
| R02 授权范围内按规则与本地分析模型自动选择空间 | PARTIAL_LOCAL_CLASSIFIER_NOT_IMPLEMENTED | 实例绑定/关键词规则/歧义澄清/追问绑定；历史Luna 21条合成分类题 | 内部可离线部署的分类模型接入；同引擎多实例/项目空间自动辨别；本域标注集、拒识与置信校准。目前模型可选Codex Luna，默认规则/fixture；分析通常返回engine-ops。最新用户明确改为Jev/Laya类本地分类模型。 |
| R03 独立自进化候选与批准成果同引擎共享 | PARTIAL_GOVERNANCE_ONLY | 私有草稿/远端候选；人工审核、CAS发布/撤回/回退；批准资产在同引擎节点分别消费 | 自动反馈采集与候选生成产品链；实际评测执行器；Hermes原生候选→确认RCA评测→周期人审的受控接入（路线/设计已确认，待实现）；真实领域效果验收。UI人工填候选、评测标记布尔值；Luna候选为独立脚本。当前lab关闭原生memory写能力且工具集限定mcp-ops。 |
| R04 Admin/Viewer/Chat三类用户权限 | BASIC_ROLES_VERIFIED_MANAGEMENT_PARTIAL | 独立身份和服务端拒绝；三浏览器上下文；私有会话共享、部分engine/space限制 | 配置/现有用户角色与作用域完整管理；项目范围贯穿配置和管理列表；执行脚本的权限边界闭合。配置PATCH仅node/enabled；用户管理主要列表和新建，配置实例列表只按engine过滤。 |
| R05 同引擎多节点/多进程部署 | SIMULTANEOUS_TWO_NODE_PENDING | 六个节点定义、独立运行状态；同引擎两个节点分别消费批准资产；启动器最多允许两个节点 | 至少两节点同时部署和并发任务；跨引擎隔离与同引擎共享/私有状态两组实测；一节点离线另一节点继续工作现版本实测。supervisor自动路径保留一个热Gateway，忙碌时拒绝唤醒其它节点；当前证据主要串行。 |
| R06 远端WeKnora知识/Skill消费、更新、版本与本地缓存 | VERSION_CHAIN_VERIFIED_GENERIC_ADAPTER_PARTIAL | 真实远端内容读写/发布读回/下一Run消费；固定release/native revision、CAS/回退/撤回；验证包的方法/脚本/引用/依赖检查 | 通用Skill选择/加载/运行；问题驱动检索与普通问答链完整集成；通用远端工作区管理；第三方依赖完整验证。固定scripts/probe.py与method引用路径，现有依赖校验；workspace仅node-evidence.txt；运行读取固定发布文档。 |

| 执行要求 | 判定与事实 |
|---|---|
| E01 私人可维护派生仓 | DONE_VERIFIED。历史PRIVATE与74437cb7交付保留；完整9565基线历史/许可证/upstream。最新用户授权PUBLIC，GitHub已核对公开；本轮PR与main SHA另核对。 |
| E02 真实模型测试与内部可用本地分类模型 | PAST_LUNA_TEST_DONE_LOCAL_PRODUCTION_CLASSIFIER_PENDING。历史Luna分类/候选/真实Hermes工具链实测保留；最新要求生产分类改为本地Jev/Laya类，分析中，尚未部署/接入。 |
| E03 严禁资源打满 | INITIAL_FAILURE_REMEDIATED_PROTECTION_VERIFIED。发生过内存与swap满；补救后shared1GiB/192tasks/0swap、单模型、CPU亲和性与监控；02:19Windows剩约368MiB触发停止。最新用户授权总硬上限3GiB/高水位2.5GiB、Windows/Linux各保留2GiB，空cgroup已核对；资源13项通过，模型与双节点峰值NOT_RUN。当前服务停止；CPU配额未委派。 |

## 优先残余、责任和通过条件

- **I01 / BLOCKER / 脚本继承含state_admin_key的/control/config.json可见环境**：STATIC_CODE_GAP_CONFIRMED_ATTACK_NOT_RUN；责任：Agent Core/UI执行维护者；下一步/通过条件：单独脚本执行沙箱/最小消费身份，不挂管理控制目录；实际验证不可读取凭据、不可改节点状态。
- **I02 / P0 / 同时双节点与隔离未闭合**：PENDING_IMPLEMENTATION_AND_LIVE_VALIDATION；责任：Manager/Core/验证执行者；下一步/通过条件：维持资源上限；分别测跨引擎两节点和同引擎两节点，写入自己的状态并尝试另一节点读取/写入、并发、错误凭据和单节点失效。
- **I03 / P0 / 自动学习采集、生成与评测执行器未实现**：PENDING_IMPLEMENTATION；责任：Core/知识维护者；下一步/通过条件：按本页已确认的原生简单设计接入确认RCA、实际评测和周期人审；仅私有候选，批准后CAS发布；外部项目仅参考，不作为实施依赖。
- **I04 / P0 / 项目授权与配置管理覆盖不足**：PENDING_IMPLEMENTATION_AND_REVIEW；责任：身份/UI维护者；下一步/通过条件：覆盖实例/配置/用户管理列表、读写和脚本身份，补负例。
- **I05 / P1 / 本地分类与多空间选择**：ANALYSIS_ONLY；责任：Core/路由维护者；下一步/通过条件：Jev/Laya原作者资料核对；锁定本地权重、依赖、scope候选和拒识门槛，本域数据验收。
- **I06 / P1 / 通用Skill/检索/状态适配**：PENDING_IMPLEMENTATION；责任：知识/Core维护者；下一步/通过条件：移除验证包固定路径假设，设计可声明入口、引用/依赖锁、问题检索与固定Run版本。
- **I07 / P0 / 旧完成结论与现场状态过宽/过时**：CORRECTED_IN_REASSESSMENT；责任：本轮资料执行者；下一步/通过条件：新审查文件为当前判断；旧29PASS仅原范围证据，不改原结果文件。

## 隔离缺口的源码定位

伴随服务的[控制目录挂载](../../scripts/lab.py#L114)和[控制配置写入](../../scripts/lab.py#L138)含节点管理身份；[Skill脚本执行](../../companion.py#L94)直接继承该服务的身份与挂载。此为静态可见性/权限边界缺口，未做越权攻击实测，不能由“消费API禁止写入”用例代替。

单热节点策略见[supervisor.py](../../supervisor.py#L40)；空间默认engine-ops见[routing.py](../../routing.py#L44)；人工评测布尔标记见[assets.py](../../assets.py#L124)；配置仅node/enabled见[server.py](../../server.py#L270)。

F11领域质量、F21第二物理主机、F30内部接入是真正的外部输入；同时双节点、本机隔离、自动学习链、通用Skill和管理面缺口属于应继续实现/验证的工作，不能归因于这些环境项。

本轮最新指令：生产分类优先研究本地可部署的Jev/Laya类模型，Luna历史实测保留；自进化研究Hermes原生能力及独立GitHub项目；当前仅分析，不把候选定选或文档检查当部署通过。

机器可读明细：[goals-progress-v2.json](goals-progress-v2.json)。两条技术路线的分析见本目录后续分析文件。

本轮分析已完成：[本地分类](local-classifier-analysis-v1.md)、[独立自进化](self-evolution-analysis-v1.md)、[社媒原帖](social-evidence-v1.md)、[来源账本](research-sources-v1.json)。没有模型部署/产品代码变更，R02/R03与整体PARTIAL判定不变。

最新业务信息：用户报告工单/告警/war room流程已有最终根因。F11已有潜在参考答案来源，实际数据与确认状态仍未读；[原生RCA门禁建议](rca-gated-native-evolution-v2.md)与[合同v2](evolution-quality-contract-v2.json)接入该来源。尚无领域效果或新管线验收，不提高完成率。

## 当前实现归属核对

[多引擎隔离/多节点源码归属分析](isolation-implementation-analysis-v1.md)与[SHA/差异证据](isolation-implementation-provenance-v1.json)：当前UI、权限、路由、节点池和部署封装主要是新增Engine Hub；直接复用原WebUI样式，执行复用Hermes Gateway，资产复用WeKnora。原WebUI server/api/static/index相对固定基线未改，原Profile后端未接入Hub。不能描述为原WebUI现成多引擎集群能力；完整原UI功能未继承。同时双节点与脚本权限缺口保留，不提高R01/R05完成状态。

## 同引擎跨VM/容器的路由与产物讨论

[多资源分析](multi-resource-routing-artifacts-v1.md)：由现有Manager负责授权引擎/目标→节点池与能力路由；独立工单各选一worker，必要时一个parent Run拆有限task。产物按业务Run/task/attempt登记到集中索引与已有存储；最终报告单一交付，正式知识/Skill仍经RCA评测人审发布到WeKnora，私有Home/Memory/凭据不共享。跨主机注册/租约、迁移、子任务汇聚、通用产物manifest和分布式调用预算尚未实现/验收，当前仅讨论建议，不新增实施承诺，不提高R05/R06完成状态。

目录与共享澄清见[多资源分析末节](multi-resource-routing-artifacts-v1.md)：当前是本地MCP/HTTP读取批准资产、各节点缓存，没有共享可写Home；通用原生Skill加载与受控原生学习链仍未实现。私有学习必须在活跃目录生效前入pending，经RCA/评测/周期人审后发布。

## 后续工作基线与公开交付

用户已确认接口分发＋各节点本地批准副本、不共享可写Home的方式；与原生RCA门禁/周期人审一起构成实施基线。[五模块架构总览](../../architecture/README.md)及各部分职责已整理。用户本轮明确授权公开此派生仓并通过PR合并；旧PRIVATE约束按历史解释，母仓保持原可见性。本轮设计/文档交付不会把R01–R06未实现/未验收项改成完成。
