# 可复查证据索引

2026-10-09。所有 FAIL 与追加尝试保留；不同时间/代码版本按各自范围解释。

| 证据 | 实际含义 |
|---|---|
| [live-20261008T153103.json](live-20261008T153103.json) | 49 项真实 HTTP/节点/角色功能检查（资源事件前） |
| [governance-recovery-20261008T153325.json](governance-recovery-20261008T153325.json) | 18 项真实发布竞争、撤回、回退、离线、重启检查（资源事件前） |
| [browser-guarded-2026-10-08T17-06-57-896Z.json](browser-guarded-2026-10-08T17-06-57-896Z.json) | 资源护栏下三浏览器上下文、只读启动、远端资产和移动布局 |
| [guarded-hub-20261008T170041.json](guarded-hub-20261008T170041.json) | 资源护栏下六节点逐个唤醒、消费密钥拒绝写入、取消和恢复；37 项 |
| [final-edges-1791481451416686618.json](final-edges-1791481451416686618.json) | 最后代码的 native revision/依赖包、发布消费、幂等、丢回执恢复、项目权限 |
| [resource-controls-1791480527113427669.json](resource-controls-1791480527113427669.json) | 实际内核限额、子线程/子进程 CPU 亲和性、跨进程模型单并发 |
| [luna-guarded-1791480044434422462.json](luna-guarded-1791480044434422462.json) | 资源护栏内实际 Luna 调用 |
| [luna-routing-20261008T152931.json](luna-routing-20261008T152931.json) | 21 条合成标注分类题真实 Luna 结果 |
| [luna-hermes-retry-run.json](luna-hermes-retry-run.json) | 实际 Luna → Hermes/MCP/WeKnora → 报告；此前 429 失败另保留 |
| [luna-learning-proposal.json](luna-learning-proposal.json) | 实际 Luna 生成的合成证据候选，未自动发布 |

资源事件：[诊断](resource-diagnosis-20261009.json)、[重启前节点心跳](prereboot-node-memory-20261009.json)。受限 WeKnora 启动卡点：[栈证据](guarded-weknora-startup-stall.json)。

其它 live/guarded/browser JSON 中的 FAIL 原样保留；部分为验证器错误，部分为预算拒绝/就绪竞争/接口边界，均不得计作通过。运行日志、数据库、身份和全部连续采样保存在忽略的 `.local`；正式摘要/截图/矩阵在 Git。
