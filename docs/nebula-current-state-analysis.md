# Nebula 全栈当前实现状态分析

> 审查日期：2026-08-01
> 后端基线：`nebula` / `development` / `3d35d13ad23feb4ce367585b77de90094f3f2e26`
> 前端基线：`nebula-studio` / `development` / `5a36a7e09787889607d53ddea65b3e25b98b5397`
> 范围：代码、构建描述符、运行配置、迁移、测试清单及仓库内状态文档。本文不以独立的 PostgreSQL 数据平台方案作为实现证据。

## 1. 审查方法与结论口径

本次审查遵循以下证据优先级：

1. 可执行源码、`pom.xml`、`package.json`、工作区清单；
2. 应用配置、Flyway 迁移、自动配置注册和测试配置；
3. 仓库内 `development-status.md`、`implementation-backlog.md`、测试文档；
4. 历史规划和已完成阶段说明。

“存在接口、类或页面”只证明结构已落地；只有应用启动、目标测试和端到端验收通过后，才标记为运行闭环。2026-08-01 已完成 W0 实跑：历史 `ConfigService` 阻塞已修复，三个正式平台应用完成 Context、启动、健康、在线契约和无 Mock real-stack 验收。该结果只证明 G0 可运行基线，不代表发布、租户、CDC 等后续生产闭环已经完成。

## 2. 仓库快照

| 项目 | `nebula` | `nebula-studio` |
| --- | --- | --- |
| 分支 | `development` | `development` |
| 审查时工作树 | 干净 | 干净 |
| 主要语言 | Java、SQL、YAML | TypeScript、Vue、CSS |
| 代码规模快照 | 1,141 个 `src/main` Java 文件、57 个 `src/test` Java 文件 | 962 个 Git 跟踪文件、38 个 `package.json` |
| 构建体系 | Maven 多模块 | Vite+（`vp`）+ pnpm workspace |
| 生产入口 | 3 个 Spring Boot 平台应用 | Web Shell + Electron + 5 个 renderer |

后端根 Reactor 聚合 22 个顶层条目（含 `demos`），主要领域为 runtime、resource、governance、release、version-control、plugin、integration、database、capability、config、task、tenant、security、cluster、subscribe、camel、system、modules 和 platform。前端工作区包含 7 个应用清单、10 个 core 包、5 个 editor 包、3 个 UI 包及其他 contracts/styles/types/tooling 包。

## 3. 总体判断

| 领域 | 当前判断 | 关键事实 |
| --- | --- | --- |
| 后端模块结构 | 已成型 | 根 Reactor、各领域 starter、三平台应用和 demo 均存在 |
| 平台运行基线 | G0 已验收 | 三应用健康、在线 OpenAPI 和 real-stack 通过；默认 `LocalDeployTarget` 仍只记录日志 |
| Camel 集成 | 可联调、未完全生产化 | Console/Executor、Gateway、POLLING、DAG、监控和 PostgreSQL Debezium 路径存在 |
| 配置体系 | 核心能力与组合启动已验收 | basic/center、快照、失败策略、刷新和健康检查有代码；JDBC `ConfigService` 装配已由 Context 与真实启动验证 |
| 安全与租户 | 基础能力可用，隔离未闭环 | JWT/Session/RBAC 已装配；OAuth2 是未进入现行平台应用的可选模块；租户拦截器只检查上下文，不改写 SQL |
| 插件平台 | 主链路可用 | PF4J 单一生产链路、真实 Maven 下载/搜索、SHA-256、冲突检测和平台 REST 已落地 |
| 前端架构 | 基础重构完成 | Web/Electron 共享 manifest、preload capability、认证、运行时和 API client |
| 前端业务体验 | 主要界面已落地，G0 真实栈通过 | 登录、Shell、搜索、目录、插件、订阅、Settings、Monitor 和 Gateway 最小纵向路径已通过；完整业务数据闭环仍属后续波次 |
| 测试基础设施 | 已建立并实跑 G0 | Playwright 配置实际枚举 24 项测试；其中 real-stack 1 项已在三个正式应用上通过 |

## 4. 后端实现分析

### 4.1 技术基线

版本统一定义在 `../nebula/nebula-bom/pom.xml`：

| 类别 | 版本/实现 |
| --- | --- |
| Java | 25 |
| Spring Boot | 4.1.0 |
| Apache Camel | 4.20.0 |
| MyBatis / MyBatis-Plus | 3.5.16 / 3.5.16 |
| PostgreSQL / MySQL Driver | 42.7.2 / 9.3.0 |
| Flyway | 10.21.0 |
| Debezium | 3.0.7.Final |
| PF4J | 3.15.0 |
| JJWT | 0.13.0 |
| AWS S3 SDK | 2.45.1 |
| Redisson | 3.38.1 |

### 4.2 运行拓扑

当前正式 Reactor 中有三个平台应用：

| 应用 | 端口 | 职责 | 状态口径 |
| --- | --- | --- | --- |
| `platform-console` | 8090 | system、resource、governance、config、version、release、task、plugin 等管理 API 与 OpenAPI | 2026-08-01 启动、健康和在线 OpenAPI 通过 |
| `platform-integration` | 8080 | Camel 定义面、认证、租户、订阅、治理 | 2026-08-01 启动、健康及登录/Monitor 最小 API 通过 |
| `platform-integration-executor` | 8081 | Gateway、Route、DAG、任务与执行监控 | 2026-08-01 启动、健康及 Gateway 最小路径通过 |

`nebula-platform/platform-admin` 仍保留历史源码和 POM，但已从 `nebula-platform/pom.xml` 的 `<modules>` 中移除，并由目录 README 明确标记为归档，不属于当前 Reactor 或部署拓扑。

`demos/demo-camel-console` 和 `demos/demo-camel-executor` 是演示组合，不再作为目标生产入口。

### 4.3 已有可靠实现

#### 数据与基础设施

- `nebula-database` 提供多数据源、MyBatis、JPA、Flyway 约定及 PostgreSQL/MySQL 元数据适配。
- `nebula-integration` 已包含 Redis、Kafka、S3 和 Mail 客户端自动配置；S3/Kafka/Mail 有健康检查。
- PostgreSQL 迁移脚本覆盖 platform、camel、resource、governance、task、cluster 等领域，正式应用通过 Maven 资源复制聚合共享迁移。
- `capability-cache`、`capability-lock`、`capability-storage`、`capability-log`、`capability-encrypt` 有实际实现。

#### 插件平台

- `SpringBootPluginManager` / PF4J 是唯一生产加载链路。
- `MavenRemotePluginRepository` 使用 Java HTTP Client 获取元数据与 JAR，执行格式、内容类型和哈希校验；当前仍缺专门覆盖 HTTP 下载/失败分支的仓库测试。
- `LocalPluginRepository`、`PluginInstallService` 支持本地索引、安全路径和版本冲突处理。
- 平台 descriptor 与 Camel 领域 descriptor 已分层；内置 HTTP/MySQL/PostgreSQL 插件声明 Connector 能力。

#### Camel 集成

- Console 和 Executor 的 REST、Gateway、DAG/任务执行、租户授权、订阅、监控和治理代码均存在。
- POLLING 使用真实 JDBC 查询并产生订阅事件。
- CDC 可启动 Debezium Embedded PostgreSQL connector；模拟降级不再是静默行为，必须显式设置 `allowSimulatedFallback=true`，否则 `CdcProductionGuard` 抛出异常。
- Gateway 已包含权限与治理过滤，监控侧有调用日志、拓扑和进程内指标。

#### 配置体系

- `nebula-config` 已拆分 core、storage、center API、Config Server、Nacos、runtime、autoconfigure 和 starter。
- 支持 basic JDBC 启动期加载、center provider、文件快照、`fail-fast/use-snapshot/ignore`、可刷新前缀和健康状态。
- `ConfigAutoConfiguration` 创建 `ConfigService`，默认仓库为内存；JDBC 仓库由 `nebula.config.storage=jdbc` 选择，并在 Bean 实例化阶段显式要求 `JdbcTemplate`，兼容数据库 starter 的后置动态注册。

### 4.4 关键缺口

#### 已解除的 P0：Platform 启动与真实栈

2026-08-01 的 W0 实跑已替代 2026-07-26 历史失败结论。根因是 `JdbcTemplate` 由数据库 starter 通过 `BeanDefinitionRegistryPostProcessor` 后置注册，而 JDBC ConfigRepository 的 `@ConditionalOnBean` 在更早阶段求值，导致仓库和 `ConfigService` 未注册。移除该过早条件后，由构造参数在 Bean 实例化阶段显式校验 `JdbcTemplate`。

验证证据：

- 配置自动配置测试覆盖后置注册成功与缺少 `JdbcTemplate` 的明确失败；
- 三个正式应用的 ApplicationContext 冒烟测试通过；
- 142 模块定向 Reactor 测试及构建通过；
- 三应用从停止状态由 real-stack 脚本启动并通过 8090、8080、8081 健康检查；
- 8090 OpenAPI 3.1.0 包含 132 条路径，并按 token/session/oauth 模式声明认证；只把启动期静态清单标记为公开，数据库动态公开规则不会放宽文档声明；严格在线生成及幂等检查通过；
- `/monitor/**` 已从公开清单移除并由安全链按读写权限保护，真实栈确认未认证请求返回 401；
- 1 项无 Mock real-stack Playwright 测试通过，Web production build 通过。

实跑还修复了非 JSON 转换器被统一响应 Advice 包装导致的写出异常，以及 Cluster JDBC 事务跨入 JPA 租约回收导致的资源重复绑定。节点接管增加 `RECLAIMING` 原子状态与任务/订阅租约节点行锁围栏；real-stack 清理只终止本次启动且所有权可验证的服务。Integration 修复后持续运行超过一个调度周期，未再出现该事务异常。

#### P0：Release 未驱动真实 Runtime

`LocalDeployTarget.deploy()` 与 `rollback()` 只记录日志，没有激活 Camel Route、插件或任务。因此“申请 → 审批 → 版本 → 发布”只能视为服务/API 链存在，不能视为运行时闭环。

#### P1：租户隔离依赖 Mapper 自律

`MyBatisTenantInterceptor` 只检查查询 SQL 是否包含 `tenant_id` 并输出 trace，不注入条件，也不阻止缺少租户条件的 SQL。所有 Mapper 必须显式正确处理租户条件，当前无法形成统一的强制隔离保证。

#### P1：任务与集群仍缺分布式闭环

Cron、触发器、任务实例、重试、节点心跳和分片算法已有实现；依赖 DAG、共享注册表、分布式唯一触发和故障接管仍未完成端到端验收。

#### P1：认证增强尚未实现

后端现行平台已装配 JWT、Session、RBAC 和组织选择；仓库虽有 OAuth2 Authorization Server 模块，但 `security-starter` 和三个正式平台 POM 均未引入它，不能写成“平台默认启用 OAuth2”。同时，没有代码证据表明 MFA、TOTP、密码自助恢复、预认证事务和跨节点全会话撤销已实现。这些能力只能列为后续计划，不能沿用旧文档中的目标 API 当作现状。

另外，当前 Token 过滤器仍接受查询参数 Token，可能把凭据暴露到 URL/日志；撤销集合为进程内状态。CORS 默认策略也需要在生产 Profile 中按明确 Origin 收紧。

#### P2：生产化能力仍不足

- Kafka 统一发布已存在，但消费、重试/DLQ、幂等和自动配置优先级仍需验证。
- 通知包含站内、Webhook 和 Mail 通道，但记录/归档仍偏内存。
- WebSocket、集群发现、Route Trace/指标多为单进程或内存状态。
- CDC 仍可在明确授权时运行模拟模式；offset、单活与接管需要生产化。
- 插件缺少制品签名、可信供应商和依赖约束求解。
- 文件存储同时存在本地与 S3 路径，但按 `storageType` 选择实现的装配行为仍需专项测试。
- 平台开发配置中仍有被 Git 跟踪的明文敏感配置项；生产凭据必须迁出仓库并轮换，文档和日志不得复制其值。

## 5. 前端实现分析

### 5.1 技术基线

版本来自 `../nebula-studio/pnpm-workspace.yaml` 与根 `package.json`：

| 类别 | 版本/实现 |
| --- | --- |
| Node.js | `>=22.12.0` |
| 包管理声明 | pnpm 11.5.1；日常命令统一经 Vite+ `vp` |
| Vite+ / Vite | 0.2.6 / 8.1.3 |
| Vue / Vue Router | 3.5.35 / 4.6.4 |
| TypeScript | 6.0.3 |
| Electron / electron-vite | 43.x / 5.x |
| Tailwind CSS | 4.3.3 |
| Vitest / Playwright | 4.1.10 / 1.62.0 |

### 5.2 当前应用与共享层

| 层级 | 当前实现 |
| --- | --- |
| 宿主 | `apps/web` Web Shell；`apps/electron` Electron 主进程与统一 renderer 引导 |
| Renderer | frontend、integration、settings、login、docs |
| 配置单源 | `configs/windows.json` 定义窗口、API base/target、角色、help key 和 preload capability |
| Core | api-client、app-shell、auth/auth-provider、runtime、shell、tenant、sse-events、msw 等 |
| UI | nebula-ui、nebula-layout、nebula-agent、styles |
| Editors | code、DAG、flow、integration panel、low-code form |
| Contracts | 手写领域契约 + OpenAPI 生成快照/facade |
| 正式共享 feature | 只有 `packages/features/use-confirm` |

Electron 与 Web 都消费生成的窗口配置。Electron preload 由统一入口按 capability 组装，子应用通过 `bootMicroApp` 适配 standalone、Web embed 和 Electron 模式。认证会话由 `auth-provider` 统一维护，API client 注入 token 和租户头并处理 401。

### 5.3 已完成的前端重构

- Web/Electron 窗口与 API target 单源化；生成结果有一致性检查脚本。
- `app-shell` 运行时 SDK 与 `nebula-shell` UI 容器已分离。
- 统一 preload、统一微应用启动、统一认证与租户基础能力已建立。
- Integration 已区分 Portal、Provider、Admin 三类界面，并实现资源目录、详情、申请、我的资源/订阅及管理页面。
- Settings 已分为个人、组织、平台入口；Docs 已分产品帮助与开发者参考。
- Login 前端有 credentials、organization、mfa、recovery、success、failure 显式状态模型。
- code-editor 具备独立入口、异步 Monaco provider、单测和 bundle budget；编辑器依赖不再放在基础 UI 包中。
- Playwright 四个 project 的配置真实存在；本次执行 `vp exec playwright test --list` 枚举出 24 项测试（12 mock、10 experience、1 real-stack、1 electron）。

### 5.4 前端剩余问题

#### 生成契约采用不完整

`generate:contracts`、离线 OpenAPI 和 generated facade 已存在，但业务仍使用 `contracts/auth`、`contracts/system`、`contracts/integration` 等兼容手写契约。当前在线文档虽覆盖 132 条路径并声明安全要求，仍有不少操作缺少精确响应体、错误响应与领域约束元数据；生成类型不能替代运行时校验。新增 API 应只通过 facade 暴露，存量需逐域迁移并在 CI 校验差异。

#### feature 边界仍主要留在应用内部

Integration 内已经有 `src/features/plugin-catalog`、`resource-catalog`、`subscription` 等应用内 feature，但 `packages/features` 只有 `use-confirm`。旧计划中声称已创建多个共享 feature 包是不准确的；只有出现多个消费者、稳定 API 和独立测试价值时才应提升为共享包。

#### AuthFlow UI 超前于后端契约

MFA 与恢复步骤是前端状态和交互容器，后端尚无对应事务、验证与恢复 API。前端必须保持不可伪造成功，并在后端契约落地后再接真实提交。

#### Mock 与真实栈边界

MSW 包提供 auth、integration、settings handlers，Mock E2E 适合快速回归。`real-stack` project 明确不允许网络 Mock。2026-08-01 已在三个正式应用上通过登录、Shell、搜索、目录、插件、订阅、Settings 权限页、Monitor、Gateway 和在线契约的最小纵向测试；资源申请、审批、发布、回滚等完整业务链仍属于 W1。

#### 其他增量治理

- Integration 仍是最大业务子应用，页面组合、API、mapper 和 feature 边界需要继续收敛。
- Settings 的实体列表、筛选、批量操作和详情抽屉尚未完全统一。
- 共享类型与本地 `env.d.ts` 仍可继续集中。
- Electron 自动更新模块仍是可插拔占位，不应标记为可发布更新链路。

## 6. 前后端契约与运行边界

`configs/windows.json` 和 Integration proxy 定义三后端目标：

| 路径域 | 目标 |
| --- | --- |
| `/api/platform`、`/api/system`、governance/version/release | `platform-console:8090` |
| 默认 `/api`、认证、租户、订阅、Camel 定义面 | `platform-integration:8080` |
| `/api/executor`、Gateway、执行面 | `platform-integration-executor:8081` |

当前是三进程过渡架构，不应再写成“只启动 platform-console + executor”。正式目标是三平台应用联合运行，demo 仅保留示例用途。

## 7. 当前优先级

| 优先级 | 工作项 | 完成定义 |
| --- | --- | --- |
| 已完成 G0 | 恢复 Platform 与真实栈基线 | ApplicationContext、三应用健康、在线契约和 `vp run test:e2e:real` 已通过 |
| P0 | 真实 DeployTarget | 至少一种资源发布后在 Runtime 生效并可回滚 |
| P1 | 租户强隔离 | 查询/写入都由统一机制强制 tenant 条件，并有跨租户负向测试 |
| P1 | CDC/任务/集群生产化 | 无未授权模拟、共享 offset、唯一调度和故障接管可验证 |
| P1 | 契约消费 | 新 API 100% 经 generated facade；存量按域迁移 |
| P1 | 后端 MFA/恢复 | 先实现安全状态机和契约，再启用前端真实步骤 |
| P2 | 消息、通知、WebSocket、观测 | 跨实例投递、持久化、DLQ 和指标/Trace 后端可验证 |
| P2 | 前端边界治理 | Integration 应用内 feature 成熟后按真实复用提升共享包 |
| P3 | 插件供应链与多库 | 签名/信任链、依赖求解和按需方言扩展 |

## 8. 风险结论

1. **最大交付风险不是缺少模块，而是“结构存在”被误写成“运行通过”。**
2. **Platform Console 与三应用真实栈的 G0 关口已通过，下一前置关口是 W1 的真实 DeployTarget。**
3. **默认日志 DeployTarget、非强制租户 SQL 和可显式启用的 CDC 模拟模式都不能进入生产完成口径。**
4. **前端重构已完成大部分基础设施，下一阶段应优先消除真实契约与真实数据缺口，而不是继续目录搬迁。**
5. **插件远程仓库已是真实实现，旧文档中的 placeholder 结论必须删除；剩余问题是供应链治理。**

## 9. 关联文档

- [模块规划](./模块规划.md)：当前模块树与职责边界。
- [详细开发计划](./nebula-development-detailed-plan.md)：从上述 P0/P1 缺口出发的执行顺序。
- [前端增量重构计划](./nebula-studio-frontend-refactoring-plan.md)：前端专项状态和剩余工作。
- [后端开发状态](../nebula/docs/development-status.md) 与 [后端 backlog](../nebula/docs/implementation-backlog.md)：后端单仓库明细。
- [前端测试](../nebula-studio/docs/testing.md) 与 [后端联调](../nebula-studio/docs/backend-integration.md)：测试拓扑和命令。