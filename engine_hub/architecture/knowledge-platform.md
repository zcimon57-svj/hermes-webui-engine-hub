# 知识平台

**2026-10-09 评审补充（待审、未改变实现状态）：** 当前指针CAS在Hub本地SQLite，不能回滚远端HTTP副作用。正式检索需按Run固定批准manifest过滤，内容publish读回与索引ready分别验收。通用Skill加载、同名覆盖和真实只读挂载仍待补；见[R06](goals/r06-assets-and-local-skills.md)、[RF06/RF07](goals/review-findings.md)。 [完整评审入口](goals/README.md)。

目标职责：WeKnora持有正式知识/Skill内容；薄release coordinator持有唯一current指针、CAS和发布/撤回/回退记录。节点只是经授权缓存和消费。实现见[assets.py](../assets.py)、[RemoteSkillProvider](../companion.py)。

当前各引擎独立身份/KB，通过WeKnora manual knowledge读写内容、读回原生修订与SHA；Skill采用SKILL.md/scripts/references/dependencies验证包适配。当前读取固定发布文档，通用Skill加载及问题驱动检索整链仍部分完成。

内容身份需区分WeKnora document/native revision、联合release、bundle/package hash。Run固定批准版本；每次消费检查远端身份、摘要/修订/发布状态和撤回，缓存不独立授予权限。节点不共用可写Home；同引擎批准资产分发为本地副本，不抽取跨引擎公共知识。

学习门禁：最终RCA来源与确认版本 → 静态/语义与正反例回放 → 周期领域人审 → 绑定候选hash与base revision → CAS发布读回。生成者不自批，关键错误不由平均分抵消；候选、推断和原始trace不自动成为正式知识。单个事件先作为有范围案例，通用Skill需要反例与适用前提审查。

候选隔离要贯穿检索、Skill发现、缓存和评测数据；仅加draft标签而正常RAG仍读出不合格。个人偏好/节点私有Memory不自动成为同引擎业务规则。

RCA纠正/撤回时失效相关评测，将依赖资产标记待复核并暂停新Run使用，保留历史版本/证据；并发发布或审核后基线变化拒绝旧审批。正式回退是更新发布指针，不删除历史来制造通过。

原始业务产物保存在Manager索引和已有内部存储；只将批准可复用案例/知识/Skill纳入本平台。待补：I03/I06、F11；通用包、动态检索、候选不可读、并发CAS、撤回/回退、专家领域验收。责任：知识维护者＋领域维护者。
