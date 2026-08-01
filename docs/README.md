# Nebula 工作区文档

本目录由工作区元仓库管理，只保存跨 `nebula` 后端与 `nebula-studio` 前端的架构、现状和开发计划。单仓库的 API、配置及运行手册仍以各自仓库的 `README.md` 与 `docs/` 为准。

## 文档索引

| 文档 | 职责 |
| --- | --- |
| [模块规划.md](./模块规划.md) | 当前模块树、职责边界、运行拓扑和依赖原则 |
| [nebula-current-state-analysis.md](./nebula-current-state-analysis.md) | 基于代码证据的全栈实现快照、已知缺口和风险 |
| [nebula-development-detailed-plan.md](./nebula-development-detailed-plan.md) | 从当前缺口出发的跨仓库实施顺序与验收关口 |
| [nebula-studio-frontend-refactoring-plan.md](./nebula-studio-frontend-refactoring-plan.md) | 前端现状、已完成重构及剩余增量工作 |
| [PostgreSQL_实时离线一体化数据平台方案汇总.md](./PostgreSQL_实时离线一体化数据平台方案汇总.md) | 独立的数据平台方案，不作为 Nebula 当前实现状态的证据 |

## 当前审查基线

工作区文档于 **2026-08-01** 按以下代码基线重审：

| 仓库 | 分支 | 提交 |
| --- | --- | --- |
| `nebula` | `development` | `3d35d13ad23feb4ce367585b77de90094f3f2e26` |
| `nebula-studio` | `development` | `5a36a7e09787889607d53ddea65b3e25b98b5397` |

判断优先级为：可执行源码和构建描述符 > 运行配置与迁移 > 仓库内状态文档 > 历史计划。代码中存在类或接口，不等于对应应用已经启动或端到端链路已经通过。

## 维护规则

1. 模块、端口、脚本和版本必须从仓库文件读取，不复制旧计划中的假设。
2. 已完成能力从开发计划移出，在现状文档中保留证据；未通过运行验收的能力不得标记为“可部署”。
3. 后端单域细节更新到 `../nebula/docs/`，前端单域细节更新到 `../nebula-studio/docs/`；本目录只维护跨仓库结论。
4. 每次重审同时更新基线提交、已知阻塞、验收命令和文档间链接。
