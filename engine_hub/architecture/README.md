# Engine Hub 五模块架构与评审入口

**当前评审：[PR #12](https://github.com/zcimon57-svj/hermes-webui-engine-hub/pull/12) · [总账 #2](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/2)。**

完整材料见[六目标评审入口](goals/README.md)：先读[系统现状/目标架构与端到端流程](goals/overview.md)，再看[审查发现](goals/review-findings.md)、目标设计、[待决策表](goals/decisions.md)和[验收解释](goals/acceptance-matrix.md)。原PR保持打开，由用户转发给他人；文档通过不等于实现或领域验收。

## 固定的五个一级模块

| 模块 | 职责与边界 | 详细入口 |
|---|---|---|
| 业务接入 | 身份/对象权限、目录与业务目标路由、输入修订、会话/报告投影；模型只建议 | [模块摘要](business-access.md) · [R01](goals/r01-isolation-and-ui.md) · [R02](goals/r02-local-routing.md) · [R04](goals/r04-access-control.md) |
| Agent Manager | 唯一Run/尝试/worker分配、取消/恢复与产物权威；内部接口仍待验 | [模块摘要](agent-manager.md) · [R05](goals/r05-multi-node-and-artifacts.md) |
| Agent Core | Hermes执行、按scope私有状态、隔离候选/评测、批准本地快照 | [模块摘要](agent-core.md) · [R01](goals/r01-isolation-and-ui.md) · [R03](goals/r03-native-evolution.md) |
| 知识平台 | WeKnora内容；单一release协调与批准消费/检索资格；节点缓存不成为权威 | [模块摘要](knowledge-platform.md) · [R06](goals/r06-assets-and-local-skills.md) |
| MCP接口 | 在可信Run/目标上下文中访问业务证据与批准资产；不取代业务授权 | [模块摘要](mcp-interface.md) · [R04](goals/r04-access-control.md) · [R06](goals/r06-assets-and-local-skills.md) |

WebUI为交互面，评测器/发布协调/伴随服务属于相应模块内部职责，图中存在一个框不意味着必须新增独立平台。当前新增Hub只直接复用上游样式、保留上游代码并调用Hermes Gateway；原Profile/API/SSO/工作区全套能力未整合。[源码归属](../reviews/2026-10-09-reassessment/isolation-implementation-analysis-v1.md)与[固定版本](../versions.lock.json)给出基线。

## 当前事实和待实施边界

本地ReferenceManager仅用于开发合同验证；单热Gateway自动轮换与手工最多两个节点不证明当前版本同时双节点容量。内部Manager、RCA与真实业务交付F30未验，第二物理主机F21未验，真实领域学习F11未验。

本轮静态审查还发现读取下游触发派发/stop、脚本继承管理权限、同引擎换实例被旧绑定提前返回、评测只记录布尔值、远端发布与本地CAS事务分离等具体问题；对应修法、来源和关闭条件均在[审查发现](goals/review-findings.md)，没有因文档更新而宣称修复。

执行仍受[三个要求](goals/execution-requirements.md)约束：保留历史/许可证/失败证据，生产分类选用经核实的内部本地方案，3GiB聚合max/2.5GiB high/0swap/192tasks与双宿主准入。CPU是亲和性降级限制，不是已生效cpu.max；当前用户宿主状态未在本轮探测。

原PR #1作为历史合入基线保留；实现进度在[总账](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/2)及分项Issue更新，[历史进度快照](../reviews/2026-10-09-reassessment/goals-progress-v2.md)和[STATE](../STATE.json)保持可追溯。
