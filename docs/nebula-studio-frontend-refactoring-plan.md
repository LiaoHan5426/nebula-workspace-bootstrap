# Nebula Studio 前端架构现状与增量重构计划

> 文档版本：v3.2（架构演进与装配层设计参考）
> 最后更新：2026-09-08
> 代码基线：`nebula-studio@406671858aeeffe57cf0320ebfd0d1f6ac4e34fd`
> 架构演进说明：本文记录了 v3.x 阶段装配层 `nebula-assembly`、配置单源与宿主适配的设计与实现背景。随着后续 Module Federation 架构的全面落地，前端架构已进一步升级为 Host/Remote 模型：原 `bootMicroApp`、`sub-web/frontend`、`sub-web/login` 已被 Host 内置载荷（`@nebula-host-boot/workspace`、`@nebula-host-boot/login`）与 `@nebula-studio/application-bootstrap` 显式生命周期替代；最新跨仓库重构规划以 [Nebula 前端 Module Federation 架构重构计划](./nebula-module-federation-frontend-refactoring-plan.md) 及其 A/B/C 轨执行计划为准。

## 1. 当前结论

Nebula Studio 已完成宿主、窗口配置、preload、认证、运行时、基础布局、主要产品界面和测试分组的基础重构。下一阶段不需要再次搬迁目录，而应集中解决：

1. G0 真实后端栈已通过，但 W1 资源发布与完整真实数据链尚未闭环；
2. generated contracts 业务采用不完整；
3. Integration 的 feature 主要仍是应用内边界；
4. MFA/恢复只有前端状态容器，后端契约未实现；
5. Settings 存量实体页面和跨应用真实数据仍需收口；
6. 组件库仍按常规 UI 组件库思路演进，导致页面、编辑器、Web/Electron 宿主之间出现过多转换层和适配层。下一阶段应增加底层组件装配层，把组件、运行环境能力、样式 token 和编辑器接入统一收口，而不是继续扩大纯展示组件数量；
7. `nebula-assembly` 新增后，`packages/core` 中存量 glue/bridge 层尚未同步精简。若 `app-shell`、`runtime`、`shell`、`electron-shared` 继续保留重复的宿主判断、presentation bridge、theme/locale/preference bridge 和 embed glue，整体复杂度只是被重新包装，并没有真正下降；
8. 运行形态地址配置已收口到既有 `configs/windows.json`，但后续新增页面、测试、脚本时仍必须遵守“配置 → 生成产物 → helper 消费”的链路，避免重新散落 `localhost`、端口、API target 或 embed URL。

## 2. 技术与工作区基线

| 类别                     | 当前值               |
| ------------------------ | -------------------- |
| Node.js                  | `>=22.12.0`          |
| 包管理声明               | `pnpm@11.25.0`       |
| 日常工具                 | Vite+ CLI `vp`       |
| Vite+ / Vite             | 0.3.0 / 8.2.2        |
| Vue / Vue Router         | 3.5.42 / 4.6.4       |
| TypeScript               | 6.0.3                |
| Electron / electron-vite | 44.2.0 / 5.0.0       |
| Tailwind CSS             | 4.3.3                |
| Vitest / Playwright      | 5.0.0 / 1.62.1       |
| 工作区清单               | 38 个 `package.json` |

版本事实来自根 `package.json` 与 `pnpm-workspace.yaml`。尽管 package manager 字段仍声明 pnpm，仓库约定日常安装、脚本、检查和测试统一经 `vp` 执行。

## 3. 当前架构

### 3.1 应用层

```text
apps/
├── electron/                 # 主进程、窗口生命周期、renderer 引导
├── electron-preload/         # 统一 preload + capability 工厂
├── web/                      # Web Shell 与 embed 入口
└── sub-web/
    ├── frontend/             # Shell/个人工作台
    ├── integration/          # Portal、Provider、Admin 与 Camel 业务
    ├── settings/             # 个人、组织、平台设置
    ├── login/                # 认证流程
    └── docs/                 # 产品帮助与开发者参考
```

### 3.2 共享层

```text
packages/
├── contracts/               # 手写兼容契约 + OpenAPI 生成结果/facade
├── core/
│   ├── api-client
│   ├── app-shell             # 待精简：保留 shell 协议/manifest/消息，不继续承载 UI 装配胶水
│   ├── auth / auth-provider
│   ├── electron-shared       # 待精简：保留 Electron 共享类型/preload 契约，theme/locale/preference bridge 向 assembly/boot 边界收口
│   ├── msw
│   ├── runtime               # 待精简：保留 bootMicroApp 协议，减少运行时宿主检测扩散
│   ├── shell                 # 待治理：Shell 产品容器，避免继续沉淀跨宿主 UI glue
│   ├── sse-events
│   └── tenant
├── editors/
│   ├── code-editor
│   ├── dag-editor
│   ├── flow-editor
│   ├── integration-panel
│   └── low-code-form
├── features/
│   └── use-confirm          # 当前唯一正式共享 feature
├── ui/
│   ├── nebula-assembly       # 目标新增：底层组件装配层
│   ├── nebula-agent
│   ├── nebula-layout
│   └── nebula-ui
├── styles/
└── types/
```

### 3.3 依赖方向

目标依赖方向为：

```text
apps → app-local features → shared features/editors/ui → core/contracts
```

约束：

- `core` 不依赖 `apps` 或业务 feature；
- `core` 不依赖 `ui/nebula-assembly`，但 `core` 中已被 assembly 接管的 UI 装配、overlay、theme/density、editor host 与宿主判断能力必须逐步删除或降级为兼容 facade；
- `ui` 不访问业务 API；
- `ui/nebula-ui` 只提供无宿主假设的基础组件，`ui/nebula-assembly` 负责组件装配、运行环境能力注入和样式适配；
- 页面不重新声明服务端 DTO；
- Electron 与 Web 不维护两套窗口、认证或 API target；
- feature 不直接维护另一套全局 Session/Tenant 存储。

## 4. 运行模型

### 4.1 配置单源

`configs/windows.json` 是以下信息的单源：

- Web/Electron renderer；
- embed entry；
- 后端 `apiTargets`（platform/console/executor origin）；浏览器 API 路径前缀不在此配置；
- label、category、help key、搜索关键词和角色；
- preload capability；
- display order。

生成脚本将配置转为 app-shell/Electron 可消费的代码，`check:generated` 检查幂等和漂移。

### 4.1.1 地址与运行形态单源（已落地）

`configs/windows.json` 已扩展为窗口、API base、dev API target 和前端运行形态的共同入口，不再新增独立 runtime address 配置文件。这里的“运行形态”不是 Electron/Web 宿主差异，而是子应用如何被访问和装载：

| 运行形态 | 说明 | 地址来源要求 |
| --- | --- | --- |
| `integrated` | Web Shell / Electron Shell 统一承载，sub-web 通过 embed/iframe/renderer 配置进入 | Shell entry、embed entry、window manifest、API base、asset base 必须来自生成配置 |
| `standalone` | `apps/sub-web/*` 独立启动，用于子应用局部开发、调试和单包测试 | 独立 dev server port、base path、proxy target、mock/real API mode 必须来自同一注册表 |
| `real-stack` | 三后端应用 + Web 前端真实链路验证 | 后端 console/executor/platform 地址、OpenAPI 地址、Playwright baseURL 必须由注册表派生 |
| `mock/e2e` | Playwright mock-regression / experience 等测试运行 | 测试入口、route pattern、mock API base 不得手写散落地址 |

目标是把“地址变更”从全局搜索改成修改既有 `configs/windows.json`，并由生成和检查发现漂移。当前扩展内容包括：

- `shell.web`、`shell.electron.rendererEntry`、`shell.embedQuery`；
- 每个 sub-web 的 `standalone.port`、`standalone.basePath`、`proxyPreset`、`displayPath`；
- 仅配置 `apiTargets`（platform/console/executor origin）；API 路径前缀按 target 分组，作为代码黑盒，调用形态为 `GENERATED_API_NAMESPACES.<target>.<name>`；
- real-stack OpenAPI 与健康检查地址；
- Playwright project 的默认 baseURL 与允许 mock 的 route pattern；
- dev/prod 差异只通过 profile 覆盖，不允许在业务代码里拼接端口。

生成产物包括：

- app-shell/Electron/window manifest 消费的 generated window/runtime constants；
- `internal/vite` runtime helper、Vite/Vite+ dev server proxy 配置；
- Playwright `baseURL`、real-stack 脚本和 contract generation 的 endpoint；
- `@nebula-studio/contracts` / api-client 可消费的 API namespace constants；
- drift check：除配置、生成产物和明确白名单外，禁止新增裸 `localhost`、`127.0.0.1`、固定前后端端口和硬编码跨应用 URL。

边界：

- 页面、feature、editor、UI 包不得读取或拼接 host/port；
- standalone 子应用只能读取自身运行形态下的 generated address，不得假设 Shell 存在；
- integrated 运行时只能通过 Shell/window manifest 解析 embed entry，不得硬编码兄弟子应用地址；
- 测试可以声明 route pattern，但 pattern 来源应从测试运行形态配置生成或集中导出。

### 4.2 宿主与 renderer

- Web 由 `apps/web/src/shell-entry.ts` 启动主 Shell，由 embed entry 加载子应用。
- Electron 使用单一 renderer boot，再根据窗口/renderer 配置动态加载子应用。
- preload 由统一入口按窗口 capability 组装 auth、notify、settings、shell 等桥接。
- 子应用通过 `bootMicroApp` 适配 standalone、Web embed、Electron 三种运行模式。
- 当前 Electron 内嵌展示配置为 iframe，与 Web Shell 保持一致。

### 4.3 认证与租户

- `auth-provider` 是认证 Session 的共享入口。
- API client 自动注入 Bearer Token、租户头并统一处理 401。
- `app-shell` 负责 Web/Electron 的会话同步和 embed 导航协议。
- `tenant` 包负责加载、选择和切换租户；子应用不得新建私有租户存储键。
- Shell Event Bus 已有 auth、tenant、theme 等跨应用事件，但真实数据失效仍需 real-stack 验证。

### 4.4 底层组件装配层（目标新增）

当前 `packages/ui` 更接近常规组件库：基础组件、布局组件、业务页面和编辑器入口之间需要手写 glue code；Electron 与 Web 又分别补运行环境适配。这使前端架构在“看起来分层清晰”的同时，实际开发中出现重复转换、重复 props 映射、重复样式兜底和宿主差异判断。后续优化不应继续把所有能力堆到 `nebula-ui`，而应新增一个底层组件装配层，建议包名为 `packages/ui/nebula-assembly`。

必须守住的依赖方向：

```text
apps boot 边界
  → nebula-layout / features / editors   # 只消费 assembly contract
    → nebula-assembly                    # 装配、overlay、style、editor host
      → nebula-ui + styles               # 无宿主判断

core/runtime、app-shell、electron main 不依赖 assembly。
```

`bootMicroApp` 继续作为子应用启动协议，不直接 import assembly，避免 `core → ui`。Web/Electron/standalone 的差异只能出现在 apps boot 组装 Host Adapter 的边界；页面、feature、editor 内不得判断 `window.electron`、iframe、preload 或路由实现。现有 `ConfigProvider` 不拆除，theme/locale 仍由它同步 DOM；assembly 读取并桥接该上下文，同时补齐 density、overlay、host capability 和 editor host。

需要特别注意：新增 `nebula-assembly` 不是“再加一层”。它只有在后续同步精简 `packages/core` 旧 glue 层时才算完成架构优化。`app-shell` 应回到 shell manifest、窗口/嵌入协议、消息与导航协作；`runtime` 应只保留子应用启动协议和最小运行模式识别；`electron-shared` 应保留 Electron 共享类型、preload 契约和 ConfigProvider 兼容入口；`shell` 应作为产品 Shell 容器，不再继续沉淀跨宿主 UI 装配逻辑。凡是已经由 assembly 提供的 overlay、style contract、host surface、editor host 和页面级适配，都应从 core glue 中移出、删除或转为兼容 shim。

装配层职责：

- 提供 `createNebulaComponentContext()` / `provideNebulaAssembly()` 一类统一入口，注入 runtime、theme、locale、density、teleport target、overlay container、asset resolver、host capability 和 navigation bridge；
- 面向 Web、Electron、standalone 子应用暴露同一套 adapter contract，由宿主在启动时提供能力，不允许业务组件直接判断 `window.electron`、iframe、preload 或路由实现；
- 把 `packages/editors` 的 Code/DAG/Flow/低代码表单接入抽象为 editor host contract，例如尺寸、主题、快捷键、只读态、命令面板、文件/资源选择器、诊断面板和保存事件；
- 统一 ViewModel → component props 的低层映射，减少页面、feature 和编辑器各自维护转换层；
- 统一 overlay、message、confirm、drawer、modal、tooltip、context menu 等跨宿主行为，避免 Web/Electron 分别适配；
- 输出可测试的 composition primitives，而不是继续制造大型“万能业务组件”。

首批公共入口建议保持克制：

- `createNebulaComponentContext()`、`provideNebulaAssembly()`、`useNebulaAssembly()`、`tryUseNebulaAssembly()`；
- `createWebHostAdapter()`、`createElectronHostAdapter()`、`createStandaloneHostAdapter()`，由 apps boot 显式传入 `openExternal`、`notify`、`navigation`、asset URL 等能力，adapter 只做标准化，不把 Electron API 暴露给业务；
- `overlay.confirm()`、`overlay.toast()` 与 `NebulaOverlayRoot`，toast 第一期可为空实现；
- `applyStyleContract(root)`，只作用于应用挂载根或 iframe 内根节点，不默认写 `document.documentElement`，避免多子应用互相污染；
- `useEditorHost()`，第一期只固定 theme、readonly、size/container、save command、diagnostics slot/stub、resource picker stub。快捷键 registry、命令面板可以预留类型，但不急于做复杂实现。

建议分层：

```text
nebula-ui               # 纯基础组件与设计 token 消费，不感知宿主
nebula-layout           # Shell/layout primitives，依赖 assembly context
nebula-assembly         # 组件装配、宿主能力、样式适配、editor host contract
features/editors        # 只消费 assembly contract，不直接适配 Web/Electron
apps                    # 只在启动边界提供 Web/Electron/standalone host adapter
```

样式治理也应从“页面内临时 Tailwind class”转为“token + CSS 变量 + 组件命名空间”的组合：Tailwind 可以继续作为 utility 生成工具，但不能成为跨包样式契约。更接近 Element Plus 的做法是：基础样式、主题变量、尺寸、暗色模式和组件状态类由组件库/装配层稳定输出，应用只覆盖 token 或命名空间变量。这样可以解决当前 Tailwind CSS 集成部分规则不生效、显示与预期不一致、不同子应用样式注入顺序不稳定的问题。

非目标：

- 不把 `nebula-assembly` 做成新的业务组件大杂烩；
- 不在装配层访问后端 API 或业务 store；
- 不要求 Electron/Web 各自维护单独 UI 适配层；
- 不为了“组件库完整度”继续扩展低复用视觉组件；
- 不替换 `app-shell` IPC、preload 能力模型或 `ConfigProvider`；
- 不在首批全量迁移 Integration 自定义 modal、Settings 实体列表、MFA、generated contracts。

## 5. 产品界面现状

### 5.1 Shell / Frontend

已实现：

- 个人工作台；
- 最近访问、申请、待办、异常和快捷动作模型；
- 应用启动器；
- 全局搜索/命令入口；
- 组织切换、标签、面包屑和 iframe 子应用承载；
- 加载失败、会话失效等恢复界面。

限制：部分摘要仍由前端模型或零值 provider 提供，尚未通过真实后端聚合数据验收。

### 5.2 Integration

路由和导航已区分：

| Surface  | 主要角色    | 当前职责                               |
| -------- | ----------- | -------------------------------------- |
| Portal   | 资源消费者  | 资源目录、详情、申请、我的资源、订阅   |
| Provider | 资源提供方  | 创建、版本、发布、授权与使用摘要       |
| Admin    | 管理员/运维 | 审批、插件、租户、Executor、治理、监控 |

应用内已经形成 `resource-catalog`、`plugin-catalog`、`subscription`、flows 等 feature 目录，但它们不是 `packages/features` 下的共享包。短期应继续收敛应用内部边界，不能仅为满足旧计划数量而制造共享包。

### 5.3 Settings

已实现个人、组织和平台三类入口、角色导航、权限矩阵、配置展示和审计页面。剩余问题：

- 用户、角色、权限、应用等实体列表模式未完全统一；
- 批量操作依赖后端批量事务契约，不能用前端串行请求伪造原子性；
- 组织/租户/权限真实联调依赖 Platform Console 恢复启动。

### 5.4 Login / AuthFlow

前端显式状态包括：

```text
credentials → organization → mfa → recovery → success/failure
```

已覆盖账号错误、锁定、网络、服务不可用、会话过期、权限变化和 MFA required 等分类。后端当前没有 MFA/TOTP/恢复事务 API，因此：

- mfa/recovery 只能作为 UI/状态容器；
- 不得在 Mock 之外伪造真实验证成功；
- 后端状态机落地后再启用真实提交和契约映射。

### 5.5 Docs

已拆分产品帮助和开发者参考，并有全文搜索、角色目录、文档元数据、help key 和首次任务引导。后续重点是随真实功能更新内容，而不是再次调整顶层结构。

### 5.6 Editors

`code-editor` 已有标准入口、独立类型检查、测试、异步 Monaco provider 和 bundle budget。基础 UI 不再直接承载编辑器实现。DAG、Flow、低代码表单继续作为独立编辑能力，不应互相反向依赖。

## 6. 已完成事项

以下事项不再进入重构 backlog：

- [x] `windows.json` 配置单源与 Schema；
- [x] Web/Electron 共享 manifest 和 API target；
- [x] 统一 preload capability；
- [x] app-shell SDK 与 shell UI 分离；
- [x] 统一 auth-provider、runtime 和 api-client 基础；
- [x] Portal/Provider/Admin 信息架构；
- [x] Settings 个人/组织/平台一级分区；
- [x] Docs 产品帮助/开发者参考分区；
- [x] AuthFlow 前端状态容器；
- [x] code-editor 边界、测试和 bundle budget；
- [x] Mock、experience、real-stack、electron 四类 Playwright project；
- [x] 保留 `apps/sub-web` 命名，不做无收益的整体迁移；
- [x] **F0** 真实栈基线（G0）：`ConfigService`、在线 OpenAPI、三应用 `run-real-stack.ps1` 与 real-stack E2E 已通过（2026-08-01）。
- [x] **F9** 运行形态地址配置：扩展既有 `configs/windows.json` / schema；API 侧仅配置 `apiTargets`，路径前缀与 Vite proxy 收口到 `internal/vite` API context 黑盒，调用为 `GENERATED_API_NAMESPACES.<target>.<name>`。

## 7. 当前缺口

> 本节仅保留 **仍未完成** 或需 **外部依赖** 的条目；F0/F7/F8/F9 已闭合，详见 §6。

### F1：generated contracts 采用率（P0）

- [x] System / Settings：`User`/`Role`/`Permission`/`Organization`/`ShellApp`/`ConfigItem` 经 `contracts/system/mappers.ts` 对齐 generated
- [x] Integration Task / Flow：`TaskCreateRequest`/`FlowCreateRequest` 经 `contracts/integration/mappers.ts` + `taskApi` 线格式映射
- [x] Subscription portal DTO：`SubscriptionAccessRequest*` 迁入 `contracts/integration/subscription`
- [x] ESLint `contract-boundary` + README 新 API 规则
- [ ] Auth、Camel Plugin、governance/monitor 全量 OpenAPI 覆盖（**手写保留，非 backlog 尾巴**）

### F2：真实数据与 ViewModel 闭环（P1）

- [x] Shell `workspaceModel` 摘要接 console/monitor API（`useWorkspaceSummary`）
- [x] Integration 管理首页「待发布」接 interface 列表状态
- [x] Tenant 页移除硬编码用户，改 `/api/system/users/page`
- [ ] Sessions/Profile 完整数据：**依赖后端 session/identity API**（前端保留 skeleton + empty/forbidden）

### F3：feature 治理（P1）

- [x] `packages/features/README.md` 提升门槛检查表
- [x] `plugin-catalog/index.ts` 门面（与 `subscription-manager` 同级）
- [x] 明确不提升 `resource-catalog` / `plugin-catalog` / `subscription-manager` 至 `packages/features`（单消费者）

### F4：Settings 横向收口（P1）

- [x] Users/Roles/Permissions/Apps — 已用 EntityList
- [x] Logs → EntityListPage
- [x] Config / Organizations — 保留树与 scope/inherit/impact，统一 filter/header/危险操作文案（本轮对齐 EntityList 模式）
- [x] **批量操作：不适用**（后端未提供 batch 契约）

### F5：AuthFlow（P1）

- [x] **F5a** 前端 `authStateMachine`（`nextStep` / 稳定错误码 reducer；MFA/组织完成前 `canPersistFinalToken` 拦截）
- [ ] **F5b 外部依赖**：后端预认证/MFA/恢复契约 + real-stack Auth E2E

### F6：类型与构建治理（P2）

- [x] `env.d.ts` 共享类型收敛至 `@nebula-studio/types/sub-web`；各 app 仅保留 `Window.api` 差异
- [x] `check:editors` / editor boundaries 保持 CI 通过；**不删** `packages/editors`
- [ ] Electron 自动更新：占位未接签名/更新源/回滚（**本轮不交付**）

### ~~F7~~ / ~~F8~~（已闭合 → §6 摘要）

- **F7 已完成**：`nebula-assembly` 三阶段 + host-boundary lint；E2E `expectAssemblyMarkers` 统一 Web/Electron 断言
- **F8 已完成**：core 胶水 inventory + boot 盖章 + layoutHost facade + core→assembly lint；`installWebPresentation` / `shellHostBridge` / `IframeHost` / `installShellIframeElectronBridge` 为**保留协议**，非待删模块

### ~~F9~~（已闭合 → §6 摘要）

- **F9 已完成**：未新增配置文件，直接扩展 `configs/windows.json` 和 `configs/windows.schema.json`，统一承载 `standalone`、`integrated`、`real-stack`、`mock/e2e` 的入口、base path、dev server、API target、OpenAPI endpoint 和 route pattern。浏览器 API 路径前缀与 Vite proxy 不进入 `windows.json`，而按 `apiTargets` 分组固化在 API context 黑盒中。
- `scripts/generate-window-configs.mjs` 生成 app-shell/Electron manifest、runtime address constants 和 `@nebula-studio/contracts` API namespace constants；`internal/vite` 提供 shell、standalone、proxy、Playwright、real-stack、OpenAPI helper。
- 子应用 Vite 配置只声明 `appId`，端口、base path、proxy preset 均从 `windows.json` 派生；Shell 集成运行时通过 window manifest/embed helper 进入子应用。
- `scripts/generate-contracts.mjs`、`playwright.config.ts`、`scripts/e2e/run-real-stack.ps1`、real-stack E2E 和前端 api-client 已切换为生成常量/helper。
- `vp run check:generated` 已包含地址漂移检查，防止新增裸 host、固定端口和硬编码跨应用 URL。

## 8. 测试现状

2026-08-19 在本轮 §7 收口执行：

```text
vp run check:generated
vp run --filter @nebula-studio-internal/vite test
vp run electron#typecheck:node
vp run build:web
```

F9 地址配置改造补充验证：

```text
vp run generate:configs
vp run check:generated
vp run --filter @nebula-studio-internal/vite test
vp run electron#typecheck:node
vp run build:web
```

已知未闭合类型问题（非 F9 地址改造新增）：

- `vp run --filter @nebula-studio-renderer/integration typecheck` 仍受历史测试 fixture、订阅事件类型导出、ServiceFlow editor 可选值、tenant users API DTO 等问题影响；
- `vp run --filter @nebula-studio-renderer/settings typecheck` 仍有 `LogsPage.vue` 未使用 `search` 变量。

| Project           | 职责                                           | 本轮 |
| ----------------- | ---------------------------------------------- | ---- |
| `mock-regression` | 快速稳定回归；含 `expectAssemblyMarkers` helper | 已跑 |
| `experience`      | 亮暗主题、响应式、键盘焦点和性能预算           | 未全量 |
| `real-stack`      | 三后端 + Web；禁止业务 Mock                    | 需本地栈 |
| `electron`        | 启动、会话、assembly 标记复断言                | 需构建 Electron |

Playwright 枚举仍为 **24 项 / 8 文件**（`vp exec playwright test --list`）。real-stack 需三应用健康后单独执行 `vp run test:e2e:real`。

## 9. 增量实施顺序

### Phase A：恢复真实栈

- [x] 修复 Platform Console Context；
- [x] 三后端应用健康检查；
- [x] 严格在线生成契约并完成幂等检查，在线失败不回退已提交契约；
- [x] real-stack 完整通过。

### Phase B：契约和真实数据

- [x] 迁移 Platform/System/Integration contracts 首批（F1）
- [x] Portal/Shell 摘要与 Integration 管理页关键指标使用真实 API（F2 子集）
- [ ] 组织/租户切换与跨应用失效 real-stack 回归
- [x] 新 API ESLint 禁止手写重复 DTO

### Phase C：应用内边界收敛

- [x] 新增 `packages/ui/nebula-assembly`（F7）
- [x] Web/Electron/standalone assembly adapter（`assembly-boot`）
- [x] Code Editor + DAG 试点 EditorHost
- [x] token/CSS variables/namespace 样式契约
- [x] 分类 + 冻结第二入口 + facade 精简 core glue（F8；**非删文件**）
- [x] 建立运行形态地址注册表，收口 sub-web standalone / integrated / real-stack / mock-e2e 的入口、API target、proxy 与测试地址（F9；扩展既有 `configs/windows.json`，不新增配置文件）
- [x] Integration composable 提取：`useResourceCatalogPage` / `usePluginsPage` / `useTenantPage` + 单测
- [x] mapper/composable 单测（contracts + catalog + tenant + authStateMachine）
- [x] feature 提升门槛文档；`plugin-catalog` index 门面
- [x] Settings Logs EntityList；Config/Organizations 对齐 EntityList 模式

### Phase D：认证增强与生产体验

- [x] 前端 MFA/恢复状态机（F5a；`authStateMachine.ts`）
- [ ] 接入后端 MFA/恢复契约 + E2E（F5b，外部依赖）
- [ ] Electron 更新链路；
- [ ] 更完整的 WCAG 扫描、视觉审查和性能基线；
- [ ] 插件签名、实时通知和观测能力对应 UI。

## 10. 质量关口

每个前端变更至少满足：

- `vp check`；
- 受影响 workspace 的 typecheck/test；
- `vp run build:web` 或 `vp run build`；
- 生成脚本后无未提交差异；
- 新 API 有 adapter/mapper 测试；
- 新页面有 loading、empty、error、partial、forbidden 状态；
- Web/Electron 共享能力定义；
- 新增或改造跨宿主组件时，必须通过 assembly adapter 注入 host capability，不得在组件内直接判断 Web/Electron；
- 编辑器接入必须消费 editor host contract，不能在 editor 包内复制 Shell、preload 或 Web embed 适配；
- 样式变更必须落到 token/CSS variables/namespace 或组件层样式入口，不能只靠页面级 Tailwind class 兜底；
- assembly 覆盖的能力不得在 `packages/core` 中新增第二套 glue/facade；涉及 core 的重构必须说明删除了哪些旧入口、减少了哪些导出或调用路径；
- 地址、端口、API target、OpenAPI endpoint、Playwright baseURL 只能来自运行形态地址注册表或生成产物；新增裸 `localhost`、`127.0.0.1`、固定端口、硬编码跨应用 URL 必须被检查拦截；
- 核心用户旅程有对应 Playwright 层级；
- 真实业务完成声明必须以 real-stack 为证据。

推荐完整顺序：

```text
vp install
  → vp run check:generated
  → vp check
  → vp run test
  → vp run build
  → vp run test:e2e:mock
  → vp run test:e2e:experience
  → vp run test:e2e:electron
  → vp run test:e2e:real
```

## 11. 暂缓事项

以下事项没有当前代码证据表明值得优先实施：

- 把 `apps/sub-web` 整体改名；
- 立即把 Integration 拆成多个独立应用；
- 为满足目录数量创建空 feature 包；
- 在后端无批量事务 API 时实现“伪批量”；
- 在真实数据闭环前继续扩大视觉组件数量；
- 继续为 Web、Electron、standalone 分别维护页面级 UI 适配层；
- 把 Tailwind utility class 当作跨包样式契约；
- 新增 `nebula-assembly` 后继续保留与其职责重叠的 core glue 层，并把“双轨兼容”长期化；
- 继续在页面、feature、editor、测试、脚本中散落运行地址，并依赖全局搜索维护；
- **不因低使用率删除 `packages/editors/*` 或 app-shell 协议 glue**（`installWebPresentation`、`shellHostBridge`、`IframeHost` 等为正式边界）。

## 12. 成功标准

前端重构真正完成应满足：

1. 三平台应用真实栈持续通过；
2. 后端字段漂移在生成、编译或 E2E 阶段被阻止；
3. Portal、Provider、Admin 和 Settings 使用真实数据与权限；
4. Web 与 Electron 共用窗口、认证、租户和 API 定义；
5. Web、Electron、standalone 共用底层组件装配层，业务组件和编辑器不再手写宿主适配；
6. `packages/core` 中与 assembly 重叠的 glue/bridge 层被删除、收敛或降级为明确的兼容 facade，导出面和跨包调用路径实际减少；
7. sub-web 独立运行、Shell 集成运行、mock/e2e、real-stack 的地址配置来自同一运行形态注册表，地址调整不再依赖全局搜索；
8. App-local feature 边界清晰，共享包只来自真实复用；
9. 样式 token、CSS variables、组件命名空间和暗色/密度配置稳定，Tailwind 只作为实现工具而非跨包契约；
10. AuthFlow 的 MFA/恢复由真实后端状态机驱动；
11. Mock、体验、Electron 和 real-stack 各自承担明确且不互相替代的责任。
