# 业务接入

**2026-10-09 评审补充（待审、未改变实现状态）：** 目录和业务路由由接入侧裁决，模型仅建议。当前conversation快捷分支会先于新instance返回，完整换目标/Memory边界仍待补。内部RCA只为用户报告，尚未读取其字段/权限；详细合同与场景见[R02](goals/r02-local-routing.md)和[R04](goals/r04-access-control.md)。 [完整评审入口](goals/README.md)。

目标职责：将工单、告警、war room输入与业务身份转换成授权引擎/项目/实例上下文；展示报告和待审学习，不接管执行或发布权威。

当前新增Hub实现本地身份、Admin/Viewer/Chat能力、会话owner与部分engine/space检查、实例规则路由和歧义澄清：[auth.py](../auth.py)、[routing.py](../routing.py)、[server.py](../server.py)。原WebUI完整Profile/SSO/工作区交互未接入，管理列表范围和配置能力仍有缺口。

接入记录需要稳定incident_id关联ticket/alert/warroom、input_revision、Run和report_revision。最终RCA保存责任人确认状态、版本、时间、scope和证据。已有最终根因来源为用户报告；实际内部字段/权限/确认状态尚未读取，不声称已取得golden数据。

普通客户端只能选择授权业务范围，不能注入Gateway URL、密钥、node/profile/KB来扩权。Worker执行位置与被分析target实例分别记录；换worker不改变业务目标和权限。

最终RCA触发对已有候选的业务评测，不把session结束当学习验收完成。回放输入只含诊断时已知证据，最终RCA仅给评测器；同事件的多个告警/票据不跨开发/验收split。RCA复制Agent报告且未经独立核实，不作为独立真值。

输出：持久输入修订、授权范围和关联信息、最终RCA修订、报告展示/交付引用。业务关闭由原业务系统负责，工具成功或报告送达不自动关闭工单。

待补与验收：内部身份/事件/RCA接口F30，真值与阈值F11；负例包括跨项目、未知实例、重复输入、根因纠正、答案泄漏。责任：业务接入/身份维护者＋领域确认人。
