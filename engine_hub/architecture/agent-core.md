# Agent Core

**2026-10-09 评审补充（待审、未改变实现状态）：** 新conversation不自动隔离同Home Memory；需按可信state_scope解析实际状态和提示/工具输入。pending必须位于全部普通Skill扫描根外，不能放入活跃create_dir。当前lab生成配置关闭memory/user_profile特性不等于所有写入口屏障。[R01](goals/r01-isolation-and-ui.md)、[R03](goals/r03-native-evolution.md)、[R06](goals/r06-assets-and-local-skills.md)提供具体边界与负例。 [完整评审入口](goals/README.md)。

目标职责：运行真实Hermes Gateway与原生Session/MCP能力；保持节点与任务私有状态；受控生成学习候选并读取批准知识/Skill。当前部署与隔离封装见[lab.py](../scripts/lab.py)、[Companion](../companion.py)、[资源控制](../resources.py)。

每节点独立Home/配置/工作区/端口/密钥，在Bubblewrap环境中使用自己的/state和/workspace。共享宿主内核与网络，不等于强租户网络隔离或每Issue任意代码隔离。I01：Companion执行批准脚本仍继承可见控制凭据的环境；必须先拆脚本执行身份/挂载，不能通过批准标签掩盖执行权限缺口。

当前MCP读取特定批准包、按hash落approved-cache，再返回方法/引用/脚本结果；不是已完成通用Hermes原生Skill目录安装。lab在首次生成配置时设置memory_enabled/user_profile_enabled=False；既有配置和所有写入口仍需核查，自动学习链尚未接入。

用户确认的改造：原生前台/后台业务Memory/Skill写入私有pending或候选目录，在操作运行生效前拦截；候选仅用于隔离评测，不进入正常Skill发现/RAG。统一受管写口及approve路径，所有正式变更必须有RCA/实际评测/周期人审回执。

批准后，各同引擎节点经API取得固定版本和hash，准备本地只读快照，通过受管Skill加载路径使用；旧Run固定旧版本，新Run采用新版本。采用实际只读挂载/独立发布身份保护正式内容，私有候选不能覆盖同名批准Skill。原生通用加载与此写入闭环仍待实现。

Memory、会话、凭据和可写Home不自动跨节点同步。迁移只恢复已授权输入/必要检查点，不能复制完整Home。共享批准版本与内容，各节点各自保存私有状态。

资源：当前包络3GiB max、2.5GiB high、0swap、192tasks、单核亲和性；CPU cgroup配额未委派。宿主Linux/Windows各保留2GiB并加新负载预留；单模型任务槽、触线停止、不自动重启。跨VM总预算另需Manager约束。

待补与验收：I01/I02/I03/I06；脚本不可读管理凭据、双节点互不可越权、未审候选不生效、批准版本真实被原生加载、撤回/漂移拒绝、断线不伪造迁移成功。责任：Core维护者。
