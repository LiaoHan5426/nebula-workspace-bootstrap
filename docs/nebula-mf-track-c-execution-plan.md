# Nebula Module Federation C 轨执行计划

> 依据：`nebula-module-federation-frontend-refactoring-plan.md` v1.2  
> 范围：C 轨（§17 第 25–41 条；Phase 8–12）。不等待再扫 B。  
> 仓库：`nebula-studio`（Compiler / Studio Remote / Editor）+ `nebula`（只读 Definition API + platform-low-code-write 写网关）  
> 开工日：2026-08-23  
> 状态复核：2026-09-08

## 当前进度（2026-09-08）

A/B 轨执行切片已关门。**Phase 8–12 实现已补齐至可部署边界并完成运行加固：**

1. **画布交互与响应式深度修复**：
   - 解决低代码编辑器中组件物料无法加入画布的问题，引入兼容 Vue 响应式 Proxy 的 `cloneDraft` 深度克隆机制，替换在 Chromium/Electron 下报错的 `structuredClone`；
   - 优化物料面板拖放与点击双模态事件响应，避免 Chromium 原生 `draggable` 吞噬点击事件；
   - 完善容器插入目标推导 `resolveInsertParentId`，支持跨容器拖放、同级排序、循环嵌套防护与删除快捷键。
2. **后端写安全与独立写网关**：
   - `platform-low-code-write`（端口 8092）作为独立的写网关 JVM 运行，只开放 `/api/low-code/write/**` 写表面；
   - 支持 PKCS#11 HSM 与 HMAC 验签双模式，完成低代码 API 安全加固与配置隔离（372f51b）。
3. **性能与沙箱保障**：
   - `LowCodeCompiler` 生成真实 Vue SFC 运行时代码；
   - `SandboxFrame` 隔离求值与超时熔断；
   - `vp run soak:low-code` 压测与 Grafana SLO 看板就绪。生产一小时长 soak 与真实硬件 HSM 演练待部署环境最终执行记录。

**审计（low-render）：** `@nebula-studio/nebula-low-render` 仍是 DAG/插件属性表，不是页面 renderer。禁止再写第二套属性表递归器。

Host 仍走 `driver=federation`。`demo-board` 与 `low-code-studio` 共用 `nebula_low_code_studio` Remote。

本轮补齐：palette 和现有节点均可跨容器拖放，阻止循环嵌套；支持同级排序、删除、Enter/Space 选中及方向键排序；Inspector 可编辑可见性、隔离、全部现有 props 和 binding。写操作统一走 `/api/low-code/write/**`。

## 已落地

| ID       | 工作项                                     | 验收                                                                                                                                |
| -------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| C8–C11-1 | 契约 / Compiler / Studio / draft / Catalog | 见上批                                                                                                                              |
| C10-2    | 审批 / 灰度 / 读缓存 / 匿名拒绝            | `requireApproval` → PENDING + `POST .../approve`；`rolloutPercent` + `POST .../gray`；runtime 只读 ACTIVE 缓存；写路径需登录测试    |
| C11-2    | 扫描 / 验签 / Electron lockfile            | Catalog submit/publish 扫描+SHA-256 验签；Electron `low-code-lockfile.json` + `low-code-studio` remote dist                         |
| C12-1    | iframe / 超时表达式                        | `SandboxFrame`/`isolation=iframe` 走 `sandbox=allow-scripts`；`evaluateExpressionIsolated` 超时；故障熔断 `data-lc-sandbox-circuit` |
| C10-3    | 写 API 前缀 + 审批工单 UI                  | `/api/low-code/write`（`write-api-enabled`）；Harness 旁 `ApprovalQueue`；`GET .../versions` + 通过按钮                             |
| C11-3    | HMAC 密钥 / 漏洞工单 / CAS lockfile        | `nebula.low-code.catalog-hmac-key`；`POST .../catalog/advisories`；lockfile `cas` SHA-256 文件图                                    |
| C12-2    | Worker / 遥测 / 第三方 Catalog 关闭        | `expression.worker.ts`（无 Worker 时回退）；`sandboxTelemetry`；`third-party-catalog: false` 默认拒绝非 `trusted://`                |
| C9-2     | Studio 完整设计态交互                      | 跨容器拖放/排序/删除、循环保护、键盘操作、props/binding Inspector                                                                   |
| C10-4    | 独立写 JVM                                 | `platform-low-code-write`；write-only surface；共享 JWT；独立数据库/端口配置                                                        |
| C11-4    | HSM 验签                                   | `LowCodeSignatureVerifier` + JDK PKCS#11 adapter；HMAC 仅保留开发模式                                                               |
| C12-3    | soak / SLO                                 | `vp run soak:low-code`；p95/错误率门槛；Prometheus textfile；Grafana dashboard                                                      |

```text
vp run --filter @nebula-studio/low-code-contract test
vp run --filter @nebula-studio/low-code-compiler test
```

审批：`POST /api/low-code/studio/{app}/publish` 带 `requireApproval: true`，再 `POST .../approve`。灰度：`POST .../gray`。写网关：`GET /api/low-code/write/health`（需登录）。生产 HMAC：环境变量 `NEBULA_LOW_CODE_HMAC_KEY`。

## 部署环境验收队列

- 使用目标厂商 PKCS#11 驱动与真实 HSM key alias 完成联调和轮换演练。
- 对生产地址执行至少一小时 soak，归档 `.prom` 输出和 Grafana 截图；本地测试不得替代该结果。
