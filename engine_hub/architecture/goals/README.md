# 六个功能目标的架构评审

[目标/进度总账 #2](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/2)。本目录按R01–R06组织架构，便于对应Issue逐项评论，不新增一级模块。五个一级模块仍是业务接入、Agent Manager、Agent Core、知识平台、MCP接口，见[模块职责总览](../README.md)。

用户已确认的方向与本PR需要评审的接口/状态/边界分开标注；文档通过不意味着实现或领域验收通过。此前PR #1为已合入基线；本轮PR保持打开，用户转发，不指定评审人、不自动合并。

| 目标 | 架构文件 | 涉及模块 |
|---|---|---|
| R01 隔离与统一UI | [R01](r01-isolation-and-ui.md) · [Issue #3](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/3) | 接入、Manager、Core、MCP |
| R02 本地分类/空间路由 | [R02](r02-local-routing.md) · [Issue #4](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/4) | 接入、Core、Manager |
| R03 原生RCA门禁与共享进化 | [R03](r03-native-evolution.md) · [Issue #5](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/5) | 五模块及领域人审 |
| R04 三角色与scope | [R04](r04-access-control.md) · [Issue #6](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/6) | 五模块的权限边界 |
| R05 多节点/资源/产物 | [R05](r05-multi-node-and-artifacts.md) · [Issue #7](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/7) | Manager、Core、MCP、接入 |
| R06 远端资产/本地批准副本 | [R06](r06-assets-and-local-skills.md) · [Issue #8](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/8) | 知识、Core、MCP、Manager |

E01代码/仓库交付、E02真实模型与本地分类、E03资源控制是跨目标执行要求，在Issue跟踪并约束各架构。本轮不把目标进度通过文档PR自动关闭，也不引入外部进化、评测或工作流项目。

评审应逐项留下：认可内容、阻塞问题、待补证据、接口/责任调整。重点检查I01控制凭据、I02同时双节点、真实评测替代passed=true、原生Skill加载与共享、跨VM计划与当前单机事实之间的边界。

## 三个执行要求的评审约束

| 要求 | Issue | 对架构的约束 |
|---|---|---|
| E01 | [#9](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/9) | 保留上游历史/许可证/代码与失败证据；提交与远端SHA可核对，文档待审不等于业务通过 |
| E02 | [#10](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/10) | 本地生产分类与真实模型/工具/领域验证分别记录；数据/阈值/提供商边界明确 |
| E03 | [#11](https://github.com/zcimon57-svj/hermes-webui-engine-hub/issues/11) | 本机硬包络与宿主准入、单模型并发、触线停止；跨host总预算不由本地flock保证 |
