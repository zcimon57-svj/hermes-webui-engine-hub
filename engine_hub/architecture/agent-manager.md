# Agent Manager

职责：现有业务Manager拥有Run生命周期、节点分配、产物索引、评测/审批状态和交付回执。WebUI只投影状态；Worker只执行。当前[ManagerClient/ReferenceManager](../manager.py)是新适配合同与本地开发替身，不是内部Manager已上线。

当前基础：输入幂等、engine/启用/运行数/健康筛选、会话固定节点、固定知识/Skill release、取消与终态报告SHA。本地[Supervisor](../supervisor.py)仍单热Gateway；手工上限两个，同时双节点I02 NOT_RUN。

路由先定授权engine/project/instance/target，再选能访问目标且能力/版本/预算满足的worker。独立工单一Run一worker；若一个工单确需多执行资源，讨论方案为parent Run＋有限task。跨VM可信注册、租约/attempt代际、自动迁移与子任务汇聚均尚未实现。

产物归business Run/task/attempt。Manager持久化manifest/报告revision/交付引用；日志、附件和中间文件进已有内部存储。节点临时目录不作为最终存储；执行结束但上传未确认不算交付，多个worker不能覆盖同一报告。汇总报告不扩大底层证据授权。

受控学习记录：来源incident/Run/报告、RCA版本、base release、candidate hash、评测器/题集版本、评测结果、审核身份/决定、发布回执。状态：WAIT_RCA → WAIT_EVAL → WAIT_REVIEW → APPROVED → PUBLISHED。未知/失败/未审均不能发布，审批后内容或基线变化重新评测/审核；现有客户端passed=true不是真实评测器。

故障迁移讨论：新attempt绑定新worker和必要检查点，旧代际不得覆盖新结果；有副作用结果未知先核查，不自动重试。取消先持久化意图并关闭新派发；晚到回执不得复活取消Run。跨主机模型额度由Manager统一分配，当前本地flock不是分布式预算。

待补与验收：I02/I03、内部F30、跨主机F21；覆盖重复请求、并发、断线、丢回执、晚到结果、CAS冲突、取消和产物缺失。责任：Manager维护者＋验证执行者。
