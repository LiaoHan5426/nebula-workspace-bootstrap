# Nebula 全栈实现分析与优化规划

> 分析日期：2026-07-10（基于当前代码仓库 spot-check 重写；2026-07-24 补充 `nebula-config` 配置中心专项核实）
>
> 范围：nebula（后端 Java/Spring Boot 平台） + nebula-studio（前端 Vue3/Monorepo）
>
> 前置文档：[模块规划.md](./模块规划.md)、[development-status.md](../nebula/docs/development-status.md)、[implementation-backlog.md](../nebula/docs/implementation-backlog.md)、[development-plan.md](../nebula/docs/development-plan.md)、[详细开发规划](./nebula-development-detailed-plan.md)
>
> **说明**：`development-status.md` / `implementation-backlog.md`（更新至 2026-06-30）已滞后于代码；本文以 2026-07-10 代码实勘为准。旧版分析中多处「已完成」偏乐观，本文已下调。

---

## 一、总体完成度矩阵

### 1.1 后端（nebula）

约 **1066** 个 Java 源文件（camel 300 / security 140 / plugin 97 / capability 77 / system 64 / governance 52 / runtime 52 / database 53 等）。

| 层级         | 模块域                                      | 模块数 | 已完成 | 部分实现 | 待实现/空壳 | 说明                                                           |
| ------------ | ------------------------------------------- | ------ | ------ | -------- | ----------- | -------------------------------------------------------------- |
| 基础         | tools/bom                                   | 2      | 2      | 0        | 0           | 纯工具库 + 版本管理                                            |
| 运行时       | runtime                                     | 6      | 2      | 3        | 1           | core 完整；context/lifecycle/extension 骨架                    |
| 数据与连接   | database/integration                        | 12     | 6      | 5        | 1           | PG/MySQL 元数据可用；S3/Kafka/Mail 有真实客户端；Oracle 空     |
| 能力层       | capability                                  | 9      | 4      | 4        | 1           | cache/lock/storage/log/encrypt 可用；message 默认内存；WS 单机 |
| 安全与租户   | security/tenant                             | 13     | 5      | 6        | 2           | JWT/OAuth/RBAC 可用；租户拦截器弱（不改写 SQL）                |
| 平台核心模型 | resource/governance/release/version-control | 17     | 3      | 9        | 5           | API 链已串；**Deploy 仅打日志**，非生产闭环                    |
| 平台能力域   | config/task/cluster/subscribe               | 22     | 5      | 11       | 6           | Cron/Trigger 可用；DAG/分片未接入执行                          |
| 插件平台     | plugin                                      | 11     | 6      | 3        | 2           | PF4J 本地安装可用；Maven 远程为 placeholder                    |
| Camel集成    | camel                                       | 22     | 12     | 8        | 2           | Console/Executor 可演示；CDC 有 Debezium 但易回落模拟          |
| 系统与业务   | system/modules                              | 12     | 5      | 5        | 2           | user/config/file 可用；organization CRUD 有，租户绑定未齐      |
| 平台应用     | platform                                    | 2      | 1      | 1        | 0           | platform-console 依赖聚合 + OpenAPI；非仅 Health               |
| 演示应用     | demos                                       | 6      | 5      | 1        | 0           | demo-camel-console/executor 为主                               |

**后端结论：**

- **可演示主线**：登录 → 租户 → 接口/订阅 → Gateway 调用 → 监控/治理 → 插件管理（仍以 demo-camel-console :8080 + executor :8081 为主）
- **平台管理入口**：`platform-console` 已通过 starter 依赖聚合 system/resource/governance/release/version/task 等 REST，并暴露 SpringDoc OpenAPI（`scanBasePackages=com.lh`）
- **平台闭环未真正贯通**：Resource → Governance → Version → Release 的进程内 API/状态机已存在，但 `LocalDeployTarget` 仅日志，**无真实 Runtime 部署**
- **文档漂移**：`implementation-backlog.md` 仍写「CDC 仅 Simulated」「console 仅 Health」——均已过时；同时旧版本分析把多项标成「已完成」也偏高

### 1.2 前端（nebula-studio）

| 层次       | 包域                               | 数量 | 状态     | 说明                                                                                                   |
| ---------- | ---------------------------------- | ---- | -------- | ------------------------------------------------------------------------------------------------------ |
| 应用入口   | apps/web, apps/electron            | 2    | 可用     | Web shell + Electron 双入口                                                                            |
| 子应用     | apps/sub-web/\*                    | 5    | 可用     | integration / settings / login / docs / frontend；多数有 README                                        |
| 核心包     | packages/core/\*                   | 10   | 可用     | api-client、app-shell、auth、runtime、shell、sse-events、tenant 均有实现                               |
| UI包       | packages/ui/\*                     | 3    | 可用     | nebula-ui（全量组件，仍含编辑器依赖）、nebula-layout、nebula-agent                                     |
| 编辑包     | packages/editors/\*                | 5    | 参差     | dag/flow/integration-panel/low-code-form 可用；code-editor 导出仍为 stub                               |
| 功能包     | packages/features/\*               | 5    | 多数骨架 | use-confirm 可用；plugin-installer 薄封装；route-designer / subscription-manager / version-diff 仅占位 |
| 基础设施   | internal/\*、tools/\*              | ~5   | 可用     | `defineNebulaConfig` + `standardApiProxy` 已收敛                                                       |
| 类型与契约 | packages/contracts、packages/types | 2    | 管道就绪 | `generate:contracts` + 离线 openapi.json 已有；**业务代码仍用手写 DTO**                                |

**前端结论：**

- Monorepo 结构成熟（Vite+ / pnpm / Vue3 / TypeScript / Tailwind4）
- Shell 嵌入子应用架构清晰：`app-shell`（SDK）与 `shell`（UI 容器）职责已拆分
- **核心不足**：生成契约未被消费、features 包多为骨架、E2E 仅冒烟、nebula-ui 编辑器依赖未拆出

---

## 二、后端缺陷与优化方向

### B-1. 平台核心闭环未真正贯通（P0）[部分实现]

**现状**：Resource / Governance / Version / Release 均有 Entity + Service + REST；协调器可串起申请 → 快照 → 审批 → 流水线状态翻转。

**仍缺**：

- `LocalDeployTarget.deploy/rollback` **仅打日志**，不激活 Route/Plugin/Task
- `ResourceTypeRegistrar` 无各域实现类；Route/Plugin/Task 未自动注册为 Resource
- Governance audit 多为日志；policy 极薄
- Version diff 仅为字符串相等摘要，无结构化差异

**代码入口**：

- `nebula/nebula-resource/resource-registry` — `PersistentResourceRegistry`
- `nebula/nebula-governance/governance-request` — `GovernanceRequestCoordinator`、`DefaultGovernanceService`
- `nebula/nebula-release/release-manager` — `DefaultReleaseManager`、`LocalDeployTarget`
- `nebula/nebula-version-control/version-core` — `PersistentVersionService`

**优化方向**：

1. 实现真实 DeployTarget（对接 Camel Runtime / PluginManager / Task 激活）
2. 各域实现 ResourceTypeRegistrar，统一资源注册
3. Audit 持久化 + Policy 规则引擎补强
4. 结构化 VersionDiff API，供前端 version-diff 包消费
5. 验收测试：至少一种 Resource 走通 Draft → Version → Approval → **真实 Deploy** → Runtime

---

### B-2. CDC 订阅默认仍易回落模拟（P0）[部分实现]

**现状**：`nebula-camel-subscribe` 已有 `DebeziumCdcConnector` / `DebeziumEngineFactory` / `DebeziumCdcRuntimeLauncher` / `CdcOffsetManager`，依赖 `debezium-embedded` + postgres connector。

**仍缺**：

- `TableSubscriberRouteBuilder` 在 Debezium 未启用时走内嵌 `SimulatedCdcProcessor`
- 引擎失败时 `startSimulatedFallback` 仍造假数据
- 与 `nebula-subscribe` 平台模型对齐未验证；无 MySQL CDC connector

**优化方向**：

1. 生产配置强制真实 Debezium，禁止静默 fallback（或明确开关 + 告警）
2. 完善 offset 持久化与断连重连
3. 对齐订阅事件格式到平台 subscribe 模型
4. 按需增加 MySQL connector

---

### B-3. 任务调度：Cron 可用，DAG/分片未接线（P1）[部分实现]

**现状**：`TaskScheduler` + `CronScheduleSupport`（cron-utils）、`TriggerManager`、`TaskScheduleBridge` 可用；platform-console 依赖 `task-starter`。

**仍缺**：

- `DependencyGraph`（task-dependency）有单测，**未接入执行编排**
- `TaskShardManager`（task-cluster）算法存在，**未接入调度执行**
- 与 Camel Executor 手工触发路径并存

**优化方向**：

1. 将 DAG 依赖解析接入 Trigger/Scheduler 主路径
2. 分片与 cluster 活跃节点联动，故障转移
3. 统一调度 REST，收敛 Executor 手工触发入口

---

### B-4. 组织与租户：CRUD 有，SQL 隔离弱（P1）[部分实现]

**现状**：组织树 CRUD + 策略 REST 存在；`TenantContextHolder` / `TenantContextFilter` / `MyBatisTenantInterceptor` 均有类。

**仍缺**：

- `MyBatisTenantInterceptor` **不改写 SQL**，仅检查上下文 / 打 trace
- 租户仓仍有 `InMemoryTenantRepository` 路径
- 组织与租户/授权深度绑定、前端 OrgSwitcher 全链路未齐

**优化方向**：

1. 拦截器真正注入 `tenant_id` 条件（或等价多租户方案）
2. 持久化租户仓 + 组织-租户绑定 REST
3. 前端租户切换后强制刷新各子应用数据

---

### B-5. platform-console 已聚合，统一门面仍弱（P1）[基本可用]

**现状**：依赖聚合 system / governance / resource / release / version / task / subscribe / security / integrations / capabilities；SpringDoc + `SwaggerConfig`；`scanBasePackages=com.lh`。

**仍缺**：

- 无统一 `/api/platform/**` 业务门面（靠组件扫描暴露各模块路径）
- 健康检查 modules 状态硬编码 `"UP"`
- 前端默认基址与 demo :8080 并存，切换策略需明确

**优化方向**：

1. 明确 studio 默认 API 基址切到 platform-console
2. 真实健康聚合（各 starter 探活）
3. 过渡期保持 demo-camel-console 可启动

---

### B-6. 消息与实时通道：有实现，默认偏单机（P2）[部分实现]

| 模块         | 现状                                                              | 缺口                                                          |
| ------------ | ----------------------------------------------------------------- | ------------------------------------------------------------- |
| message      | `InMemoryMessagePublisher` 默认；`KafkaMessagePublisher` 条件装配 | 默认内存；与 InMemory 的 `@ConditionalOnMissingBean` 竞态风险 |
| notification | 内存服务 + Webhook + Mail channel                                 | 无短信；存档仍内存                                            |
| websocket    | 会话/鉴权/路由/心跳较完整                                         | 离线缓冲内存；无集群广播                                      |

**优化方向**：

1. 默认生产配置切 Kafka；理清 Bean 条件优先级
2. WebSocket 集群广播 + 持久离线消息
3. 与 subscribe SSE 统一事件模型

---

### B-7. 多数据库适配：PG + MySQL，Oracle 空（P2）[部分实现]

**现状**：`PostgresqlMetadataProvider`、`MysqlMetadataProvider` 均有；platform-console 当前只依赖 postgres adapter。

**仍缺**：Oracle / SQL Server 适配器；非 PG 的 Flyway schema 清理器。

**优化方向**：按需实现 Oracle；console 可配置引入 mysql adapter；前端数据源页展示多库类型。

---

### B-8. 插件远程仓库为假下载（P3）[本地可用 / 远程骨架]

**现状**：PF4J 本地 `PluginInstallService` 可真实 load/start；Console 插件 REST 可用。

**仍缺**：`MavenRemotePluginRepository.download()` 写入 `"placeholder-jar"`；`search()` 返回空。

**优化方向**：真实 HTTP/Maven 下载 + 仓库索引 + 版本冲突检测；前端插件市场对接。

---

### B-9. 可观测性：monitor 较实，OTel 未接入（P3）[部分实现]

**现状**：`camel-monitor` 有调用日志、拓扑、限流/熔断/白名单 REST；`camel-observability` 为进程内 `RouteTracer`（内存 Map）。

**仍缺**：无 OpenTelemetry / Micrometer 依赖；observability 与 monitor 数据模型未统一。

**优化方向**：可选 OTel 接入；统一拓扑数据存储与前端还原 API。

---

### B-10. Integration 连接层已有真实客户端（P3）[部分实现]

**现状**（相对 6 月 backlog「仅骨架」已前进）：

- S3：真实 `S3Client` + HealthIndicator
- Kafka：真实 `KafkaTemplate` / ConsumerFactory + health
- Mail：真实 `JavaMailSender` + `NebulaMailHelper`

**仍缺**：与 capability-storage / message 的深度整合与生产运维面。

---

### B-11. 集群发现偏单机内存（P2）[部分实现]

**现状**：`ClusterDiscoveryService` 内存注册/心跳；`DistributedLockManager` 注释标明单机内存；与 `task-cluster.TaskShardManager` 存在两套分片概念。

**优化方向**：Redis 分布式锁；K8s/Consul 发现；与 task 执行闭环；收敛重复分片实现。

---

### B-12. nebula-config 配置中心重构（P1）[✅ 2026-07-25 已完成]

> 以下内容记录 2026-07-24 重构前基线。2026-07-25 已完成 basic/center 双模式、启动期 EnvironmentPostProcessor、Spring Cloud Config/Nacos provider、版本监听、文件快照、三种失败策略、白名单刷新及健康检查；实现与用法见 `nebula/docs/config/index.md`。

**重构前现状**：`nebula-config` 更接近“动态配置表 + 本地事件”的基础能力，而不是配置中心客户端或配置中心服务端。

- `config-core` 仅提供 `ConfigService.save/find/delete` 与 `ConfigItem` 模型。
- `config-storage` 提供 `InMemoryConfigRepository` 与 `JdbcConfigRepository`；JDBC 通过 `nebula.config.storage=jdbc` 从 `nebula_config` 表读写配置。
- `config-autoconfigure` 默认装配内存仓库、`DefaultConfigService`、CORS/CSP 过滤器。
- `config-runtime` 的 `ConfigRefreshListener` 目前只记录变更日志；`CorsPolicyManager` / `ContentSecurityPolicyManager` 是偏 Web 安全策略的运行时配置。
- `nebula-module-config`、`nebula-system-config` 与 `nebula-config` 职责交叠：前者偏业务配置管理 REST，后者偏底层动态配置表；文档中“配置中心 REST”容易误导。

**核心问题**：

1. **不是 Spring 启动期配置源**：没有接入 Spring Boot ConfigData / EnvironmentPostProcessor，不能在 Bean 创建前稳定注入外部配置。
2. **没有配置中心语义**：缺少 application/profile/label/namespace/group/dataId、版本、快照、灰度、监听、回滚、权限、审计等核心模型。
3. **启动顺序被业务化管控**：为了先拿数据源、再查配置表、再装配业务 Bean，调用方需要人为控制顺序；这说明配置加载职责没有进入 Spring 配置加载阶段。
4. **远端配置中心缺位**：无 Spring Cloud Config Server、Nacos、Apollo、Consul、Etcd 等 provider 抽象与适配器。
5. **生产默认不安全**：默认内存仓库会掩盖配置丢失；远端失败策略、缓存快照、超时、重试、降级边界均未定义。

**优化方向：双模式配置体系**：

1. **基础模式（basic）**：保持当前流程，但收敛为明确的 `nebula.config.mode=basic`。由架构指定 `DataSource` / `JdbcTemplate`，从指定表加载配置；适合单体、演示、轻量部署。要求通过 Spring Boot 启动期加载入口注入 Environment，而不是业务 Bean 启动后再查表。
2. **中心模式（center）**：`nebula.config.mode=center`，由 `nebula.config.center.provider` 选择远端适配器，首批支持 `spring-cloud-config` 与 `nacos`，后续可扩展 Apollo/Consul/Etcd。配置中心负责启动期拉取、运行期监听刷新、本地快照缓存与失败策略。
3. **统一抽象**：新增 `ConfigSource` / `ConfigProvider` / `ConfigWatcher` / `ConfigSnapshotRepository` / `ConfigMergeStrategy`，屏蔽 JDBC 与远端中心差异。
4. **优先级合并**：建议顺序为 `commandLine > env/system > center/basic external > application.yml > defaults`；多租户/应用维度按 `global -> application -> tenant -> instance` 叠加。
5. **运行期刷新**：配置变更发布统一 `NebulaConfigChangedEvent`，桥接 Spring Cloud Bus / Nacos Listener；只刷新标记为 refreshable 的配置，禁止数据库连接池等 bootstrap 配置无边界热刷。
6. **职责拆分**：`nebula-config` 负责平台配置加载与刷新；`nebula-module-config` 负责业务配置管理 UI/API；`nebula-system-config` 作为系统配置领域模型，不再宣称“配置中心”。

**建议落地关口**：

- G8a：basic 模式下，应用启动前从指定表加载配置并可覆盖 `application.yml`。
- G8b：center 模式下，Spring Cloud Config Server 与 Nacos 至少各完成启动拉取 + 运行期变更监听。
- G8c：配置中心不可用时按 `fail-fast` / `use-snapshot` / `ignore` 策略表现一致，并有启动日志与健康检查。
- G8d：删除旧的顺序管控要求，调用方只声明模式与参数，不再手工编排配置加载顺序。

---

## 三、前端缺陷与优化方向

### F-1. 子应用配置重复（P2）[基本收敛]

**现状**：`internal/vite` 提供 `defineNebulaConfig` + `standardApiProxy`；各子应用 `vite.config.ts` 已是薄包装（约 20–30 行）。

**仍缺**：薄配置仍复制粘贴；integration 保留自定义 SSE proxy（合理）；docs 无 README。

**优化方向**：可选 `createSubWebViteConfig({ root, proxy })` 进一步去重。

---

### F-2. 契约管道已建，业务未消费（P1）[管道完成 / 采用缺口]

**现状**：根脚本 `generate:contracts` → `packages/contracts/generated/platform-api.ts`；离线 `openapi.json` 存在。

**仍缺**：应用仍只 import 手写 `@nebula-studio/contracts/{auth,system,integration}`；生成类型基本无人引用。

**优化方向**：

1. 迁移业务代码到 generated types，或生成覆盖手写目录
2. CI 校验 OpenAPI 变更与 contracts 同步
3. Breaking Change 检测

---

### F-3. 跨子应用状态共享（P2）[基本完成]

**现状**：`shellEventBus`（tenant:changed / auth:logout / theme:changed）；`bootMicroApp` 统一注入。

**仍缺**：settings / login / docs 未像 integration 一样完整 `wireShellEventBus`。

**优化方向**：settings 订阅租户/登出事件并刷新数据。

---

### F-4. Shell 职责边界（P3）[已完成]

`app-shell` = Shell 运行时 SDK；`packages/core/shell` = 应用级 UI 容器。边界已清晰，无需再作为缺陷跟踪。

---

### F-5. 子应用独立性参差（P2）[部分完成]

**现状**：多数子应用有 README + 可独立 `vp`/`filter` 启动；MSW handlers 覆盖 auth/settings/integration。

**仍缺**：docs 缺 README；settings 未接 shell 事件；独立测试夹具不完整。

---

### F-6. 编辑包边界过大（P2）[仍开放]

**现状**：nebula-ui 仍依赖 CodeMirror + TipTap；`packages/editors/code-editor` 公共导出仍为 stub，未真正承接拆分。

**优化方向**：编辑器组件迁出 nebula-ui；修好 code-editor 打包与导出。

---

### F-7. E2E 覆盖不足（P2）[冒烟级]

**现状**：Playwright 有 `g4-smoke` / `g5-smoke` / `theme-switch`；G5 可触达治理相关路由。

**仍缺**：G4 多为 TODO；无登录→租户→订阅 SSE→Gateway 完整路径；无 CI 跑 Playwright。

---

### F-8. 类型声明分散（P3）[仍开放]

`packages/types` 有共享 Window/环境桩；各应用仍保留约 10 个本地 `env.d.ts`。

---

### F-9. features 包多为骨架（P2）[新增跟踪]

`route-designer` / `subscription-manager` / `version-diff` 仅模块常量 + TODO；`plugin-installer` 为薄 fetch 封装。应实现或删除，避免假模块。

---

## 四、前后端协同缺陷与优化方向

### S-1. API 契约自动生成（P0）[管道完成 / 采用缺口]

后端 SpringDoc + 前端 `openapi-typescript` 管道已通；**缺口在消费与 CI 强制同步**（见 F-2）。

---

### S-2. 验收测试不对称（P1）

缺从前端 Playwright 到 platform-console + executor 的端到端验收；无 Resource→Deploy→Runtime 硬验收。

**优化方向**：按 development-plan G5~G10 定义共同验收清单；CI 拉起 console + executor + web。

---

### S-3. 文档同步滞后（P1）

`development-status.md` / `implementation-backlog.md`（2026-06-30）与代码严重脱节；本文已按代码重写，但后端 docs 矩阵尚未同步。

**优化方向**：以本文为基准回写 backlog/status；模块变更同步更新 `nebula/docs/{domain}/`。

---

### S-4. 构建与发布流程不统一（P2）

后端 Maven、前端 pnpm/Vite+；缺统一 Docker Compose（platform-console + executor + frontend + PostgreSQL + Redis）。

---

## 五、阶段规划与关口（修订）

| 阶段   | 主题                | 后端重点                              | 前端重点                        | 协同重点     | 关口  |
| ------ | ------------------- | ------------------------------------- | ------------------------------- | ------------ | ----- |
| Phase1 | 真实闭环 + CDC 硬化 | B-1 真实 Deploy、B-2 禁止静默模拟     | F-2 消费 generated contracts    | S-1/S-2 验收 | G5/G6 |
| Phase2 | 租户隔离 + 任务接线 | B-4 SQL 隔离、B-3 DAG/分片接入、B-12 配置中心双模式 | F-3 settings 事件、F-5 独立文档 | S-3 文档回写 | G7/G8 |
| Phase3 | 统一入口 + 实时通道 | B-5 console 默认入口、B-6/B-11 集群化 | F-7 业务 E2E、F-9 features 落地 | S-4 Compose  | G9    |
| Phase4 | 扩展与完备          | B-7/B-8/B-9/B-10                      | F-6 编辑器拆分、F-8 类型集中    | —            | G10   |
| Phase5 | 持续优化            | 性能、运维面、多库按需                | 体验与包体积                    | 全链路监控   | —     |

---

## 六、关键决策记录

| 决策           | 选项                                        | 推荐                                            |
| -------------- | ------------------------------------------- | ----------------------------------------------- |
| CDC 技术选型   | Debezium Embedded / pgoutput / 自研         | Debezium Embedded（代码已引入；需硬化默认路径） |
| 消息中间件     | Kafka / RabbitMQ / Pulsar                   | Kafka（已有 publisher；默认应切生产配置）       |
| 分布式追踪     | OpenTelemetry / SkyWalking / Zipkin         | OpenTelemetry（尚未接入）                       |
| 前端状态管理   | Pinia / VueUse / 自研事件总线               | VueUse + shellEventBus（已落地）                |
| OpenAPI 生成   | openapi-typescript / swagger-typescript-api | openapi-typescript（管道已有；待业务迁移）      |
| 多数据库优先级 | MySQL > Oracle > 达梦 > 其他                | MySQL 元数据已有；Oracle 按需                   |
| 主管理入口     | demo-camel-console / platform-console       | 过渡期双轨；目标切 platform-console             |
| 配置中心模式   | basic / center                              | 双模式：basic 从指定数据源/表启动期加载；center 对接 Spring Cloud Config Server、Nacos |

---

## 七、风险与缓解

| 风险                            | 影响             | 缓解                           |
| ------------------------------- | ---------------- | ------------------------------ |
| DeployTarget 长期停留在日志桩   | 平台闭环虚假完成 | Phase1 强制真实部署验收        |
| Debezium 静默 fallback 到模拟   | 生产误用假数据   | 配置强制 + 启动告警            |
| 租户拦截器不改 SQL              | 数据串租户       | Phase2 优先硬化                |
| 契约生成但未消费                | 前后端字段漂移   | CI 强制 diff / 迁移手写 DTO    |
| Platform 替代 demo 造成回归     | 演示中断         | 过渡期双入口                   |
| JDK25 + Spring Boot4 生态成熟度 | 依赖兼容         | BOM 锁版本，定期升级验证       |
| Maven 远程插件 placeholder      | 插件市场不可用   | 明确标注骨架，勿对外宣传已完成 |
| nebula-config 误当配置中心使用  | 启动顺序被迫人工管控，生产配置能力不足 | Phase2 引入 basic/center 双模式、启动期加载、远端 provider 与失败策略 |

---

## 八、检查清单

每次迭代完成后核对：

- [ ] 依赖方向：无下层模块逆向引用
- [ ] Starter 单一入口：每个域仅一个 `*-starter`
- [ ] 命名一致：Maven artifactId / Java 根包 / docs 章节三者对齐
- [ ] 演示可回归：demo-camel-console + demo-camel-executor **与** platform-console 均可启动
- [ ] 前端可构建：`vp run build` 无报错
- [ ] API 契约：`generate:contracts` 后业务代码引用 generated（或等价同步）
- [ ] 平台闭环：至少一种 Resource **真实 Deploy** 到 Runtime（非仅状态翻转）
- [ ] CDC：生产配置下无 Simulated fallback
- [ ] 配置中心：basic/center 双模式可验收，且不再要求调用方手工编排配置加载顺序
- [ ] E2E 关键路径：登录 → 租户 → 接口管理 → Gateway 调用
- [ ] 文档：变更后同步 `development-status.md` / `implementation-backlog.md`

---

## 九、相对旧版分析的主要修正

| 旧版声称（约 2026-07-10 实施轮次） | 代码实勘结论                               |
| ---------------------------------- | ------------------------------------------ |
| B-1 平台闭环「已基本贯通」         | API 链有；**Deploy 空壳** → 部分实现       |
| B-2 CDC「已完成」                  | Debezium 有代码；**模拟仍是默认/回退支路** |
| B-3 任务调度「已完成」             | Cron/Trigger 可用；**DAG/分片未接线**      |
| B-4 租户拦截器「已实现」           | 类存在；**不改写 SQL**                     |
| B-8 远程 Maven「已实现」           | **placeholder-jar**                        |
| B-9 Observability「已实现」        | 内存 RouteTracer；**无 OTel**              |
| F-2 契约「已完成」                 | 管道完成；**业务未消费**                   |
| backlog「console 仅 Health」       | **已过时** — 依赖聚合 + OpenAPI 已有       |
| 配置中心 REST「已完成」            | 仅业务/动态配置读写；**nebula-config 尚非配置中心** |

---

> 本文档为 workspace 级规划文件，与 nebula `docs/` 下的 development-plan.md、implementation-backlog.md、development-status.md 形成互补。
> 后端技术细节与分批次计划详见上述文档（需按本文第九节回写同步）。
