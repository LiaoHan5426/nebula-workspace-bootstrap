# Nebula 跨仓库详细开发计划

> 最后更新：2026-08-01
> 代码基线：`nebula@3d35d13`、`nebula-studio@5a36a7e`
> 依据：[当前实现状态分析](./nebula-current-state-analysis.md)。本文只保留尚未完成或需要重新验收的工作，不重复记录已经完成的配置中心、插件主链路和前端 Phase 1–8 历史过程。

## 1. 计划原则

1. 先恢复可运行基线，再扩展功能。
2. “编译通过”“类存在”“Mock 通过”都不能替代真实栈验收。
3. 每个波次交付一个可观察的纵向结果，同时覆盖后端、前端、契约、迁移和测试。
4. 新 API 先定义 OpenAPI/DTO，再修改前后端；前端业务代码经 contracts facade 消费。
5. demo 只用于示例，正式验收使用三个 `nebula-platform` 应用。
6. 所有生产完成项都必须有负向测试：越权、跨租户、失败补偿、重复投递或断连恢复。

## 2. 当前前置阻塞

| 编号 | 阻塞 | 证据 | 影响 |
| --- | --- | --- | --- |
| B0-1 | `platform-console` 历史实跑缺少 `ConfigService` Bean，当前源码有候选装配但未复验 | 后端/前端仓库测试文档记录 2026-07-26 失败；当前 HEAD 未重跑 | 在复验通过前，不能宣称在线 OpenAPI、Settings、Platform API 和 real-stack 已闭环 |
| B0-2 | 默认 `LocalDeployTarget` 只写日志 | `release-manager/.../LocalDeployTarget.java` | 发布状态变化不等于 Runtime 生效 |
| B0-3 | 租户 SQL 不由框架强制 | `tenant-context/.../MyBatisTenantInterceptor.java` | Mapper 漏写条件时可能跨租户读取 |
| B0-4 | 前端 generated contracts 采用不完整 | generated facade 与手写领域契约并存 | 后端变更不能完整触发编译失败 |

## 3. 实施总览

| 波次 | 目标 | 主要交付 | 关口 |
| --- | --- | --- | --- |
| W0 | 恢复可运行基线 | Platform Context、三应用健康、真实栈脚本 | G0 |
| W1 | 真实发布闭环 | Resource → Approval → Version → Deploy → Runtime → Rollback | G1 |
| W2 | 租户与认证边界 | 强制租户隔离、组织绑定、认证契约收敛 | G2 |
| W3 | CDC、任务与集群生产化 | 共享 offset、唯一调度、故障接管 | G3 |
| W4 | 前端真实数据与契约收口 | generated facade、真实 Portal/Settings/Camel 链路 | G4 |
| W5 | 消息、观测与供应链治理 | DLQ、持久通知、跨实例通道、Trace、插件信任 | G5 |

W0 必须最先完成。W1 与 W2 可在 G0 后并行；W3 与 W4 可按契约分片并行；W5 不阻塞核心平台首次可用版本。

## 4. W0：恢复 Platform 与真实栈基线

### 4.1 后端

- [ ] 为 `platform-console` 增加 ApplicationContext 冒烟测试，断言以下 Bean 同时存在：
  - `ConfigRepository`
  - `ConfigService`
  - `ConfigRestController`
  - `DataSource` / `JdbcTemplate`
- [ ] 核对 `config-starter` 到 `config-autoconfigure` 的传递依赖和 `AutoConfiguration.imports`。
- [ ] 明确 `nebula.config.storage=jdbc` 下无 `JdbcTemplate` 时的失败信息，禁止控制器以隐蔽缺 Bean 方式失败。
- [ ] 为 `platform-integration`、`platform-integration-executor` 增加最小 Context 冒烟，覆盖各自关键 starter。
- [ ] 清理或归档未进入 Reactor 的 `nebula-platform/platform-admin`，避免模块清单继续漂移。
- [ ] 将被 Git 跟踪的明文数据库/外部服务凭据迁到环境变量或受控 Secret，并完成凭据轮换；测试只使用无敏感信息的默认值。

### 4.2 前端与编排

- [ ] 保持 `scripts/e2e/run-real-stack.ps1` 使用三个正式平台应用，不退回 demo 掩盖问题。
- [ ] 服务启动后逐个验证 8090、8080、8081 健康端点。
- [ ] 从在线 8090 OpenAPI 重新生成契约，并执行生成文件差异检查。
- [ ] 失败日志继续按 Platform/Integration/Executor/Web 分域保存。

### 4.3 G0 验收

```text
后端目标 Context 测试通过
  → 三应用启动并健康
  → Web 启动
  → 在线契约生成无漂移
  → vp run test:e2e:real 通过
```

不得通过跳过 8090、关闭健康检查或启用 MSW 完成 G0。

## 5. W1：真实资源发布闭环

### 5.1 先选一个资源类型

首个纵向切片推荐 Camel Route/API，不同时处理 Route、Plugin 和 Task。该资源必须具备：

- 稳定 `resourceId`、租户和版本；
- 可持久化草稿与快照；
- 可审批发布；
- 可部署到 Executor；
- 可查询运行状态；
- 可回滚到上一版本。

### 5.2 后端工作

- [ ] 实现领域 `ResourceTypeRegistrar`，把目标 Camel 资源注册到统一 Resource Registry。
- [ ] 为目标类型实现真实 `DeployTarget`，调用 Executor/Runtime，而不是日志桩。
- [ ] Release 状态只在 Runtime 确认成功后进入成功态；失败时记录原因并执行补偿。
- [ ] Version diff 输出结构化字段变化，不只返回字符串相等摘要。
- [ ] 审批、发布、回滚、Runtime 状态使用同一关联 ID 和审计事件。
- [ ] 增加幂等、并发发布、Executor 不可用和回滚失败测试。

### 5.3 前端工作

- [ ] Provider 页面支持草稿、版本、提交审批和发布状态。
- [ ] Admin 页面支持审批、失败原因和审计查看。
- [ ] Portal 只展示已发布且当前用户可访问的资源。
- [ ] 发布进度来自真实后端状态，不使用前端计时器模拟。
- [ ] 版本详情和 diff 经 generated contracts facade 映射为 ViewModel。

### 5.4 G1 验收

单租户下完成：创建资源 → 生成版本 → 提交审批 → 审批通过 → 部署到 Executor → Gateway 调用成功 → 回滚 → 行为恢复。数据库、审计和 Runtime 状态必须一致。

## 6. W2：租户、组织与认证边界

### 6.1 强制租户隔离

- [ ] 选定统一方案：SQL AST 改写、MyBatis-Plus TenantLine，或强制租户 Mapper 生成/静态规则。
- [ ] 查询、更新、删除和批量操作都必须覆盖 `tenant_id`，不能只检查 SELECT。
- [ ] 对平台级表建立显式豁免清单，默认不豁免。
- [ ] TenantContext 在异步任务、Camel Exchange、SSE 和审计事件中传播并在结束时清理。
- [ ] 建立 tenant-a 访问 tenant-b 数据的负向集成测试。

### 6.2 组织与租户

- [ ] 持久化组织、成员、租户和角色绑定，消除默认内存仓库路径对生产配置的影响。
- [ ] `switch-org` 后重新计算组织、租户和权限，不只修改前端本地状态。
- [ ] Shell 切换组织/租户后广播事件，业务子应用清理服务端状态缓存并重新请求。

### 6.3 Token 与 Web 安全

- [ ] 生产路径禁用查询参数 Token，只接受安全的 Authorization Header 或受控 Cookie。
- [ ] 将 Token 撤销/会话失效状态迁移到可跨节点共享且带 TTL 的存储。
- [ ] CORS 使用环境化 Origin 白名单；携带凭证时禁止任意 Origin Pattern。
- [ ] 确认 OAuth2 是否进入产品范围；如需要，应显式装配、持久化密钥与客户端并完成联调；如不需要，应把模块标记为可选实验能力。

### 6.4 MFA 与恢复的正确顺序

当前后端没有 MFA/TOTP/恢复实现。该能力不应与 W0/W1 混入，建议作为 W2 后半段独立纵向切片：

1. 定义预认证事务和稳定错误码；
2. 任何 MFA/组织步骤完成前不得签发最终 Token 或建立认证 Session；
3. 首期实现 TOTP 与一次性恢复码；
4. 再实现邮箱密码恢复和全会话撤销；
5. 最后把前端现有 AuthFlow 的 mfa/recovery 容器接到真实 API。

### 6.5 G2 验收

- 跨租户读写全部被拒绝；
- 组织切换后前后端上下文一致；
- 未完成的认证事务不能访问受保护 API；
- 若 MFA 子切片尚未排期，前端继续禁止伪造成功。

## 7. W3：CDC、任务与集群生产化

### 7.1 CDC

- [ ] 生产配置固定 `allowSimulatedFallback=false`，启动失败直接失败并告警。
- [ ] 模拟模式只允许开发/测试 profile，并在 UI 显示明确的“模拟”状态。
- [ ] offset 从单机文件迁移到共享、带租户/订阅作用域的存储。
- [ ] 增加单活租约、断线重连、重复事件幂等和接管测试。
- [ ] 将 CDC 事件格式与平台 subscribe 模型统一。

### 7.2 任务与集群

- [ ] 把 `DependencyGraph` 接入 Scheduler/Trigger 主路径。
- [ ] 把 `TaskShardManager` 与共享 Node Registry 和租约联动。
- [ ] 保证 Cron 在多实例下唯一触发；节点故障后可恢复或接管。
- [ ] 任务实例、日志、重试和最终状态持久化。
- [ ] 收敛通用 Task 与 Camel Executor 手工触发的重复入口。

### 7.3 G3 验收

双 Executor 场景下：真实 PostgreSQL WAL 事件不重复丢失；Cron 只触发一次；主节点停止后备用节点接管；日志和 offset 可追溯。

## 8. W4：前端真实数据与契约收口

### 8.1 契约

- [ ] 在线 OpenAPI 覆盖 Auth、Platform、System、Governance、Version、Release、Camel 关键域。
- [ ] 业务只从 `@nebula-studio/contracts` facade 导入，不直接依赖 generated 文件路径。
- [ ] 新 API 禁止新增重复手写 DTO；存量按 Auth → Platform/System → Integration 顺序迁移。
- [ ] CI 执行生成、diff 和 breaking-change 检查。

### 8.2 页面与 feature

- [ ] Portal 的目录、详情、申请、进度、接入信息全部使用真实 API。
- [ ] Settings 的用户、角色、权限、组织、应用统一 EntityList/详情模式，但不在无批量事务 API 时伪造原子批量操作。
- [ ] Integration 页面只负责路由与组合；API、mapper、状态机留在应用内 feature。
- [ ] 只有出现至少两个真实消费者时，才把 app-local feature 提升到 `packages/features`。
- [ ] Login 的 MFA/恢复步骤只在后端契约可用后启用提交。

### 8.3 G4 验收

- Mock、experience、electron 保持稳定；
- real-stack 覆盖登录、工作台、资源目录、申请、Settings、插件、订阅、Gateway、Monitor；
- 后端字段变化能在契约生成、TypeScript 编译或 E2E 中失败；
- 网络面板确认真实栈没有 MSW/page.route 业务响应。

## 9. W5：生产化增强

### 9.1 消息与实时通道

- Kafka publisher/consumer 自动配置、幂等、重试和 DLQ；
- 通知记录持久化，WebSocket/SSE 跨实例广播并保证一次可达语义；
- 消息、订阅、通知统一事件标识和审计上下文。

### 9.2 可观测性

- 统一 camel-monitor 与 observability 数据模型；
- 指标和 Trace 从进程内 Map 迁移到可查询后端；
- 评估 OpenTelemetry/Micrometer，建立跨 8090/8080/8081 的关联 ID。

### 9.3 插件供应链

- JAR 签名、可信供应商和密钥轮换；
- 平台版本兼容范围与依赖约束求解；
- 私有 Maven/Nexus/Artifactory 搜索适配；
- 安装、升级、回滚和运行时加载的端到端测试。

### 9.4 G5 验收

多实例环境下消息可追踪、通知可恢复、Trace 可跨进程关联；受信插件可从远程仓库安装、运行和回滚，不受信制品被拒绝。

## 10. 验证命令

### 后端

```bash
# 目标模块测试；具体 -pl 列表按改动收窄
mvn -pl <module> -am test

# 三平台应用构建
mvn -pl nebula-platform/platform-console,nebula-platform/platform-integration,nebula-platform/platform-integration-executor -am package
```

长期运行应用时，应从各应用模块目录启动，或使用显式 `-f`，避免 `spring-boot:run` 绑定父 POM。

### 前端

```bash
vp check
vp run test
vp run build
vp run test:e2e:mock
vp run test:e2e:experience
vp run test:e2e:electron
vp run test:e2e:real
```

### 每个关口的最小证据

- 命令和退出码；
- 目标提交 SHA 与工作树状态；
- 测试报告和失败日志路径；
- 数据库/Runtime 状态证据；
- 生成契约 diff；
- 不包含密码、Token、API Key 或连接串明文。

## 11. 文档同步

每完成一个关口：

1. 更新 `../nebula/docs/development-status.md` 与 `implementation-backlog.md`；
2. 更新 `../nebula-studio/docs/testing.md`、`backend-integration.md` 及受影响应用 README；
3. 更新本目录的 [当前实现状态分析](./nebula-current-state-analysis.md)；
4. 只有模块职责或 Reactor 变化时才更新 [模块规划](./模块规划.md)；
5. 记录真实测试日期，不把历史通过数量冒充当前提交的执行结果。
