# 当前目标、设计与证据入口

2026-10-09。整体功能仍部分实现；本轮将目标、进度、已确认设计和架构提交PR作为后续工作基线。仓库公开已由用户明确授权，公开检查与PR/合并核对见交付记录；历史PRIVATE记录只表示当时状态。

- [五模块架构总览](../../architecture/README.md)与各模块文档。
- [六目标/三要求、简单自进化设计、责任与未完成项](goals-progress-v2.md)；[机器可读进度](goals-progress-v2.json)。
- [当前源码归属与隔离边界](isolation-implementation-analysis-v1.md)、[源码SHA/差异](isolation-implementation-provenance-v1.json)。
- [同引擎多资源路由/产物与MCP/本地目录关系](multi-resource-routing-artifacts-v1.md)：扩展分析，尚未实施或验收。
- [受控进化合同](evolution-quality-contract-v2.json)：原生候选→最终RCA门禁→周期人审→CAS发布。外部项目仅参考，不引入依赖。
- [本地分类分析](local-classifier-analysis-v1.md)：本地模型尚未接入，不受“外部自进化项目不引入”决定影响。
- [实际3GiB/2.5GiB空cgroup核对](resource-budget-v3-applied.json)、[资源回归检查](resource-budget-v3-checks.json)。CPU为单核亲和性，非已生效CPU配额；模型与双节点峰值NOT_RUN。

已确认共享方式：通过受控MCP/HTTP取得统一批准内容，各节点本地只读副本执行；不共享可写Home、私有Memory、会话和凭据。当前消费是特定包适配，通用原生Skill加载与原生候选闭环待实现。

下一步：I01凭据隔离、I02实际同时双节点、I03RCA/评测/人审产品链、I04管理授权、I05本地分类/多空间、I06通用Skill/检索。F11已有RCA来源为用户报告，但数据/确认状态/阈值未核查；F21第二主机、F30内部接口仍未验。旧29 PASS不作目标完成率。

历史研究与阶段检查保留：

- [Jev/Laya等分类来源](research-sources-v1.json)、[社媒证据](social-evidence-v1.md)。
- [原生/独立进化研究](self-evolution-analysis-v1.md)、[质量门禁项目参考](native-evolution-quality-gates-v1.md)、[RCA路线研究](rca-gated-native-evolution-v2.md)。此前未定选/预算未应用等文字按历史版本阅读，当前决定以上述进度/架构为准。
- [文档保护检查](documentation-validation-v1.json)、[RCA路线文档检查](rca-route-document-checks-v1.json)、[简单设计检查](simple-evolution-design-checks-v1.json)、[源码分析检查](isolation-analysis-checks-v1.json)、[多资源分析检查](multi-resource-analysis-checks-v1.json)。这些不是生产业务验收。

原[执行合同](../../contracts/EXECUTION-v1.md)保留历史内容，最新用户决定已写入当前状态。后续工作以本入口、架构、进度和实际证据继续。
