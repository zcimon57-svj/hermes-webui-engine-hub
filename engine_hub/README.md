# Hermes WebUI Engine Hub（私人派生仓）

实现入口为 `engine_hub`，保留上游完整 Git 历史、许可证和 `upstream` remote。基线 WebUI 为 `4a0639397d1d4eb14965d9e88f39aecffa9ef345`；Hermes 固定为 `345cd2b057a452236de401d3534b8502a7465e8d`，真实 health 为 0.21.3。

一个 UI 提供四引擎六节点目录、三类登录、授权空间路由、私有会话/报告、真实 Gateway Run/取消、远端节点状态 CAS，以及远端 WeKnora 知识/Skill 包的候选、评测、批准、撤回和回退。内部 Manager 通过版本化客户端接入；本地验收使用明确标注的 reference Manager。业务状态权威在 Manager，正式内容在 WeKnora，唯一发布指针由薄的 release coordinator 管理。

## 当前验收边界

[验收矩阵](acceptance-local-r1.json)、[版本锁](versions.lock.json)、[状态](STATE.json)和 [证据索引](evidence/INDEX.md)承载现场结果。失败尝试、资源事件及先前反例均保留。

- 真实 HTTP、浏览器、Hermes Gateway、MCP、WeKnora和独立测试身份已验证；确定性协议 fixture 与合成内容用于功能验收。
- 用户指定的 `gpt-6-luna` 已实际调用：21 条合成标注分类题全部匹配；已完成一次真实 Hermes → Luna → MCP → WeKnora → 报告链，并另做受限环境下的真实 Luna 分类。CLI 配置和 usage 可核对，CLI JSON 不暴露 provider 的 `response.model`。
- F11 领域学习质量、F21 第二物理主机、F30 内部环境继续 NOT_RUN。真实学习收益、生产诊断和外部工单关闭尚未验收。
- 同宿主的节点 Home、工作区和 API 身份隔离；共享宿主、内核、网络。逐不可信 Issue 的任意代码强隔离不属于已通过项。

## 资源合同（用户最新约束）

**所有本轮负载合计受 `eh158.slice` 限制：1 GiB RAM、192 个线程/进程、0 swap。** 896 MiB 为软停止线。当前 WSL 只委派 memory/pids；CPU 通过所有进程、容器入口和子线程固定核心 0 并持续核对实现，不能把未生效的 CPUQuota 属性当证据。

启动前同时核对 WSL 和 Windows 可用内存；至少保留 WSL 2 GiB、Windows 512 MiB，另计本次启动预留。宿主采样不可用、已有 swap 压力或预算不足时拒绝新工作。每五秒监控；触线先持久化原因，再停止本轮 slice，保持人工/控制器显式 reconcile，禁止自动恢复。监控器另有 64 MiB/16 tasks 限制。仅回收本轮 cgroup 的缓存，不修改 WSL/Windows 全局配置，不操作其它会话或服务。

本受限宿主通常只保留一个热 Gateway；Manager 按授权引擎按需唤醒、任务完成后轮换，同会话固定节点。忙碌/不确定 Run 不被迁移或为了腾容量而停止。手工批次最多两个节点，仍受总预算检查。六个节点可以串行实测；不能把串行验收声称为六节点同时常驻的资源验收。历史同时部署证据另列其时间与边界。

## 运行和复建

需要 Linux、Bubblewrap、用户 systemd 的 memory/pids 委派、Docker rootless、Python 3.11 Hermes 环境。既有环境仅作为只读依赖使用；可以通过 `ENGINE_HUB_HERMES_SOURCE` 和 `ENGINE_HUB_HERMES_PYTHON` 指定同 SHA 的独立安装。跨机器冷安装仍未验证。受限容器的静态 CPU 入口当前面向 Linux x86_64。

```bash
python3 -m unittest engine_hub.tests.test_policy engine_hub.tests.test_resources -q
python3 -m engine_hub.scripts.guarded_exec -- gcc -nostdlib -static -Wl,--build-id=none \
  -o engine_hub/.local/affinity-launcher engine_hub/scripts/affinity.S
python3 -m engine_hub.scripts.infra
python3 -m engine_hub.scripts.seed
python3 -m engine_hub.scripts.lab start --nodes ''
python3 -m engine_hub.scripts.lab status
```

入口 `http://127.0.0.1:15800`。资料均为本地测试数据；容器卷和 `.local` 不进入 Git。`eh158r-*` 是受限容器；前次 `eh158-*` 容器保持停止及数据留存。DuckDB 的 spatial/excel 自动安装被固定版支持的开关关闭，本期仅验 Markdown/Skill 包，xlsx 导入不在通过范围。

三个默认 UI 角色是 `admin`、`viewer`、`chat`。登录资料保存在忽略的 `.local/login-users.json`。`reviewer` 仍是 Admin 角色，另外明确授予评测/发布 capability；普通 Admin 没有发布权。`restricted` 仅有 PG 范围。用户还可配置 `spaces`，项目/实例绑定和共享会话受服务端检查。

管理员看脱敏配置/诊断、排空节点、通过读回 SHA 写远端 Memory/固定工作区记录。Viewer 只浏览授权信息，页面初始化不创建会话。Chat 提问、追问、取消自己的回答。私有会话默认只属于作者，通过“授权只读共享”向有相应引擎/空间权限的账号开放。

普通问答选逻辑引擎或提供登记实例；未知/歧义要求澄清。追问保持原空间与节点，明确换引擎创建新安全状态。请求不接受任意 Gateway URL、API key、Profile 或 KB 扩权。

```bash
# 显式模式变更仅在没有活动/不确定 Run 时进行：
python3 -m engine_hub.scripts.model_mode luna
python3 -m engine_hub.scripts.lab start --nodes ''
# 安全预算不足会拒绝模型调用，不回退到另一模型。
python3 -m engine_hub.scripts.model_mode fixture
python3 -m engine_hub.scripts.lab stop
```

`lab stop` 停止登记的进程 scope；容器仍在独立 slice 中。停止整个本轮环境可使用 `systemctl --user stop eh158.slice`，数据和卷保留。监控器的 unit 单独登记在 `.local/watchdog.json`。禁止停止整个 user slice、WSL 或相邻服务。资源 trip 的原因先核对、修复，再通过 `python3 -m engine_hub.resources reconcile` 解除，之后显式启动。

## 内容、版本和学习

本锁定 WeKnora 镜像的 `/skills` 返回空目录；提供明确的 RemoteSkillProvider 包适配：Skill 包以远端 manual knowledge 内容保存，包含 `SKILL.md`、`scripts/probe.py`、`references/method.md`，可带 `dependencies.json`。这是远端包适配，不是声称原生 WeKnora sandbox Skill 自动兼容 Hermes。

节点从批准版本下载并校验只读、内容寻址快照；方法、引用和脚本实际消费。依赖使用钉死的 Python/包版本检查已预置的只读环境，缺失或版本不合就拒绝，禁止自动安装/升级。旧合成包采用 Python 3.11 标准库合同。内容、native `remote_revision` 与联合 `release` 是不同身份；发布固定文档 ID、摘要、原生修订、配置摘要，CAS 决定唯一 current 指针。在途 Run 保持固定 release；远端漂移、撤回、鉴权失败不允许旧缓存继续执行。

允许的反馈先形成所属节点/会话的私有草稿，经明确共享同意写入所属引擎的远端候选，再评测、独立账号审核和发布。同引擎分享批准成果，其它引擎保持原版本。人工候选验证治理机制，真实 Luna 候选保留为待专家审阅，均不证明真实学习质量。

## 实现地图

| 一级模块 | 此次职责与文件 |
|---|---|
| 业务接入 | `auth.py`、`routing.py`、`server.py`、`static/`：身份、角色/空间检查、交互与输入修订 |
| Agent Manager | `manager.py`：ManagerClient、本地 reference、幂等、持久 Run、取消/恢复、报告 SHA/本地回执；`supervisor.py`：开发环境受限节点生命周期 |
| Agent Core | `companion.py`：单节点状态、CAS、私有草稿、只读执行快照；`resources.py`：资源预算；`codex_luna.py`/`luna_bridge.py`：受控模型协议适配 |
| 知识平台 | `assets.py`：WeKnora 内容客户端与单一 release/CAS 权威 |
| MCP接口 | `node_mcp.py`：只读证据及批准知识/Skill 消费；消费密钥不能修改节点状态，状态管理密钥位于 Gateway 不可见的伴随服务控制目录 |

WebUI 自己的状态仅包括身份/权限、会话展示和持久输入意图；业务 Run 的终态和报告在 Manager，真实执行在 Gateway。UI 丢回执后从 Manager 恢复授权可见性；同输入修订不产生重复 Run。所有列表、详情、下载及 SSE 使用同一可见性检查。SSE 提供有限状态/事件快照，页面每四秒轮询；没有另造常驻 token 流权威。

## 验证入口

```bash
python3 -m engine_hub.scripts.guarded_exec -- python3 -m engine_hub.scripts.verify_resource_limits
python3 -m engine_hub.scripts.guarded_exec -- python3 -m engine_hub.scripts.verify_guarded_hub
python3 -m engine_hub.scripts.guarded_exec -- python3 -m engine_hub.scripts.verify_final_edges
python3 -m engine_hub.scripts.guarded_exec -- node engine_hub/scripts/browser_guarded.cjs
```

浏览器依赖通过 `ENGINE_HUB_PLAYWRIGHT` 指向既有 Playwright；本机现存路径仅是依赖复用，版本锁另记。不要为了读证据重复跑 probe；它会创建新测试会话。全部运行均保留失败和额外尝试，测试不修改母仓已有未提交文件、历史源码、内部服务或其它实验。

## 未决项与接手

| 项目 | 责任角色 / 下一步 / 通过条件 |
|---|---|
| F11 真实学习质量 | 领域维护者＋确认人：提供有领域真值的真实回放集、阈值和独立审阅；候选正确、反例拒绝和业务效果分别验收 |
| F21 第二物理主机 | 运行维护者：提供授权测试主机/网络/身份；按相同固定版本测试远程断线与节点状态 |
| F30 内部接入 | Manager/身份/MCP维护者：提供实际版本、接口、作用域和投递回执；保持内部 Manager 权威，实测取消、恢复、权限与业务交付 |
| 不可信任意代码/HA | 运行与安全维护者：独立环境和故障合同；本机 Bubblewrap/受限批准脚本不外推强隔离或 HA |
| 规模与领域分布 | 架构师/PM/领域：更大且已签收的分类集、真实反馈与容量计划；21 条合成题只证明本次小样本结果 |

下一 session 先读本文件、STATE、验收矩阵和资源采样，核对 Git、PRIVATE、精确 SHA 与运行 unit/boot 身份；保持资源总上限，继续仍有授权环境的条目，不重建覆盖现有身份/会话/发布清单，不把 NOT_RUN 变成 PASS。
