# 验收矩阵与历史证据的适用范围

[评审入口](README.md) · [审查发现](review-findings.md) · [总账 #2](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/2) · [原始 F01–F32 记录](../../acceptance-local-r1.json)

本页是 **2026-10-09 评审解释与待补验收**，不修改原始结果。原记录有 29 个 PASS、3 个 NOT_RUN，PASS 必须连同时间、版本、输入和 scope 阅读；不是 29/32 的目标完成率。本轮只做文档/源码/官方资料核对，没有增加任何功能或领域 PASS。

<a id="evidence-levels"></a>

## 1. 四类证据必须分开

| 层次 | 能证明什么 | 不能证明什么 |
|---|---|---|
| 固定源码/文档检查 | 代码分支、接口、职责与设计缺口 | 真实部署成功、未覆盖输入安全、业务效果 |
| 历史本地功能证据 | 指定版本/场景/资源下的真实HTTP、Gateway、身份或包消费 | 另一版本、更多并发、跨机HA、完整权限 |
| 真实模型与领域评估 | 对指定模型、标签/真值、数据划分及阈值的结果 | 所有领域、同名其他权重/运行器、未跑本地模型 |
| 目标/生产部署验收 | 完整场景、真实权限与故障、内部接口和交付 | 不能由文档合并或模拟器自动获得 |

[历史证据索引](../../evidence/INDEX.md)保留所有失败和额外尝试。旧 1 GiB 限额的 F03，与后续 [3 GiB 空组配置读回](../../reviews/2026-10-09-reassessment/resource-budget-v3-applied.json)分别标记；任何一者都不证明本机双节点加本地分类/学习负载已验。

## 2. F01–F32 逐项解释

“原记录”逐字保留 PASS/NOT_RUN；“当前解读”与“待补”是本轮审查，不是动态重跑结果。原证据列给出代表性直接入口，完整多次尝试见原始 JSON。

| 编号 / 目标 | 验收对象 | 原记录 | 当前解读 | 待补或重新验收 | 代表性原证据 |
|---|---|---|---|---|---|
| F01 / R01 | 统一入口 | PASS | 旧三角色/页面整链；不代表完整原WebUI继承 | R01/R04：所有显示面按完整scope过滤 | [证据1](../../evidence/guarded-hub-20261008T170041.json) · [证据2](../../evidence/browser-guarded-2026-10-08T17-06-57-896Z.json) |
| F02 / R01 | 六节点路由 | PASS | 六节点分别运行的证据；不是同时六节点容量 | R01/R05：同引擎与跨引擎两组同时运行证据 | [证据1](../../evidence/guarded-hub-20261008T170041.json) |
| F03 / R01 | 状态与资源边界 | PASS | 历史1GiB包络和普通API路径；脚本权限仍有缺口 | R01/E03：脚本管理身份隔离、当前3GiB负载验证 | [证据1](../../evidence/guarded-hub-20261008T170041.json) · [证据2](../../evidence/resource-controls-1791480527113427669.json) |
| F04 / R02 | 可信规则路由 | PASS | 登记实例/规则已有 | R02：目录版本、同引擎不同实例冲突和授权空间 | [证据1](../../evidence/live-20261008T153103.json) |
| F05 / R02 | 分析与歧义 | PASS | 规则/可选Luna；未接内部本地模型 | R02：本地候选约束、拒识、未知与越权负例 | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/luna-guarded-1791480044434422462.json) |
| F06 / R02 | 真实分类质量 | PASS | Luna 21条合成题；不等于本地或真实领域质量 | R02/E02：真实标签、校准/holdout、误路由与容量 | [证据1](../../evidence/luna-guarded-1791480044434422462.json) · [证据2](../../evidence/luna-routing-20261008T152931.json) |
| F07 / R02 | 追问连续性 | PASS | 旧空间/显式切引擎检查；未覆盖同引擎换实例 | R02：新增instance与旧conversation绑定冲突；同Home Memory按scope隔离 | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/guarded-hub-20261008T170041.json) |
| F08 / R03 | 私有学习草稿 | PASS | 普通节点/会话草稿隔离；任意代码强隔离未验 | R01/R03：前后台所有写入口pending且不进入业务消费 | [证据1](../../evidence/guarded-hub-20261008T170041.json) · [证据2](../../evidence/governance-recovery-20261008T153325.json) |
| F09 / R03 | 候选治理链 | PASS | 人工候选和评测标记；不是自动候选加真实评测 | R03：原生候选、确认RCA、实际评测及独立人审 | [证据1](../../evidence/governance-recovery-20261008T153325.json) · [证据2](../../evidence/final-edges-1791481451416686618.json) |
| F10 / R03 | 同引擎批准共享 | PASS | 固定包由同引擎节点分别消费 | R03/R05/R06：同时节点实际加载相同批准hash且私有状态不共享 | [证据1](../../evidence/guarded-hub-20261008T170041.json) · [证据2](../../evidence/governance-recovery-20261008T153325.json) |
| F11 / R03 | 学习领域质量 | NOT_RUN | 未取得独立RCA真值、专家阈值与真实回放验收 | R03/E02：领域确认人提供输入，真实收益/反例独立报告 | 原记录无实测证据 |
| F12 / R03 | 并发发布和撤回 | PASS | 本地指针CAS治理；不构成远端分布式原子性 | R03/R06：远端部分成功/超时、对账、候选不可见、撤回传播 | [证据1](../../evidence/governance-recovery-20261008T153325.json) · [证据2](../../evidence/final-edges-1791481451416686618.json) |
| F13 / R04 | 独立身份 | PASS | 独立测试账号与会话已有 | R04：现有用户修改/撤权、委派子集与事件连接 | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/guarded-hub-20261008T170041.json) |
| F14 / R04 | Admin能力 | PASS | 基础配置操作；管理范围/私有正文访问仍需区分 | R04：配置、用户、节点、发布额外capability矩阵 | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/browser-guarded-2026-10-08T17-06-57-896Z.json) |
| F15 / R04 | Viewer能力 | PASS | 基础写接口拒绝；GET下游可能触发派发 | R04/R05：全部读路径不执行恢复写入/脚本 | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/guarded-hub-20261008T170041.json) |
| F16 / R04 | Chat能力 | PASS | 提问、追问、取消自己的运行的限定场景 | R04：owner/共享/撤权/重连/在途Run负例 | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/guarded-hub-20261008T170041.json) |
| F17 / R04 | 汇总和范围 | PASS | 部分engine/space拒绝；管理与资产服务覆盖不完整 | R04/R06：列表/详情/下载/管理/API/MCP同一scope | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/guarded-hub-20261008T170041.json) |
| F18 / R04 | 多用户并发 | PASS | 历史三浏览器上下文范围 | R04：并发撤权与执行点重验，结果不扩权 | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/browser-guarded-2026-10-08T17-06-57-896Z.json) |
| F19 / R05 | 同引擎多节点 | PASS | 原记录明确最终受限宿主单热轮换；同时容量未验 | R05/E03：当前版本真实同时双节点及预算峰值 | [证据1](../../evidence/governance-recovery-20261008T153325.json) |
| F20 / R05 | 节点池与断线 | PASS | 本地/旧范围池与断线检查 | R05：单节点故障、取消、晚到结果、产物恢复 | [证据1](../../evidence/governance-recovery-20261008T153325.json) |
| F21 / R05 | 第二物理主机 | NOT_RUN | 跨物理主机仍未运行 | R05：授权主机、注册/租约/代际/网络/产物实证 | 原记录无实测证据 |
| F22 / R06 | 远端知识读取 | PASS | 实际WeKnora固定知识读取 | R06：问题驱动检索、批准集合过滤和内容引用 | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/guarded-hub-20261008T170041.json) |
| F23 / R06 | 远端更新 | PASS | 远端写和读回路径 | R06：索引ready、权限变化、部分失败与重启 | [证据1](../../evidence/governance-recovery-20261008T153325.json) · [证据2](../../evidence/final-edges-1791481451416686618.json) |
| F24 / R06 | 远端Skill包 | PASS | 固定SKILL.md/probe/reference包和声明依赖检查 | R06：通用原生发现/选择/加载/执行及同名覆盖 | [证据1](../../evidence/guarded-hub-20261008T170041.json) · [证据2](../../evidence/luna-hermes-retry-run.json) |
| F25 / R06 | 资产版本权威 | PASS | 联合release/base/摘要及远端修订已有 | R06：发布意图、唯一协调器、跨服务异常恢复 | [证据1](../../evidence/governance-recovery-20261008T153325.json) · [证据2](../../evidence/final-edges-1791481451416686618.json) |
| F26 / R06 | 缓存资格 | PASS | 固定包每次读回/摘要/撤回检查 | R04/R06：真实只读执行边界、scope、替换竞态与撤权 | [证据1](../../evidence/guarded-hub-20261008T170041.json) · [证据2](../../evidence/governance-recovery-20261008T153325.json) |
| F27 / R06 | 远端管理读回 | PASS | 固定Memory和node-evidence文件路径 | R01/R04/R06：受限通用工作区/状态管理及管理权限 | [证据1](../../evidence/live-20261008T153103.json) |
| F28 / R01 | Run生命周期 | PASS | 本地真实Gateway限定流程 | R01/R05：纯读语义、在途取消、未知结果与真实故障 | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/guarded-hub-20261008T170041.json) |
| F29 / R01 | Manager适配合同 | PASS | ReferenceManager本地合同替身 | R05：内部适配字段/版本/恢复合同需单独验收 | [证据1](../../evidence/live-20261008T153103.json) · [证据2](../../evidence/guarded-hub-20261008T170041.json) |
| F30 / R01 | 内部Manager对齐 | NOT_RUN | 内部真实版本/身份/业务接口未接入 | R01/R05：内部维护者提供环境后验证取消/恢复/投递 | 原记录无实测证据 |
| F31 / R01 | 恢复与数据保留 | PASS | 旧限定失败/回执保留证据 | R05/R06：读与写恢复拆开、远端未知和产物完整性 | [证据1](../../evidence/guarded-hub-20261008T170041.json) · [证据2](../../evidence/governance-recovery-20261008T153325.json) |
| F32 / R01 | 派生仓交付 | PASS | 旧私人交付历史；2026-10-09用户已授权公开 | E01：保留历史/许可证/代码和失败记录，原PR持续评审 | [证据1](../../evidence/private-delivery-r1.json) |

## 3. 新目标验收的阅读入口

六份设计各自提供 Given/When/Then 场景及局部编号，说明前提、动作、预期结果、需要保存的观察；它们与 F 编号是补充映射，不覆盖历史状态。

| 目标 | 详细场景入口 | 必需组合 |
|---|---|---|
| R01 | [隔离与统一入口](r01-isolation-and-ui.md) | 同引擎/跨引擎、正常/恶意脚本、管理/消费身份、纯读取 |
| R02 | [本地分类与路由](r02-local-routing.md) | 显式实例/无实例、追问冲突、无权/未知/歧义、真实领域/离线容量 |
| R03 | [原生学习](r03-native-evolution.md) | 前台/后台/approve、RCA缺失/纠正、真实评测/反例、人审/基线变化 |
| R04 | [角色与范围](r04-access-control.md) | 三角色×动作×scope×owner/共享×撤权/在途状态 |
| R05 | [节点和产物](r05-multi-node-and-artifacts.md) | 同时两个节点、故障/取消/晚到、worker≠target、跨机另验 |
| R06 | [资产与Skill](r06-assets-and-local-skills.md) | 部分发布/未知应答/重启、草稿隔离、通用加载、同名覆盖、索引/撤回 |

## 4. 缺输入与可推进工作

| 项目 | 目前缺少的具体内容 | 谁提供 / 通过条件 | 输入到位前仍可做的工作 |
|---|---|---|---|
| F11 领域真值 | 最终RCA只为用户报告；接口、确认状态、事件映射、评测集/阈值未读取 | 领域/业务确认人；可追溯真值与独立holdout、人审规则 | 写入口与回执合同、静态负例、数据隔离与评测执行器实现 |
| F21 第二物理主机 | 授权主机、网络、版本、身份与预算 | 运行维护者；两host真实断线/权限/代际/产物验证 | 本机同时双节点、注册/代际/产物接口设计 |
| F30 内部整链 | 实际Manager/身份/MCP/RCA版本、接口和投递回执 | 内部接口维护者；受理、取消、恢复、权限和交付实证 | 保留明确标记的ReferenceManager合同验证 |
| R02 本地定型 | 确切模型/权重/运行器、领域标签及资源峰值 | Core/领域/运行；同题质量与禁网容量记录 | 规则、澄清、授权候选、artifact校验和适配接口 |
| I01/I02/I04/I06 | 实现与本机验证尚未完成 | 对应实现角色；真实边界与负例 | 这些不能笼统归因于“没有内部环境” |

## 5. 本轮文档验证口径

本轮检查 Markdown 结构、相对链接/锚点、GitHub 文档与源码目标、Mermaid 图源结构、JSON 和 Issue/PR 交叉关联，并核对提交仅包含评审资料。详见 [本轮检查记录](../../evidence/review-readiness-checks-20261009.json)。检索来源成功读取是资料证据；没有执行的服务、CI、领域/并发/内部测试明确记为 NOT_RUN。
