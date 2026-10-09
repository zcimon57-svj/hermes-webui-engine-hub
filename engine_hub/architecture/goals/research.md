# 官方调研依据、版本差异与项目适用范围

[评审入口](README.md) · [审查发现](review-findings.md) · [总图](overview.md) · [R02](r02-local-routing.md) · [R03](r03-native-evolution.md) · [R06](r06-assets-and-local-skills.md)

核查日期：**2026-10-09**。本次使用官方源码、官方协议/内核文档和本仓库固定代码；没有下载模型权重或启动运行实例。下面明确区分外部事实与本项目设计判断。已有更广的候选研究见[历史来源账本](../../reviews/2026-10-09-reassessment/research-sources-v1.json)，这些历史研究不自动成为型号选择或实现验收。

## 1. 版本对照

| 对象 | 固定身份或规范日期 | 本轮可确认的内容 | 仍不能推出的结论 |
|---|---|---|---|
| Engine Hub | 主线 `6e6c4e897c62078ff1f14f072abe3fd7d7c461b3`；PR 原头 `faf6321077067da1585fb40a71c0d420bab5ee01` | 实现调用路径、文档与旧证据的对应关系 | 本轮未重新运行功能/负载/内部接口 |
| Hermes Agent | `345cd2b057a452236de401d3534b8502a7465e8d`，项目 health 记录 0.21.3 | 下文原生 Profile、Memory、Skill、hook 和审批源码 | 上游今天新增的其他能力不能算入固定部署 |
| WebUI 上游 | `4a0639397d1d4eb14965d9e88f39aecffa9ef345` | 派生仓来源、当前保留的上游代码 | 不能认为保留文件就表示新 Hub 继承了全部 UI/API |
| WeKnora 运行镜像 | source 标签 `d97ad7a4`；image ID `sha256:687374a4d457b15e2afc0d1f61935ae41e11becadcd26d76aba1a1f903fe47c1` | [版本锁](../../versions.lock.json)与历史实例证据中的身份 | 本轮官方仓库不能解析这个短 ref，不据此推断私有源码或镜像不存在 |
| WeKnora 邻近源码 | `1edcd54b43606d9079bb36650efe3f68707a79ea`，锁文件明确写 `adjacent_source_not_runtime` | 下文该版本接口和异步索引行为 | 不证明运行镜像完全相同行为，需兼容测试 |
| MCP | 当前实验默认 `2025-03-26`；另参考 `2025-06-18` HTTP 授权 | 协议协商、stdio 与 HTTP 认证边界 | 不把新规范要求当当前 stdio 已实现 OAuth |
| Linux 资源机制 | 官方 Linux 6.12 cgroup v2 文档 | high/max、CPU 时间限额、cpuset 的语义 | 不证明用户宿主现况、双节点容量或模型峰值 |

原始组件与镜像细节以[versions.lock.json](../../versions.lock.json)为准；旧 source hash 和之后的资源修改分别解释，不用本轮文档提交覆盖旧运行身份。

<a id="sources-hermes-profile"></a>

## 2. Hermes Profile、Home 与凭据

**官方事实。** 固定版本的 [Profiles 文档](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/website/docs/user-guide/profiles.md#L185-L203)将状态目录、工作目录和沙箱区分；默认 local 终端仍拥有启动用户的文件访问权限。独立 Home 避免 Memory 等状态互相混用，但不自动限制可读宿主路径。[OAuth 说明](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/website/docs/user-guide/profiles.md#L65-L68)还描述某些 Profile 回读根 Home 的登录凭据。

**本项目判断。** R01/R04 需要证明实际执行身份、挂载、环境、继承文件描述符和服务密钥边界，不能用不同 Profile 名称替代。每节点批准资产可以分发相同内容；可写 Home、会话、凭据和草稿仍应私有。这是设计推导，本轮未执行逃逸或攻击实验。

**Memory 采用时机。** [固定版本 Memory 文档](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/website/docs/user-guide/features/memory.md#L38-L57)区分持久文件更新和会话开始形成的提示快照。本项目还需明确 Run、会话与 release 的采用边界；不能笼统声称“写入后所有在途会话立即更新”。

<a id="sources-hermes-learning"></a>

## 3. 原生学习与批准能力：可复用的接缝及限制

| 固定版本事实 | 官方源码 | 对本项目的影响 |
|---|---|---|
| Memory/Skill 有 write approval 与 pending；配置缺失或读取异常会关闭 gate | [write_approval.py 43–59](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/tools/write_approval.py#L43-L59)、[pending 路径](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/tools/write_approval.py#L64-L68) | 可复用候选结构；需要启动校验及运行期失败关闭 |
| Memory 和 Skill 的 gate 导入异常存在放行分支 | [Memory](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/tools/memory_tool.py#L64-L77)、[Skill](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/tools/skill_manager_tool.py#L581-L597) | 不能由正常 pending 演示证明全部写入受管 |
| 原生 approve/apply 重放直接写原生状态，未含 Hub 的 RCA、评测/基线与联合发布绑定 | [Memory apply](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/tools/memory_tool.py#L249-L259)、[Skill apply](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/tools/skill_manager_tool.py#L625-L631)、[CLI 批准](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/hermes_cli/write_approval_commands.py#L77-L104) | 正式批准路径必须封闭旁路并绑定精确内容与权限 |
| `pre_tool_call` 可阻断/批准/修改；`post_tool_call` 是事后观察 | [hooks 控制说明](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/website/docs/user-guide/features/hooks.md#L531-L575) | 前置 hook 可承接工具层检查；不能涵盖所有 CLI、宿主直写或直接 apply |
| 后台 review 是独立执行路径；配置读取异常有继续启用分支 | [background_review.py](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/agent/background_review.py#L188-L202) | 后台任务也必须计入统一资源/取消预算，不能只约束前台 |

上述事实支持 [R03](r03-native-evolution.md) 的工程判断：将原生候选入口与受保护批准目录结合，并用真实评测回执和周期领域人审控制晋升。它们不支持“原生已经完整实现本项目 RCA 学习链”。内部 RCA 的实际字段、访问权、确认人和质量阈值仍需业务方提供。

## 4. 原生 Skill 加载不能只看 external_dirs

固定版本的 [skill_utils.py](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/agent/skill_utils.py#L337-L413)支持 local、create_dir、external_dirs 等根目录；[扫描顺序](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/agent/skill_utils.py#L802-L810)、[索引去重](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/tools/skills_tool.py#L181-L223)和 [skill_view 查找](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/tools/skills_tool.py#L461-L480)有顺序与同名冲突语义，可信项目路径可能覆盖同名技能。后台的[外部 Skill 写保护](https://github.com/NousResearch/hermes-agent/blob/345cd2b057a452236de401d3534b8502a7465e8d/tools/skill_manager_guards.py#L164-L183)也不等于所有前台和文件系统访问均只读。

因此 R06 的正式采用需验证：批准包是否实际被发现、加载和执行；同名候选/项目目录能否遮蔽；写身份与挂载是否受管；目录或配置被替换时是否拒绝；依赖、解释器和包 hash 是否属于同一个验收版本。候选必须放在正常扫描根之外；把 pending 放进活跃的 create_dir 会进入原生扫描，不能作为隔离方案。现有固定 probe 的成功不替代这些测试。

<a id="sources-weknora"></a>

## 5. WeKnora：内容、Skill、修订、发布和索引

**当前项目路径。** [assets.py](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/assets.py#L9-L45)以 manual knowledge 保存/读取知识和 JSON Skill 包；[历史能力探测](../../evidence/weknora-capabilities-1791478160281775602.json)记录运行实例 `/skills` 的有限结果。该探测不能变成“上游没有 Skill API”，也不能变成“原生 Skill 已被 Hub 使用”。

**邻近源码事实。** [routes_agent.go](https://github.com/Tencent/WeKnora/blob/1edcd54b43606d9079bb36650efe3f68707a79ea/internal/router/routes_agent.go#L70-L90)可见原生 Skill/sandbox 相关接口；[knowledge_create.go](https://github.com/Tencent/WeKnora/blob/1edcd54b43606d9079bb36650efe3f68707a79ea/internal/application/service/knowledge_create.go#L988-L1113)的 manual 更新先保存内容/metadata 和待处理状态，再异步处理索引。该路径读取旧版本后递增，不等于客户端指定预期版本的跨文档 CAS。

**本项目判断。** 保留 WeKnora 作为内容权威，Hub 的唯一发布协调器管理联合 release、base/current CAS 和资格；远端写入与本地事务必须通过对账闭合。问题驱动检索还需单独验证索引就绪、修订、草稿/未采纳内容不可见和撤回传播。需要针对锁定运行镜像做兼容测试，不能用邻近源码的行为替代现场结果。

<a id="sources-mcp"></a>

## 6. MCP：协议兼容、传输认证和业务授权

[MCP 2025-03-26 生命周期](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle)要求服务端只协商实际支持的版本。[2025-06-18 授权规范](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)针对 HTTP 传输，区分 stdio，并要求接收方校验 token 目标，禁止将客户端 token 直接透传给下游。[OWASP 授权指南](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)说明默认拒绝和逐请求验证的原则。

当前 [node_mcp.py](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/node_mcp.py)是手写 stdio 适配，initialize 会回显客户端版本；应定位为受限验证实现。后续兼容验收要包含明确支持版本、初始化、未知方法、输入、超时和断开，不能声称任意 MCP 客户端完整兼容。

业务上的 owner/project/engine/target/Run/attempt 权限不由传输自动提供。本项目应保留用户、Gateway、Companion、资产服务和 WeKnora 各自的身份边界，在服务端把同一个可信上下文用到最终动作。工具的“只读”描述或 annotations 也不能替代对底层脚本和写请求的核查。

<a id="sources-cgroup"></a>

## 7. cgroup、CPU 亲和性和容量证明

[Linux 6.12 cgroup v2 文档](https://docs.kernel.org/6.12/admin-guide/cgroup-v2.html)分别定义：`cpu.max` 为周期 CPU 时间限额，cpuset 为可运行 CPU 范围，`memory.high` 为回收/节流阈值，`memory.max` 为内存限额；仅设置 high 不会直接停止工作。新子进程继承父组，移动旧进程不会自动迁移其已经存在的子进程。[sched_setaffinity](https://man7.org/linux/man-pages/man2/sched_setaffinity.2.html)约束线程可运行 CPU 集合，可由有权主体修改。

本项目[当前资源源码](https://github.com/zcimon57-svj/hermes-webui-engine-hub/blob/6e6c4e897c62078ff1f14f072abe3fd7d7c461b3/engine_hub/resources.py#L16-L23)设定 3 GiB max、2.5 GiB high、192 tasks，以及 Linux/Windows 各 2 GiB 预留；[v3 配置读回](../../reviews/2026-10-09-reassessment/resource-budget-v3-applied.json)明确 CPU controller unavailable，模型和双节点峰值未运行。单核亲和性不是 CPU 时间配额，配置通过也不证明任意未定模型能进入此包络。

工程建议是把后台学习、分类模型、Gateway、容器及派生进程都算入同一准入/运行预算，并实测拒绝和触线停止；跨 host 时还需要 Manager 全局配额与各 host 限制共同生效。没有新增容量数字或阈值承诺。

## 8. 本地分类模型研究如何进入本轮评审

保留[原有分类调研](../../reviews/2026-10-09-reassessment/local-classifier-analysis-v1.md)作为候选来源：该文把 Jev 作为商业接口对照，把 Laya、GLiClass 等列为本地研究候选，**没有完成本项目的定型、部署或领域验收**。其中旧 1 GiB 预算按历史阅读，当前资源口径见上一节。

本轮 [R02](r02-local-routing.md)定义候选约束、拒识、绑定冲突、离线制品和验收方法；不再次凭公开榜单宣布模型优胜。模型/权重/运行器/语言/许可证和转换后摘要需要逐一确认，质量、冷加载峰值、延迟和线程预算需在本域数据上测量。选择、参数阈值和扩展容量作为[决策项](decisions.md)待签收。
