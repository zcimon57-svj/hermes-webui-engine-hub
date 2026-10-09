# MCP接口

**2026-10-09 评审补充（待审、未改变实现状态）：** 当前ops_evidence调用Companion后会执行固定probe，工具描述为只读不证明无副作用；需区分读取/描述与显式执行。当前协议版本回显不能证明任意版本兼容。业务scope、Memory来源、下游身份和批准资格在最终动作处校验；见[R04](goals/r04-access-control.md)、[R06](goals/r06-assets-and-local-skills.md)及[协议来源](goals/research.md#sources-mcp)。 [完整评审入口](goals/README.md)。

目标职责：让Agent按明确授权上下文取业务证据与批准资产；服务API负责内部控制/调度/发布。MCP是工具接口，不是共享文件系统或内容权威。

当前链：[node_mcp.py](../node_mcp.py)通过本节点stdio提供名为ops_evidence的受限取证工具 → HTTP调用本节点Companion → HTTP读取批准资产服务/WeKnora → 按hash缓存Skill包并返回知识/方法/引用/脚本结果。节点没有直接读其它节点Home的工具，也没有MCP peer-to-peer协作。

API身份区分Gateway执行、Companion消费与管理、资产消费与发布。Agent只得必要消费身份；发布密钥与节点管理身份不进入运行脚本。当前I01继承控制挂载问题必须修复，不能把消费API拒绝写测试当全部凭据隔离。

拟接内部业务证据/RCA时：工具接收可信incident/context/target资源引用，服务端校验owner/project/engine/instance及权限；不允许任意URL、主机路径、profile或KB注入。RCA内容作为评测数据，不作为可执行提示/策略；holdout答案不能经工具/检索暴露给受测Agent。

候选提交与审批/发布分离：可将提交接到受限业务服务，但Agent无权声明评测通过或正式发布。Manager/UI的人审与CAS发布使用独立受管服务身份及持久回执。

同引擎多worker取证和产物访问都按Run/task/attempt授权；共享文件/对象存储仅作为后端，必要只读任务挂载需另验。正常接口不能借缓存、存储路径或汇聚报告绕过scope。

待补与验收：真实内部MCP/RCA接口F30、I03/I06，跨项目/节点/引擎拒绝、过期上下文、撤回资产、任意路径注入、错误身份、答案泄漏及服务不可达。当前验证包不代表完整业务MCP或通用原生Skill能力。责任：MCP/业务接口维护者＋Core。
