# Nebula 全栈当前实现状态分析

> 审查日期：2026-09-08
> 后端基线：`nebula` / `development` / `372f51bfaa8a6b9c9885a1a7fd675e3b9d7923ed`
> 前端基线：`nebula-studio` / `development` / `406671858aeeffe57cf0320ebfd0d1f6ac4e34fd`
> 范围：代码、构建描述符、运行配置、迁移、测试清单及仓库内状态文档。本文不以独立的 PostgreSQL 数据平台方案作为实现证据。

## 1. 审查方法与结论口径

本次审查遵循以下证据优先级：

1. 可执行源码、`pom.xml`、`package.json`、工作区清单；
2. 应用配置、Flyway 迁移、自动配置注册和测试配置；
3. 仓库内 `development-status.md`、`implementation-backlog.md`、测试文档；
4. 历史规划和已完成阶段说明。

“存在接口、类或页面”只证明结构已落地；只有应用启动、目标测试和端到端验收通过后，才标记为运行闭环。
2026-08 期间，系统完成了 G0 可运行基线；随后的 8 月中下旬至 9 月初，全面推进并完成了前端 Module Federation（A 轨）、体验底座与状态规范（B 轨）、低代码全栈平台与双 JVM 读写隔离（C 轨），以及依赖版本与工具链演进（Vite+ 0.3.0、Vitest 5.0、Electron 44、Vue 3.5.42、TanStack Form）。

## 2. 仓库快照

| 项目 | `nebula` | `nebula-studio` |
| --- | --- | --- |
| 分支 | `development` | `development` |
| 审查时工作树 | 干净 | 干净 |
| 主要语言 | Java、SQL、YAML | TypeScript、Vue、CSS |
| 代码规模快照 | 1,200+ 个 `src/main` Java 文件、70+ 个 `src/test` Java 文件 | 1,100+ 个 Git 跟踪文件、38 个 `package.json` |
| 构建体系 | Maven 多模块 | Vite+（`vp`）+ pnpm workspace |
| 生产入口 | 4 个 Spring Boot 平台应用 | 2 个 Host（Web/Electron）+ 4 个核心 Federation Remote |

后端根 Reactor 聚合 22 个顶层条目（含 `demos`），包含 `platform-console`、`platform-integration`、`platform-integration-executor` 以及独立的写安全网关 `platform-low-code-write`。前端工作区全面基于 Module Federation，拆分为 Web/Electron Host，Docs/Settings/Integration/Low-Code Studio Remote，以及 contracts、platform、low-code、editors、ui、testing 分层共享包。

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

当前正式 Reactor 中有四个平台应用：

| 应用 | 端口 | 职责 | 状态口径 |
| --- | --- | --- | --- |
| `platform-console` | 8090 | system、resource、governance、config、version、release、task、plugin 等管理 API、低代码只读 Catalog/Definition 与 OpenAPI | 启动、健康和在线 OpenAPI 通过 |
| `platform-integration` | 8080 | Camel 定义面、认证、租户、订阅、治理 | 启动、健康及登录/Monitor 最小 API 通过 |
| `platform-integration-executor` | 8088 | Gateway、Route、DAG、任务与执行监控 | 启动、健康及 Gateway 最小路径通过（端口由 8081 调整为 8088） |
| `platform-low-code-write` | 8092 | 低代码设计态保存/发布写接口、独立 JVM 与 HSM/PKCS#11 验签保障 | 独立构建与只写网关隔离通过 |

`nebula-platform/platform-admin` 仍保留历史源码和 POM，但已从 `nebula-platform/pom.xml` 的 `<modules>` 中移除，并由目录 README 明确标记为归档，不属于当前 Reactor 或部署拓扑。

`demos/demo-camel-console` (8080) 和 `demos/demo-camel-executor` (8088) 是演示组合，不再作为目标生产入口。

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
| 包管理声明 | `pnpm@11.25.0`；日常命令统一经 Vite+ `vp` |
| Vite+ / Vite | 0.3.0 / 8.2.2（`catalog:vite`） |
| Vue / Vue Router | 3.5.42 / 4.6.4 |
| TypeScript | 6.0.3 |
| Electron / electron-vite | 44.2.0 / 5.0.0 |
| Tailwind CSS | 4.3.3 |
| Vitest / Playwright | 5.0.0 / 1.62.1 |
| 模块联邦 | `@module-federation/vite@1.21.3` + `@module-federation/runtime@0.21.6` |
| 表单验证 | `@tanstack/vue-form@1.33.5` + `zod@4.5.4`（全面替代旧 vee-validate） |

### 5.2 当前应用与共享层

| 层级 | 当前实现 |
| --- | --- |
| 宿主（Host） | `apps/web` Web Shell Host；`apps/electron` Electron 主进程与 Host 窗口管理 |
| 独立 Remote | `sub-web/docs`、`sub-web/settings`、`sub-web/integration`、`remotes/low-code-studio` |
| 验证沙箱 | `apps/mf-poc-host` |
| 配置单源 | `configs/windows.json`（窗口/presentation）、`configs/environments.json`（API targets）、`configs/real-stack.json`、`configs/e2e.json` |
| Platform 底座 | `packages/platform/*`（`api-client`、`application-bootstrap`、`application-contract`、`application-runtime`、`assembly-boot`、`auth`、`federation-protocol`、`host-capabilities`、`i18n`、`login-ui`、`query`、`shell-host`、`shell-protocol`、`state`、`storage`） |
| Low-Code 体系 | `packages/low-code/*`（`compiler`、`contract`、`kit`） |
| UI 与体验 | `packages/ui/*`（`nebula-ui`、`shell-ui`、`tokens`、`nebula-layout`、`nebula-assembly`、`nebula-agent`） |
| Editors | `packages/editors/*`（`code-editor`、`dag-editor`、`flow-editor`、`integration-panel`、`low-code`、`low-code-form`） |
| Contracts | `packages/contracts/*`（`auth`、`common`、`generated`、`integration`、`system`） |
| Testing | `packages/testing/msw` |

### 5.3 已完成的前端 Module Federation 与体系演进

- **A 轨（模块联邦与交付闭环）**：完成 Docs、Settings、Integration、Low-Code Studio 作为 Federation Remote 的独立构建与动态加载；Web 与 Electron 统一为 Host；清理旧微前端嵌套（原 `frontend`、`login` 并入 Host 内置载荷），消除 hall-of-mirrors 双层壳层嵌套；建立 runtime 动态应用注册发现（`/api/system/frontend-apps/runtime`）；完成 `configs/windows.json` 职责拆分；统一构建工具到 `internal/build-kit` 与 `internal/node-kit`。
- **B 轨（体验底座与状态规范）**：完成语义化 Tokens 与 Theme Matrix 契约，支持动态模式与主题色；搭建 Pinia 客户端状态、Vue Query 服务端缓存与 Vue I18n 消息按需装载底座；表单体系整体升级为 `@tanstack/vue-form` 与 `zod`；统一跨宿主 HostCapability 注入。
- **C 轨（低代码全栈闭环）**：完成 LowCodeEditor 交互式画布（跨容器拖放、节点排序、属性与事件检查器、防循环嵌套保护）；实现 `LowCodeCompiler` 生成真实 Vue SFC 运行时；实现低代码只读服务与 `platform-low-code-write` 只写 JVM 隔离、PKCS#11/HMAC 双模式验签、沙箱表达式隔离求值及 SLO 压测基准。

### 5.4 前端剩余关注点

#### 生成契约采用覆盖

`generate:contracts`、离线 OpenAPI 和 generated facade 已存在，但部分存量业务仍依赖 `contracts/auth`、`contracts/system`、`contracts/integration` 等手写契约。随着低代码与新平台 API 扩展，需持续维护 OpenAPI 生成与类型校验的一致性。

#### AuthFlow UI 与安全凭据收口

登录前端已具备完整的 credentials、organization、mfa、recovery 状态模型。后端现行以 JWT/Session/RBAC 为核心，需配合后端安全边界推进持久化多租户隔离与真实 HSM/凭据轮换演练。

#### 真实栈测试与发布演练

`real-stack` 测试项目已可联合后端平台应用及前端 Web/Electron 完成自动化校验。下一阶段重点是真实资源的完整发布闭环（Resource → Approval → Version → DeployTarget → Runtime/Executor）。

## 6. 前后端契约与运行边界

`configs/environments.json` 和 Integration proxy 定义四个平台应用目标：

| 路径域 | 目标 | 职责 |
| --- | --- | --- |
| `/api/platform`、`/api/system`、governance/version/release、低代码只读 | `platform-console:8090` | 平台基础治理与系统元数据 |
| 默认 `/api`、认证、租户、订阅、Camel 定义面 | `platform-integration:8080` | 集成平台与流程治理 |
| `/api/executor`、Gateway、执行面 | `platform-integration-executor:8088` | 运行时路由与网关执行（端口 8088） |
| `/api/low-code/write/**` | `platform-low-code-write:8092` | 低代码独立写网关与安全保障 |

当前为四进程平台架构，加固了低代码写操作的安全围栏。正式目标是平台应用联合运行，`demos/demo-camel-console` (8080) 与 `demos/demo-camel-executor` (8088) 仅保留示例与轻量调试用途。

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