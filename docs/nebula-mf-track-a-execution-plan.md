# Nebula Module Federation A 轨执行计划

> 依据：`nebula-module-federation-frontend-refactoring-plan.md` v1.2  
> 范围：仅 A 轨（§17 第 1–16 条）。不等待 B/C。  
> 仓库：`nebula-studio`（前端）+ `nebula`（Phase 3 registry）  
> 开工日：2026-08-22  
> 状态复核：2026-09-08

## 当前进度（2026-09-08）

A 轨 Phase 0–7 主路径已全面落地并稳定运行。近期持续加固完成：

1. **统一 AppDock / Chrome Catalog 引导机制**：将 `SHELL_CHROME_CATALOG` 与应用发现引导抽入 `@nebula-studio/app-shell`，并在 Electron 主进程早启动阶段与 Web 宿主同步调用，彻底解决 Electron 与 Web 端集成应用卡片数量不一致、单卡片行宽溢出及视图生命周期失步问题；
2. **构建与依赖链升级**：完成 Vite+ 0.3.0、Vite 8.2.2、Vitest 5.0.0、Electron 44.2.0、pnpm 11.25.0 升级；
3. **测试验证**：`vp run test:e2e:real`（复用 Console/Integration/Executor 8088 真实服务）与 `vp run test:e2e:electron` 已通过；Host 初始同步 JS gzip 维持在 35 KiB 左右；§17 涉及 A 轨条目全部关门。

**历史保留项复评：** A-R1 已完成：`apiTargets`、real-stack、E2E patterns 分别迁至 `configs/environments.json`、`configs/real-stack.json`、`configs/e2e.json`，生成器/Vite/real-stack 脚本读取拆分配置并通过 schema 校验。目录改名没有运行时收益；`bootMicroApp` 是受限的 standalone/Host composition API且 Federation 已禁止调用；每请求 CSP nonce 属部署网关职责。

## 复评实施结果

| ID   | 工作项                 | 验收                                                                                                                                                          |
| ---- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A-R1 | 配置职责拆分（已完成） | `configs/windows.json` 只保留 shell/Electron renderer/preload/presentation；三个拆分配置均有 schema；生成器、Vite proxy、OpenAPI、soak、real-stack 脚本已切换 |

A-R1 已完成且不要求删除 `bootMicroApp`、改目录名或等待 B/C。

已落地切片（按刀，下文保留）：

已完成 Phase 0–2 A 加载路径（Web `/?embed=docs`、Electron 文档窗口/iframe）。Docs Federation **不再调用 bootMicroApp**；standalone 仍用 `boot.ts`。

Phase 3 第一刀已落地：`FrontendApplication` 表 + `GET /api/system/frontend-apps/runtime`。

Phase 3 第二刀：Web/Electron Federation 加载走 runtime API。`windows.json` 仍描述 Electron 窗口、非 federation embed、`apiTargets`。

Phase 3 第三刀：`V014` 把 workspace / settings / integration 以 `driver=native` 写入 runtime；Host 侧栏与应用集成网格 overlay runtime 元数据。

Phase 4 第一刀：Settings 导出 `./application`，Web/Electron 经 runtime Federation 加载；Host 不再静态依赖 `@nebula-studio-renderer/settings`。standalone 仍用 `boot.ts`。外观页走 Host `theme.setScheme`，不直接 import electron-bridge。已人工验证。

Phase 5 第一刀：Integration 导出 `./application`，runtime `driver=federation`（`V016`），Web/Electron 动态加载。Host 不再静态依赖 `@nebula-studio-renderer/integration`。standalone 仍用 `boot.ts`。已人工验证三种访问路径。

Phase 5 第二刀：Integration Host 嵌入走 capabilities（token / 租户 / 登出事件）。standalone `/login` **复用 Login 子应用**（单一 UI），不复制登录页。Federation 入口不 import Login。

Phase 5 第三刀：BPMN / DAG / Monaco / VXE 经 editor 包 `defineAsyncComponent` 从 Remote 制品加载（MF 会忽略 `manualChunks`）。Host 源码与依赖不引用这些运行时。已人工验证：管理员侧栏「流程定义 / DAG 编排」、BPMN 起步图、DAG 编辑器打开、Host CSP 可加载 Remote 字体。

Phase 5 第四刀：Web 嵌入 E2E（`#/flows`、`#/dag`）已通过 `vp run test:e2e:mock`（15 passed）。同时修正 Settings 嵌入路径为 `/?embed=settings`，去掉 `networkidle`。

Phase 6 第一刀：Host `/?embed=login` 走 `bootHostLogin`，只挂载共享 `login/app`。

Phase 6 第二刀：Host Web 工作台走 `bootHostWorkspace`，只挂载共享 `main/app`；不再调用 `main/boot`。

Phase 6 第三刀：Electron 工作台 / 登录 renderer 走 Host `bootHostWorkspace` / `bootHostLogin`，不再 glob `frontend`/`login` 的 `main.ts`。`windows.json` 窗口、preload、login modal 映射保留。已人工验证登录加载。

Phase 6 第四刀：删除 generated Web embed `login-entry`；login `webLoad=host`；Host boot 显式传入 runtime mode。standalone 仍可 `detectRuntimeMode`。已完成代码落地。

Phase 6 第五刀：`@nebula-studio/msw` 迁到 `packages/testing/msw`；`vp run check:boundaries` 锁定 Host/Remote/platform 禁止依赖与 `detectRuntimeMode` 调用范围。

Phase 6 第六刀：`@nebula-studio/nebula-shell` 迁到 `packages/ui/shell-ui`。包名不变；不拆 app-shell，不删 assembly-boot。

Phase 6 第七刀：抽出 `@nebula-studio/shell-protocol`（embed 消息、事件总线、presentation 标记）。`app-shell` 再导出；Host 实现仍留 app-shell。

Phase 6 第八刀：`bootMicroApp` 不再调用 `installWebPresentation`；Host/standalone composition root 安装 Web stub 并显式 `installShellHostBridge`。runtime 改依赖 `shell-protocol`。不删 fake `window.electron`，不删 assembly-boot。

Phase 6 第九刀：`@nebula-studio-renderer/assembly-boot` 迁到 `packages/platform/assembly-boot`。包名不变；不把 overlay 并进 Host，不删 fake `window.electron`。

Phase 6 第十刀：Web/Electron 适配从 `app-shell` 迁到 `@nebula-studio/shell-host`。Host 与 standalone `boot.ts` 安装；Federation 入口不 import。

Phase 6 第十一刀：删除 `detectRuntimeMode`；Web 不再伪造 `window.electron`（只装 `window.api`）；`windows.json` 去掉 label/category 等业务字段，离线回退用 `shellChromeCatalog`。`apiTargets` 仍留在 `windows.json`。

Phase 6 第十二刀：runtime mode 迁到 `shell-protocol`；Federation / assembly-boot 不再依赖 `@nebula-studio/runtime`；删除 app-shell 协议 shim 与 auth-provider 登录再导出。`bootMicroApp` 仍作 standalone/Host 兼容 adapter。

Phase 6 第十三刀：Remote / nebula-layout / auth 不再依赖 `app-shell` 会话与 embed helper；实现迁到 `shell-protocol` 与 `auth-provider`。`bootMicroApp` 仍编排 auth + electron-bridge。`windows.json` 仍含 `apiTargets`。不批量改名 `apps/sub-web`。

Phase 4/5 E2E：补 standalone Playwright（三 Remote 独立源）、Host mock 隔离/恢复（manifest 失败不影响 login/shell）、real-stack 覆盖 docs/`#/flows`/runtime registry、Electron 切 docs 后回到 shell。`vp run test:e2e:real` 脚本入口已恢复。

Phase 1 lint 边界：Host/Remote 禁止依赖与 `window.api`/`electron` 探测改 ESLint；`check-boundaries.mjs` 只留结构性锁。

Phase 1 node-kit 第一刀：窗口配置生成下沉 `@nebula-studio-internal/node`；根 `generate-window-configs.mjs` 只编排。目录不改名。

Phase 1 node-kit 第二刀：运行时地址漂移扫描下沉 `runtimeAddressDrift.mjs`；`check-generated.mjs` 仍编排 generate + stale 对比。不改名、不迁 `check-boundaries`。

Phase 1 node-kit 第三刀：`GENERATED_STANDALONE_APPS` / `GENERATED_FEDERATION_DEV_ENTRIES` 写入 contracts generated；Electron 与 `frontendRuntime` 不再手写 5174/5176/5177。

Phase 3 第四刀：`ensureFrontendApplicationOpenApi` 把 runtime/管理 DTO 写入 generated OpenAPI；Host 经 mapper 消费 `FrontendRuntimeEntryView`。

Phase 7 第一刀：registry `iframe` / `external` 进入应用集成网格。iframe 同域 `/iframe-guest.html` + origin/nonce/MessageChannel（仅 `ping`）；external `window.open` 且无 capabilities。不写入 `windows.json`。已人工验证 Web/Electron。

Phase 7 第二刀：Federation 加载超时 + last-known-good + 熔断；`rolloutPercent=0` 不进 runtime；Host CSP 增加 `frame-src 'self'`。

Phase 7 第三刀：http(s) manifest SRI（runtime 下发 `integrity`，打包协议跳过）；Host 遥测 POST `/api/system/frontend-apps/telemetry`；熔断/SRI 失败且存在上一版本时自动回滚；Electron `nebula-remote://` / `file:` 钉死 extraResources，不从 HTTP 自动更新。

Phase 7 第四刀：manifest 公钥信封签名（`nebula-sig-v1`，ECDSA P-256 / Ed25519）；runtime 只下发信封不含私钥；空签名跳过；失败走 LKG 并记 `signature_mismatch`。不进入 Phase 8 低代码。

Phase 7 第五刀：`IframeCapabilityBridge` 协议 v1 协商、ping payload schema、请求超时/取消、unmount dispose。方法白名单仍仅 `ping`。

Phase 7 第六刀：Host CSP 收紧 `base-uri` / `object-src` / `form-action`，`frame-src` 允许 loopback 跨源 iframe；runtime 下发 `allowedOrigins`（禁止 `*`）；种子 `iframe-cross-demo`。Vite `host: true` 同时服务 `127.0.0.1`。已人工验证。

Phase 7 第七刀：生产 Host 才启用 script nonce。`vp run dev:web` 的 HTML 源码仍含 `script-src 'unsafe-inline'`（HMR）。构建时 Vite `html.cspNonce = NEBULA_CSP_NONCE`，并删除 script `unsafe-inline`。占位符可由前置网关按请求替换；本刀不实现网关。

Phase 1 CSS/bundle 收口：删除 `theme.css` 对 `packages/`、`apps/` 的全仓库 `@source`。`nebulaTailwindSourcePlugin` 按制品依赖图注入 `@source`，构建写出 `nebula-css-source-report.json`。`configs/bundle-baseline.json` + `check:bundle` 记录 Host 初始 gzip 与 Remote JS gzip；CI 在 `build:federation-remotes` 后强制 Remote 预算。

## 原则

1. Phase 0 是真实 Remote 迁移前的硬门槛；失败则停，不进入 Docs。
2. 不批量改现有 `apps/sub-web` 目录，不删除 standalone，不把全部依赖改成 shared。
3. Phase 0 使用 Hello / synthetic Remote，不使用 Docs/Settings/Integration。
4. CSS 隔离失败时 A 轨暂停；Shadow DOM 或替代实现必须通过同一测试后才能进 Docs。
5. 现有 `vp run dev` / `vp run dev:web` 必须保持可用。

## 阶段顺序（只列 A）

| 顺序 | 阶段           | 本仓库动作                                                                    | 退出后再做                         |
| ---- | -------------- | ----------------------------------------------------------------------------- | ---------------------------------- |
| 0    | Phase 0 硬门槛 | Hello Remote、poc Host、cssNamespace、双 expose                               | 才允许 Docs                        |
| 1    | Phase 1 A      | application-contract 补全、build-kit Host/Remote 配置、shared policy、harness | 示例 Remote 双入口 + 静态 registry |
| 2    | Phase 2 A      | Docs 导出 `./application`，Web/Electron 动态加载，删 embed                    | Host 可不重建接入兼容 Docs         |
| 3    | Phase 3        | `nebula` FrontendApplication registry API                                     | Host 不再读前端仓库业务注册表      |
| 4    | Phase 4 A      | Settings 经 capabilities，独立制品                                            | Host 不静态依赖 Settings           |
| 5    | Phase 5 A      | Integration 去 login、capabilities/api-client、独立制品                       | Host 产物不含 Integration chunk    |
| 6    | Phase 6 A      | Frontend/Login 并入 Host，删 embed/runtime glue                               | 依赖图满足计划第 12 节交付边界     |
| 7    | Phase 7        | iframe/external、CSP、LKG、灰度                                               | 三种 driver 可配置接入且互不拖垮   |

## Phase 0 本轮落地（当前提交目标）

| ID   | 工作项                                                                | 验收                                                                           |
| ---- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| P0-1 | 锁定 `@module-federation/vite` / runtime；最小 `application-contract` | 包可安装、类型可 import                                                        |
| P0-2 | `apps/remotes/hello`：standalone + `./application`                    | `vp run --filter @nebula-studio-renderer/hello dev/build`                      |
| P0-3 | `apps/mf-poc-host`：静态 registry + Runtime `registerRemotes`         | 浏览器打开 poc Host 能 mount Hello                                             |
| P0-4 | `hello` + `hello-style-b` 相反 `.poc-box` 颜色；cssNamespace 插件     | 交换加载顺序后 computed style 不变                                             |
| P0-5 | `hello-dual` 暴露 `./application` 与 `./runtime-application`          | `vp run check:mf-poc` 已通过：runtime sync JS 不含 `NEBULA_POC_DESIGNER_ONLY`  |
| P0-6 | 记录 Vite+/HMR/CSP 实测                                               | `apps/mf-poc-host/POC-NOTES.md`                                                |
| P0-E | Electron：dev URL + packaged 同布局（`mf-poc://`，非生产 shell）      | `electron … --check`；窗口：`dev:mf-poc:electron` / `dev:mf-poc:electron-file` |

下一阶段：Phase 1 A 收尾后进入 Phase 2 Docs（仍不改生产业务路由以外的 Host 加载试点）。

## Phase 1 A 本轮落地

| ID   | 工作项                                                         | 验收                                                          |
| ---- | -------------------------------------------------------------- | ------------------------------------------------------------- |
| P1-1 | application-contract / host-capabilities / application-runtime | 包可 import；harness 测 mount/unmount                         |
| P1-2 | `createNebulaSharedConfig` 单源                                | vue singleton；contract shared；vue-router 可选且非 eager     |
| P1-3 | `defineNebulaHostConfig` / `defineNebulaRemoteConfig`          | Hello + poc Host 改用这两入口                                 |
| P1-4 | 静态 registry loader                                           | poc Host 走 `registerStaticRemotes` + `mountFederationRemote` |
| P1-5 | bootMicroApp 兼容                                              | 不新增 MF 调用方                                              |

```text
vp run check:federation
vp run check:mf-poc
```

## Phase 1 A 本轮落地（node-kit 第一刀）

把 `windows.json` 校验与 TS 制品生成从根脚本下沉到 `@nebula-studio-internal/node`。本刀不改名为 `internal/node-kit`，不把 `check-boundaries` / bundle / drift 一并迁走。

| ID   | 工作项                   | 验收                                                                                            |
| ---- | ------------------------ | ----------------------------------------------------------------------------------------------- |
| P1-6 | window-config 进 node 包 | `internal/node/src/windowConfig.mjs`；根脚本只 write + `vp fmt`                                 |
| P1-7 | 可测核心逻辑             | `joinOrigin`、端口冲突、生成常量有 vitest；`vp run --filter @nebula-studio-internal/node test`  |
| P1-8 | 边界锁定                 | `check:boundaries` 禁止根脚本内联 Ajv/`validateConfig`/`joinOrigin`                             |
| P1-9 | 不做                     | 目录改名 node-kit；迁 `check-boundaries.mjs`；OpenAPI generated contract；app-shell 实现迁 Host |

```text
node ./scripts/check-boundaries.mjs
node ./scripts/generate-window-configs.mjs
vp run --filter @nebula-studio-internal/node test
```

## Phase 1 A 本轮落地（node-kit 第二刀）

把运行时地址漂移扫描从 `check-generated.mjs` 下沉到 `@nebula-studio-internal/node`。本刀不改目录名，不迁 `check-boundaries` / bundle budget。

| ID    | 工作项           | 验收                                                                                      |
| ----- | ---------------- | ----------------------------------------------------------------------------------------- |
| P1-10 | drift 进 node 包 | `internal/node/src/runtimeAddressDrift.mjs`；根脚本只 generate + stale 对比 + 调用扫描    |
| P1-11 | 可测扫描         | 硬编码 loopback 报错、allowlist 跳过；`vp run --filter @nebula-studio-internal/node test` |
| P1-12 | 边界锁定         | `check:boundaries` 禁止根脚本内联 `scanRuntimeAddressDrift` / 地址正则                    |
| P1-13 | 不做             | 目录改名 node-kit；迁 `check-boundaries.mjs`；OpenAPI generated contract；bundle budget   |

```text
node ./scripts/check-boundaries.mjs
vp run --filter @nebula-studio-internal/node test
```

## Phase 1 A 本轮落地（node-kit 第三刀）

standalone / federation 开发入口从 `windows.json` 生成进 `@nebula-studio/contracts/generated`。Electron 与 `frontendRuntime` 不再手写 5174/5176/5177。本刀不把 `windows.json` 业务元数据迁出，不改 OpenAPI DTO。

| ID    | 工作项                       | 验收                                                                                        |
| ----- | ---------------------------- | ------------------------------------------------------------------------------------------- |
| P1-14 | generated federation entries | `GENERATED_FEDERATION_DEV_ENTRIES` + `GENERATED_STANDALONE_APPS` 出现在 `api-namespaces.ts` |
| P1-15 | 消费方改引用                 | Electron allowedOrigins 与 `LOCAL_FEDERATION_FALLBACKS` 来自 generated                      |
| P1-16 | 边界锁定                     | `check:boundaries` 禁止上述两文件出现 `localhost:517`                                       |
| P1-17 | 不做                         | 迁出 label/category；OpenAPI FrontendApplication contract；改名 node-kit                    |

```text
node ./scripts/generate-window-configs.mjs
node ./scripts/check-boundaries.mjs
vp run --filter @nebula-studio-internal/node test
vp run --filter @nebula-studio/application-runtime test
```

## Phase 1 A 本轮落地（lint 边界）

把 Host/Remote **禁止依赖 / 禁止 import / 禁止探测 host globals** 从根脚本改到 ESLint。`check-boundaries.mjs` 只保留 lint 表达不了的结构性锁（必有依赖、已删路径、OpenAPI 制品、generate 脚本必须走 node kit）。不改名 `node-kit`，不迁 bundle budget，不跑 real-stack E2E。

| ID    | 工作项                          | 验收                                                                            |
| ----- | ------------------------------- | ------------------------------------------------------------------------------- |
| P1-18 | `host-boundary` 覆盖 Remote src | 除 Frontend `App.vue` 外，sub-web 业务源码禁止 `window.api` / `window.electron` |
| P1-19 | `mf-boundary`                   | Remote/Host/platform `package.json` 与 import 矩阵；`windows.json` 禁止业务字段 |
| P1-20 | 瘦身 `check-boundaries`         | 不再扫 import / detectRuntimeMode / fake `window.electron`                      |
| P1-21 | 不做                            | 改名 node-kit；real-stack E2E；CSP nonce 网关                                   |

```text
node ./scripts/check-boundaries.mjs
vp run lint:eslint
```

## Phase 1 A 本轮落地（Tailwind @source + bundle 证据）

删除共享 `theme.css` 的全仓库扫描；每个 Host/Remote 只扫描本 app `src` 与 workspace 依赖。Host 初始 gzip 与 Remote JS gzip 写入 `nebula-bundle-report.json`，上限在 `configs/bundle-baseline.json`。本刀不迁 design token / 视觉规则（B 轨）。

| ID    | 工作项                   | 验收                                                           |
| ----- | ------------------------ | -------------------------------------------------------------- |
| P1-22 | 去掉 repo-wide `@source` | `theme.css` 不含 `../../../packages` / `../../../apps`         |
| P1-23 | 按制品注入 `@source`     | `nebulaTailwindSourcePlugin`；Docs 图不含 Integration/Settings |
| P1-24 | CSS source report        | 生产构建写出 `dist/nebula-css-source-report.json`              |
| P1-25 | bundle 量化证据          | `check:bundle` 记录 Host 初始 gzip；Remote 预算可开关强制      |
| P1-26 | 不做                     | 改名 node-kit / build-kit；B 轨 token/截图；Phase 8            |

```text
vp run check:css-sources
vp run --filter @nebula-studio-internal/vite test
vp run build:web
vp run build:federation-remotes
vp run check:bundle
```

## 本轮目录

```text
nebula-studio/
├── packages/platform/application-contract/
├── packages/platform/host-capabilities/
├── packages/platform/application-runtime/
├── packages/platform/federation-protocol/  # Electron 自定义协议：MIME、CORS、publicPath 改写
├── apps/mf-poc-host/                 # Phase 0 Web Host 车辆，不改生产 shell 路由
├── apps/remotes/hello/
├── apps/remotes/hello-style-b/
├── apps/remotes/hello-dual/
└── internal/vite/src/federation/     # poc 配置 + cssNamespace
```

生产 `apps/web` / Electron 从 `GET /api/system/frontend-apps/runtime` 解析 Docs remote；API 不可达时才回退本地 `:5176` / `nebula-remote://docs/`。Electron renderer 对 Docs 不再 glob `main.ts`。

## Phase 2 A 本轮落地

| ID   | 工作项                            | 验收                                                     |
| ---- | --------------------------------- | -------------------------------------------------------- |
| P2-1 | Docs `./application` + standalone | `vp run --filter @nebula-studio-renderer/docs dev/build` |
| P2-2 | Web Host 动态加载                 | `vp run dev:web` + Docs Remote，`/?embed=docs`           |
| P2-3 | Electron 动态加载                 | renderer 排除 Docs glob；dev URL / `nebula-remote://`    |
| P2-4 | 删除 `docs-entry.ts`              | Web 无静态 Docs embed 入口                               |
| P2-5 | Federation 不走 bootMicroApp      | `federation.ts` 直接 mount；`boot.ts` 仅 standalone      |

```text
vp run check:docs-mf
vp run check:federation
```

Electron 联调：先起 Docs Remote，再 `vp run dev`，打开文档窗口/页签。

## Phase 3 本轮落地

| ID   | 工作项                                      | 验收                                                                  |
| ---- | ------------------------------------------- | --------------------------------------------------------------------- |
| P3-1 | `FrontendApplication` / `Version` 表 + seed | Flyway `V013`；Docs `driver=federation` → `:5176/mf-manifest.json`    |
| P3-2 | runtime + CRUD/validate/rollout API         | `GET /api/system/frontend-apps/runtime` 含 docs，同 id 覆盖 ShellApp  |
| P3-3 | origin allowlist + contractVersion          | validate 不发外网；非 allowlist host 拒绝                             |
| P3-4 | Host 消费 runtime 加载 Federation           | Web/Electron Docs 主路径不再用仓库硬编码 remote entry                 |
| P3-5 | native catalog seed + Host 侧栏 overlay     | runtime 含 docs/main/settings/integration；网格仍有集成、侧栏仍有设置 |

```text
GET  /api/system/frontend-apps/runtime
GET  /api/system/frontend-apps
POST /api/system/frontend-apps
POST /api/system/frontend-apps/{id}/versions
POST /api/system/frontend-apps/{id}/validate
PUT  /api/system/frontend-apps/{id}/rollout
```

下一刀：Phase 4 Settings 独立 Remote。不要删 `windows.json` 的 Electron 窗口 / preload / embed / `apiTargets`。

## Phase 3 本轮落地（第四刀）

`FrontendApplicationRestService` 方法返回 `void`，springdoc 不会产出响应 schema。生成契约时由 `@nebula-studio-internal/node/frontend-openapi` 写入 `FrontendRuntimeEntryView` 等 schema。本刀不改 Java 返回类型、不进 Phase 8。

| ID   | 工作项                        | 验收                                                                                |
| ---- | ----------------------------- | ----------------------------------------------------------------------------------- |
| P3-6 | OpenAPI schema 进入 generated | `openapi.json` 含 `/api/system/frontend-apps/runtime` 与 `FrontendRuntimeEntryView` |
| P3-7 | facade + mapper               | `GeneratedFrontendRuntimeEntryView`；`mapFrontendRuntimeEntryFromGenerated`         |
| P3-8 | Host 消费 mapper              | `fetchFrontendRuntimeEntries` 映射 generated view                                   |
| P3-9 | 不做                          | 把 RestService 改成非 void；网关 CSP nonce；app-shell 实现迁 Host                   |

```text
node ./scripts/generate-contracts.mjs --file=packages/contracts/generated/openapi.json
node ./scripts/check-boundaries.mjs
vp run --filter @nebula-studio-internal/node test
vp run --filter @nebula-studio/application-runtime test
```

## Phase 4 A 本轮落地

| ID   | 工作项                                  | 验收                                                         |
| ---- | --------------------------------------- | ------------------------------------------------------------ |
| P4-1 | Settings `./application` + standalone   | `vp run --filter @nebula-studio-renderer/settings dev/build` |
| P4-2 | runtime `driver=federation`             | Flyway `V015`；`:5177/mf-manifest.json`、`nebula_settings`   |
| P4-3 | Web/Electron 动态加载                   | `/?embed=settings`；Electron glob 排除 settings `main.ts`    |
| P4-4 | 删除 settings embed entry               | Web 无 `@nebula-studio-renderer/settings` 静态依赖           |
| P4-5 | capabilities 替 electron-bridge（外观） | `theme.setScheme`；不引入 B 轨完整主题/i18n                  |

```text
vp run check:settings-mf
vp run --filter @nebula-studio-renderer/settings dev
```

联调：重启 Integration 跑 V015，先起 Settings Remote `:5177`，再刷新 `vp run dev:web`，打开设置。已人工验证。

## Phase 5 A 本轮落地（第一刀）

| ID   | 工作项                                   | 验收                                                                                                                                                          |
| ---- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P5-1 | Integration `./application` + standalone | `vp run --filter @nebula-studio-renderer/integration dev/build`                                                                                               |
| P5-2 | runtime `driver=federation`              | Flyway `V016`；`:5174/mf-manifest.json`、`nebula_integration`                                                                                                 |
| P5-3 | Web/Electron 动态加载                    | `/?embed=integration`；Electron glob 排除 integration `main.ts`                                                                                               |
| P5-4 | 删除 integration embed entry             | Web 无 `@nebula-studio-renderer/integration` 静态依赖                                                                                                         |
| P5-5 | standalone 登录复用 Login 子应用         | `/login` → `login/app`；Federation 入口不 import Login                                                                                                        |
| P5-6 | auth/tenant/SSE token 走 capabilities    | Host capabilities + api-client adapter；租户/登出事件可 reload                                                                                                |
| P5-7 | 编辑器独立制品（BPMN/DAG/Monaco/VXE）    | Remote dist 含运行时（async chunk）；Host 源码/依赖不引用。已人工验证                                                                                         |
| P5-8 | Web 嵌入 E2E                             | `vp run test:e2e:mock` 15 passed（含 `#/flows`、`#/dag`、Settings `/?embed=settings`）                                                                        |
| P5-9 | Electron / standalone / real-stack E2E   | `vp run test:e2e:standalone`；mock `remote-isolation`；real-stack 扩 docs/`#/flows`/runtime；Electron 切 docs 后回 shell。真实后端仍走 `vp run test:e2e:real` |

```text
vp run check:integration-mf
vp run --filter @nebula-studio-renderer/integration dev
vp run test:e2e:mock
```

联调：重启 Integration 控制面跑 V016，先起 Integration Remote `:5174`，再刷新 `vp run dev:web`，打开应用集成 / `/?embed=integration`。

## Phase 6 A 本轮落地

Login 首期并入 Host auth feature，避免 Remote 加载失败时无法登录。不把 Login 做成 Federation Remote。

| ID   | 工作项                                          | 验收                                                                                                                     |
| ---- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| P6-1 | Host 拥有 `/?embed=login` 入口                  | `login-entry` → `bootHostLogin`；只 import `login/app`；`vp run check:login-host`                                        |
| P6-2 | Integration / Settings standalone 仍复用同一 UI | 不复制第二套登录页；Federation 入口仍不 import Login                                                                     |
| P6-3 | Electron 登录窗映射暂不删                       | `windows.json` 的 login renderer / preload / modal 保留                                                                  |
| P6-4 | Host 拥有 Web 工作台入口                        | 已验收：未登录 `/` → `/?embed=login`；登录后工作台正常；`vp run check:host-workspace`                                    |
| P6-5 | Electron frontend/login renderer 迁 Host        | renderer 不 glob `main.ts`；走 `bootHostWorkspace` / `bootHostLogin`；`vp run check:login-host` / `check:host-workspace` |

Host 工作台 / 登录入口已验收。不要删 `windows.json` 的窗口 / preload / `apiTargets`。

## Phase 6 A 本轮落地（第四刀）

删除 Web 生成 embed 入口与 Host 对 `detectRuntimeMode()` 的依赖。standalone Remote 仍可自动检测。不批量改 `apps/sub-web` 目录，不删 Electron 登录窗映射，不拆 Web fake `window.electron` stub（Shell IPC 仍需要）。

| ID   | 工作项                     | 验收                                                                                            |
| ---- | -------------------------- | ----------------------------------------------------------------------------------------------- |
| P6-6 | 删除 generated login embed | 无 `apps/web/src/embed/login-entry.ts`；`web-boot` 直接 `bootHostLogin('platform-embed')`       |
| P6-7 | login `webLoad=host`       | `windows.json` 不再写 `webEmbedEntry`；manifest `embedBootEntries` 为空；`/?embed=login` 仍可用 |
| P6-8 | Host 显式 runtime mode     | `bootHostLogin` / `bootHostWorkspace` 必填 mode；Host 源码不含 `detectRuntimeMode`              |
| P6-9 | 不做                       | 批量改名 `apps/sub-web`；删除 Web presentation stub；拆 app-shell / 删除 assembly-boot          |

```text
vp run check:login-host
vp run check:host-workspace
vp run check:generated
vp run --filter @nebula-studio-internal/vite test
```

不要删 `windows.json` 的窗口 / preload / `apiTargets`。

Electron 联调：`vp run dev`（electron#dev），确认主窗口工作台与登录 BrowserWindow 仍可用。Web：`vp run dev:web` 工作台与 `/?embed=login` 不变。

## Phase 6 A 本轮落地（第五刀）

把测试夹具移出 `packages/core`，并用仓库脚本锁定 Host/Remote 依赖边界。本刀不迁移 `nebula-shell` / app-shell，不删 `detectRuntimeMode` standalone 用法，不实现 scripts→node-kit。

| ID    | 工作项                        | 验收                                                                                                       |
| ----- | ----------------------------- | ---------------------------------------------------------------------------------------------------------- |
| P6-10 | MSW 迁 `packages/testing/msw` | 包名仍为 `@nebula-studio/msw`；无 `packages/core/msw`；workspace 含 `packages/testing/*`                   |
| P6-11 | `check:boundaries`            | Host 生产依赖不含 docs/settings/integration；Remote 不含 Host/Electron/sibling remotes；platform 不含 apps |
| P6-12 | `detectRuntimeMode` 范围      | 仅 `packages/core/runtime/**` 与 `apps/sub-web/*/src/{boot,main}.ts`（及对应测试）                         |
| P6-13 | 不做                          | 拆 app-shell；删除 assembly-boot；OpenAPI generated contract；real-stack E2E；网关 CSP nonce               |

```text
vp run check:boundaries
vp run check:federation
```

## Phase 6 A 本轮落地（第六刀）

把 Shell Vue UI 移出 `packages/core`。包名保持 `@nebula-studio/nebula-shell`。本刀不拆 `app-shell`、不迁 assembly-boot、不改 Host boot。

| ID    | 工作项                 | 验收                                                                                       |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------ |
| P6-14 | `packages/ui/shell-ui` | 无 `packages/core/shell`；`check:boundaries` 锁定路径；chunk 规则认 `packages/ui/shell-ui` |
| P6-15 | 不做                   | 把 Web/Electron 实现迁进 Host；删除 `apps/sub-web/assembly-boot`；B 轨样式合并             |

```text
node ./scripts/check-boundaries.mjs
```

## Phase 6 A 本轮落地（第七刀）

抽出无宿主假设的 shell 协议。`app-shell` 继续再导出，现有 `@nebula-studio/app-shell` 调用方不用改。Web/Electron 桥接、窗口 manifest、auth helper 仍留在 `app-shell`。不删 assembly-boot。

| ID    | 工作项                             | 验收                                                                                                |
| ----- | ---------------------------------- | --------------------------------------------------------------------------------------------------- |
| P6-16 | `packages/platform/shell-protocol` | 包名 `@nebula-studio/shell-protocol`；无 vue / electron / app-shell 依赖                            |
| P6-17 | app-shell 兼容再导出               | `app-shell` 依赖 protocol；embed 消息 / event bus / presentation 标记从 protocol 再导出             |
| P6-18 | 不做                               | 把 Web/Electron 实现文件迁进 apps/web、apps/electron；删除 assembly-boot；删除 fake window.electron |

```text
node ./scripts/check-boundaries.mjs
```

## Phase 6 A 本轮落地（第八刀）

composition root 拥有 Web stub 与 `ShellHostBridge` 注入。`bootMicroApp` / `@nebula-studio/runtime` 不再依赖 `app-shell`。实现类仍在 `app-shell`（standalone 不能 import Host）。不删 fake `window.electron`，不删 assembly-boot。

| ID    | 工作项               | 验收                                                                                          |
| ----- | -------------------- | --------------------------------------------------------------------------------------------- |
| P6-19 | runtime 去 app-shell | `packages/core/runtime` 依赖 `shell-protocol`；`bootMicroApp` 不调用 `installWebPresentation` |
| P6-20 | Host 显式安装        | `bootHostWorkspace` 调 `installShellHostBridge` + `installWebPresentationUnlessElectron`      |
| P6-21 | 不做                 | 实现迁进 apps/web；把 assembly overlay 并进 Host；删除 fake `window.electron`                 |

```text
node ./scripts/check-boundaries.mjs
node ./scripts/check-host-workspace.mjs
node ./scripts/check-login-host.mjs
```

## Phase 6 A 本轮落地（第九刀）

把共享 boot 适配器移出 `apps/sub-web`。包名保持 `@nebula-studio-renderer/assembly-boot`。本刀不把 overlay 并进 Host，不删 fake `window.electron`。

| ID    | 工作项                            | 验收                                                                           |
| ----- | --------------------------------- | ------------------------------------------------------------------------------ |
| P6-22 | `packages/platform/assembly-boot` | 无 `apps/sub-web/assembly-boot`；`check:boundaries` 锁定路径                   |
| P6-23 | 不做                              | 并入 host-capabilities / ui/overlays；改 npm 包名；删除 fake `window.electron` |

```text
node ./scripts/check-boundaries.mjs
```

## Phase 6 A 本轮落地（第十刀）

把 app-shell 的 Web/Electron 实现文件迁到共享包 `@nebula-studio/shell-host`（`packages/platform/shell-host`）。standalone 不能 import `@nebula-studio/web`，因此不把适配器源码放进 `apps/web`。`app-shell` 不依赖 `shell-host`，避免环。本刀不删 fake `window.electron`，不删 standalone `detectRuntimeMode`，不迁 `windows.json` 业务元数据。

| ID    | 工作项                         | 验收                                                                                          |
| ----- | ------------------------------ | --------------------------------------------------------------------------------------------- |
| P6-24 | `packages/platform/shell-host` | Host/standalone boot 从 `shell-host` 安装 presentation 与 `ShellHostBridge`                   |
| P6-25 | 边界锁定                       | `app-shell` 无 `installWebPresentation.ts`；Federation `federation.ts` 不 import `shell-host` |
| P6-26 | 后续刀                         | 删除 fake `window.electron`；删除 `detectRuntimeMode`；迁 `windows.json` label/category       |

```text
node ./scripts/check-boundaries.mjs
node ./scripts/check-host-workspace.mjs
node ./scripts/check-login-host.mjs
vp run --filter @nebula-studio-renderer/main test
```

## Phase 6 A 本轮落地（第十一刀）

删除 standalone 自动探测运行模式、Web 伪造的 Electron globals，并把窗口业务元数据迁出 `windows.json`。本刀不改名为 `internal/node-kit`，不补 real-stack E2E，不把 `apiTargets` 迁到 environments。

| ID    | 工作项                      | 验收                                                                                                                     |
| ----- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| P6-27 | 删除 `detectRuntimeMode`    | 无 `detectMode.ts`；Host/standalone `main.ts` 显式 `mode`；`bootMicroApp` 必填 mode                                      |
| P6-28 | 删除 fake `window.electron` | `installWebPresentation` 只写 `window.api`；composable 经 `resolveRendererIpc()`；Remote 用 `stampFederationRuntimeMode` |
| P6-29 | 迁出业务元数据              | `windows.json` 窗口无 label/category；离线回退 `shellChromeCatalog`；生成物无业务字段                                    |
| P6-30 | 不做                        | 迁 `apiTargets`；目录改名 node-kit；real-stack E2E；CSP nonce 网关                                                       |

```text
node ./scripts/check-boundaries.mjs
node ./scripts/check-host-workspace.mjs
node ./scripts/check-login-host.mjs
vp run --filter @nebula-studio-renderer/main test
vp run --filter @nebula-studio/runtime test
vp run --filter @nebula-studio-internal/node test
vp run --filter @nebula-studio/nebula-shell test
```

## Phase 6 A 本轮落地（第十二刀）

按目标包图拆重叠：runtime mode 属于无宿主协议，不属于 `bootMicroApp` 聚合包。本刀不删除 `bootMicroApp`，不把 Remote 的 `app-shell` 会话/embed 依赖一并拆完，不迁 `apiTargets`。

| ID    | 工作项                    | 验收                                                                  |
| ----- | ------------------------- | --------------------------------------------------------------------- |
| P6-31 | mode 迁 `shell-protocol`  | `requireRuntimeMode` / `stampFederationRuntimeMode` 不在 runtime 源码 |
| P6-32 | Federation 不依赖 runtime | `federation.ts` 不 import `@nebula-studio/runtime`                    |
| P6-33 | assembly-boot 去 runtime  | 只依赖 `shell-protocol` 的 `RuntimeMode`                              |
| P6-34 | 删除 app-shell 协议 shim  | 无 `presentationHost.ts` 等再导出文件；index 直接再导出 protocol      |
| P6-35 | 停止 auth 登录再导出      | Login / frontend 从 `auth-provider/backend` 导入                      |
| P6-36 | 不做                      | 删除 `bootMicroApp`；Remote 去 `app-shell`；迁 `apiTargets`           |

```text
node ./scripts/check-boundaries.mjs
node ./scripts/check-host-workspace.mjs
node ./scripts/check-login-host.mjs
vp run --filter @nebula-studio-renderer/main test
vp run --filter @nebula-studio/runtime test
vp run --filter @nebula-studio/shell-protocol test
```

## Phase 6 A 本轮落地（第十三刀）

把 Remote / layout 从 `app-shell` 会话与 embed 实现上拆开。`app-shell` 继续再导出给 Host / Frontend / Electron 窗口配置。本刀不删除 `bootMicroApp`，不迁 `apiTargets`，不批量改名 `apps/sub-web`，不动 B 轨 styles/Pinia/i18n。

| ID    | 工作项                     | 验收                                                                                                |
| ----- | -------------------------- | --------------------------------------------------------------------------------------------------- |
| P6-37 | embed/layout 协议          | `WEB_SHELL_EMBED_QUERY` / layoutHost 在 `shell-protocol`；无 app-shell `webAuth.ts`/`layoutHost.ts` |
| P6-38 | Web 会话 helper            | `handleShellAuthUnauthorized` 等在 `auth-provider/web`                                              |
| P6-39 | Remote 去 app-shell        | docs/settings/integration 源码与生产依赖不含 `@nebula-studio/app-shell`                             |
| P6-40 | layout / auth 去 app-shell | nebula-layout 与 `@nebula-studio/auth` 不依赖 app-shell                                             |
| P6-41 | 不做                       | 删除 `bootMicroApp`；迁 `apiTargets`；批量改名 `apps/sub-web`；B 轨 styles/Pinia/i18n               |

```text
node ./scripts/check-boundaries.mjs
node ./scripts/check-host-workspace.mjs
node ./scripts/check-login-host.mjs
vp run --filter @nebula-studio/shell-protocol test
vp run --filter @nebula-studio/auth-provider test
vp run --filter @nebula-studio/auth test
vp run --filter @nebula-studio/nebula-layout test
vp run --filter @nebula-studio/nebula-shell test
```

## Phase 7 本轮落地（第一刀）

iframe / external 由 backend registry 配置；失败不得拖垮 federation。本刀不做 CSP nonce 收紧、LKG、灰度百分比。

| ID   | 工作项                          | 验收                                                                  |
| ---- | ------------------------------- | --------------------------------------------------------------------- |
| P7-1 | iframe driver + 同域 guest      | Flyway `V017` `iframe-demo`；Host 加载 `/iframe-guest.html`           |
| P7-2 | origin + nonce + MessageChannel | `connectIframeCapabilityBridge`；方法白名单仅 `ping`；禁止 `*` origin |
| P7-3 | external driver                 | `external-demo` 绝对 loopback URL；`window.open`；不注入 capabilities |
| P7-4 | 不写入 `windows.json`           | Electron chrome IPC 仍只认窗口 ID；runtime ID 在 renderer 合并        |
| P7-5 | 后续刀（本刀不做）              | CSP / SRI / LKG / 灰度 / 遥测                                         |

```text
vp run check:iframe-driver
vp run --filter @nebula-studio/host-capabilities test
vp run --filter @nebula-studio/application-runtime test
```

联调：重启 Integration 跑 V017，刷新工作台，「应用集成」出现 iframe 示例 / 外部链接示例。iframe 握手失败只 `console.warn`，不卸载 Shell。Electron renderer 必须把 `apps/electron/public` 设为 Vite `publicDir`，否则 `/iframe-guest.html` 会回退成工作台。登录后需重新 hydrate runtime（Electron 登录窗不整页刷新）。

## Phase 7 本轮落地（第二刀）

失败隔离：单 Remote 超时/失败不得拖垮 Shell；有 last-known-good 时回退；连续失败打开熔断。灰度：`rolloutPercent<=0` 从 runtime 列表剔除；1–99 由 Host 按租户+用户稳定分桶。

| ID    | 工作项                      | 验收                                                      |
| ----- | --------------------------- | --------------------------------------------------------- |
| P7-6  | Federation load timeout     | `mountFederationRemote` 15s 超时，错误留在 embed iframe   |
| P7-7  | last-known-good + circuit   | 成功写入 LKG；失败先试 LKG；3 次失败/10min 熔断 5min      |
| P7-8  | rolloutPercent              | runtime 省略 0%；Host `isInRolloutCohort`                 |
| P7-9  | Host CSP `frame-src 'self'` | Web/Electron Host 明确同域 iframe；跨源 iframe 仍后续刀   |
| P7-10 | 后续刀（本刀不做）          | SRI/签名、remote telemetry、Electron packaged remote 更新 |

```text
vp run check:remote-resilience
vp run check:federation
```

## Phase 7 本轮落地（第三刀）

Host 失败隔离之上补齐治理闭环：SRI、遥测入库、有上一版本时自动回滚、打包 Remote 禁止 HTTP 热更新。私钥签名校验本刀仍不做（`signature` 列仅管理端存储）。

| ID    | 工作项                | 验收                                                                                       |
| ----- | --------------------- | ------------------------------------------------------------------------------------------ |
| P7-11 | http(s) manifest SRI  | runtime 可下发 `integrity`；不匹配则当 live 失败并走 LKG；`nebula-remote://` 跳过          |
| P7-12 | remote telemetry      | `POST /api/system/frontend-apps/telemetry`；失败不得拖垮 mount                             |
| P7-13 | 灰度自动回滚          | `circuit_open` / `integrity_mismatch` 且存在上一版本 → 当前 `ROLLED_BACK`、上一版 `ACTIVE` |
| P7-14 | Electron packaged pin | `packagedRemoteUpdatePolicy`；`electron-builder.yml` extraResources                        |

```text
vp run check:remote-resilience
vp run check:federation
```

重启 Integration 跑 Flyway `V018`。本地 demo 种子没有 `integrity`，SRI 为跳过。自动回滚需要至少两个版本，不会把唯一的 docs/settings/integration 版本打成 0%。

## Phase 7 本轮落地（第四刀）

第三刀留下的私钥验签：Host 用 Web Crypto 校验 `nebula-sig-v1` 公钥信封（对 manifest 字节签名）。私钥永不进 runtime / Flyway。本地种子仍为空，与 SRI 一样跳过。

| ID    | 工作项                 | 验收                                                                 |
| ----- | ---------------------- | -------------------------------------------------------------------- |
| P7-15 | 公钥信封格式           | `nebula-sig-v1;alg=ECDSA-P256-SHA256\|Ed25519;pk=…;sig=…`            |
| P7-16 | Host 校验              | http(s) 拉取一次 body：先 SRI 再签名；打包协议跳过；失败当 live 失败 |
| P7-17 | runtime 下发 signature | 不含私钥；`signature_mismatch` 可触发自动回滚                        |
| P7-18 | 不做                   | Phase 8 低代码；CSP nonce；跨源 iframe                               |

```text
vp run check:remote-resilience
vp run check:federation
```

## Phase 7 本轮落地（第五刀）

补齐 iframe 桥运行治理，不扩大 capability 面：仍禁止 token / API client；`external` 仍无桥。

| ID    | 工作项             | 验收                                                                        |
| ----- | ------------------ | --------------------------------------------------------------------------- |
| P7-19 | 协议版本协商       | Host/guest `protocolVersion=1`；其它版本握手失败，不降级 `postMessage('*')` |
| P7-20 | method/schema      | 仅 `ping`；payload 必须为空且 structured-cloneable                          |
| P7-21 | timeout / cancel   | 请求默认 4s 超时；`cancel` 拒绝 in-flight；迟到 response 丢弃               |
| P7-22 | dispose            | Shell unmount / iframe reload 关闭 port；guest 处理 `dispose`               |
| P7-23 | 后续刀（本刀不做） | 生产 CSP nonce 插件、Phase 8 低代码                                         |

```text
vp run check:iframe-driver
vp run --filter @nebula-studio/host-capabilities test
```

## Phase 7 本轮落地（第六刀）

跨源 iframe 与静态 Host CSP。Vite Web 仍需 `script-src 'unsafe-inline'`（HMR）；不把 nonce + unsafe-inline 当成真实 nonce。HTML meta CSP 才是浏览器强制策略。

| ID    | 工作项                 | 验收                                                                                                 |
| ----- | ---------------------- | ---------------------------------------------------------------------------------------------------- |
| P7-24 | Host CSP               | `base-uri 'self'`、`object-src 'none'`、`form-action 'self'`；`frame-src 'self' localhost/127.0.0.1` |
| P7-25 | runtime allowedOrigins | `FrontendRuntimeEntry.allowedOrigins`；Host 拒绝不在名单的 iframe origin；禁止 `*`                   |
| P7-26 | 跨源种子               | Flyway `V019` `iframe-cross-demo`；loopback 端口对齐；Vite `host: true` 同时服务 127.0.0.1           |
| P7-27 | 后续刀（本刀不做）     | 生产 script nonce 插件、Phase 8                                                                      |

```text
vp run check:iframe-driver
vp run check:remote-resilience
vp run --filter @nebula-studio/application-runtime test
```

重启 Integration 跑 Flyway `V019`。联调：Host 用 `http://localhost` 打开，「跨源 iframe 示例」iframe `src` 为 `http://127.0.0.1:<HostPort>/iframe-guest.html`，握手 `ready`。Web/Electron Vite 需 `host: true`，否则 Windows 上 `localhost` 常只绑 `::1`，`127.0.0.1` 会连接拒绝。顶层直接打开 guest 仍为 `waiting`。

## Phase 7 本轮落地（第七刀）

生产 Host 才启用 script nonce。`vp run dev:web` 的 HTML 源码仍含 `script-src 'unsafe-inline'`（HMR）。构建时 Vite `html.cspNonce = NEBULA_CSP_NONCE`，并删除 script `unsafe-inline`。占位符可由前置网关按请求替换；本刀不实现网关。

| ID    | 工作项                    | 验收                                                                        |
| ----- | ------------------------- | --------------------------------------------------------------------------- |
| P7-28 | 生产 nonce 插件           | `nebulaHostCspNoncePlugin`；仅 `command === 'build'`                        |
| P7-29 | 去掉 script unsafe-inline | 生产 CSP `script-src` 含 `'nonce-NEBULA_CSP_NONCE'`，不含 `'unsafe-inline'` |
| P7-30 | 不做                      | 每请求轮换 nonce 的网关；Phase 8 低代码                                     |

```text
vp run check:remote-resilience
vp run --filter @nebula-studio-internal/vite test
```

## A 轨收口（§17.8 / 9 / 16 / 14，不做 CSP 网关）

产品运行时离开 `internal`：Electron `findMonorepoRoot` 在 `federation-protocol`；CSS 产品入口 `@nebula-studio/styles/{document,remote}`。删除 app-shell / runtime 协议再导出，保留 `bootMicroApp`。Federation 只用无 preflight 的 remote CSS，`cssNamespace` 打在 mount 容器，Host 拒绝重复 namespace。包数与重复 boot 写入 `configs/package-inventory.json`。

| ID     | 工作项              | 验收                                                                                                         |
| ------ | ------------------- | ------------------------------------------------------------------------------------------------------------ |
| A-8    | internal 运行时边界 | Electron 无 internal/node 生产依赖；apps/packages 禁止 runtime 引用                                          |
| A-9    | 重叠删除            | app-shell/runtime 不再导出协议；调用方直连 shell-protocol                                                    |
| A-16   | 生产 CSS 分层       | Federation `styles/remote`；容器级 appearance；重复 namespace 拒绝                                           |
| A-14   | 包库存              | `vp run check:inventory`；Host gzip 仍走 `check:bundle`                                                      |
| A-skip | 复评后保留          | CSP nonce 网关（部署职责）；目录改名（无收益）；删除 bootMicroApp（仍有 standalone/Host composition 消费者） |

```text
vp run check:boundaries
vp run check:css-sources
vp run check:inventory
vp run --filter @nebula-studio-internal/vite test
vp run lint:eslint
vp run build:web
vp run build:federation-remotes
vp run check:bundle
```

## 命令（目标）

```text
vp run --filter @nebula-studio-renderer/hello dev
vp run --filter @nebula-studio/mf-poc-host dev
vp run check:mf-poc
vp run check:federation
vp run dev:mf-poc:electron
vp run dev:mf-poc:electron-file
```
