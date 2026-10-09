# R06 远端知识/Skill、批准版本与本地消费

目标与进度：[Issue #8](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/8)；[总账 #2](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/2)。

状态：**待独立架构评审，未实施/未验收**。用户已确认的原则单独列出；详细接口、状态和验收边界由本PR评审。本轮不改运行代码、不引入外部进化/评测项目、不自动合并本PR。

## 用户已确认的共享方式

正式知识/Skill通过受控MCP/HTTP取得，各节点本地批准副本读取/执行；不共享可写Home、私有Memory、会话或凭据。节点不直接读对方目录，MCP不是存储权威。

## 当前代码与缺口

实际链：Hermes stdio MCP → 节点Companion HTTP →批准资产服务/WeKnora HTTP。Skill按hash落approved-cache，返回方法/引用与固定probe脚本结果；知识读固定发布文档。原生通用skills目录加载、问题驱动检索、通用工作区/依赖仍部分完成。

## 拟议内容与版本模型

WeKnora存正式内容；薄协调层持唯一current release指针及CAS/撤回/回退。文档native revision、联合release、包/配置hash分别记录。Run固定release/hash，不在会话途中静默换版。

包声明SKILL.md、scripts/references/templates等支持文件、可执行入口、依赖/平台锁、来源/engine/scope、manifest与hash。路径/引用/依赖检查后才准备受管加载目录；缺依赖或版本不合拒绝，不在业务Run自动安装/升级。

发布与消费顺序：候选完整包→RCA/实际评测→周期人审批准确切hash和base→CAS更新并读回→新Run取得授权版本→节点校验并形成只读快照→原生受管加载/MCP检索。元数据、文件和检索都必须排除未批准候选。

## 本地目录与安全

业务原生写先pending，不先改活跃Skill/Memory。批准目录采用实际只读挂载与独立发布身份；仅chmod或“approved”命名不是完整写保护。同名私有候选不得覆盖批准Skill；缓存始终重新检查远端scope/撤回/摘要，不能成为离线扩权来源。

RCA纠正、远端内容漂移、撤回、身份失效导致新消费拒绝并留下审计。回退更新发布指针，历史包/结果保留；在途Run依明确撤回/取消合同处理，不假装已执行动作可被回滚。

## 必须验收

完整方法/脚本/引用/依赖真实加载；问题驱动知识检索；两个同引擎节点消费相同批准版本；私有候选/跨engine/project访问拒绝；缓存损坏、远端漂移/撤回、并发CAS、审批后变更、回退和正在运行版本稳定。

## 评审问题

原生Skill外部目录/加载适配的优先级与覆盖如何限制？知识与Skill包如何统一发布而保持独立内容修订？依赖预置、长期缓存和撤回时效阈值是什么？目前验证包适配不是已经通用兼容。

责任模块：知识平台、Core、MCP、Manager与领域评审；I03/I06/F11/F30均保留。详见[当前RemoteSkillProvider](../../companion.py)及[发布层](../../assets.py)。
