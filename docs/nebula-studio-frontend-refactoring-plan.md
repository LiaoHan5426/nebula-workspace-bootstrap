# Nebula Studio 前端架构现状与增量重构计划

> 文档版本：v3.1
> 最后更新：2026-08-19
> 代码基线：`nebula-studio@5a36a7e09787889607d53ddea65b3e25b98b5397`
> 本文只描述当前代码和剩余增量工作；已完成的历史阶段不再作为待办重复保留。

## 1. 当前结论

Nebula Studio 已完成宿主、窗口配置、preload、认证、运行时、基础布局、主要产品界面和测试分组的基础重构。下一阶段不需要再次搬迁目录，而应集中解决：

1. G0 真实后端栈已通过，但 W1 资源发布与完整真实数据链尚未闭环；
2. generated contracts 业务采用不完整；
3. Integration 的 feature 主要仍是应用内边界；
4. MFA/恢复只有前端状态容器，后端契约未实现；
5. Settings 存量实体页面和跨应用真实数据仍需收口；
6. 组件库仍按常规 UI 组件库思路演进，导致页面、编辑器、Web/Electron 宿主之间出现过多转换层和适配层。下一阶段应增加底层组件装配层，把组件、运行环境能力、样式 token 和编辑器接入统一收口，而不是继续扩大纯展示组件数量。

## 2. 技术与工作区基线

| 类别 | 当前值 |
| --- | --- |
| Node.js | `>=22.12.0` |
| 包管理声明 | `pnpm@11.5.1` |
| 日常工具 | Vite+ CLI `vp` |
| Vite+ / Vite | 0.2.6 / 8.1.3 |
| Vue / Vue Router | 3.5.35 / 4.6.4 |
| TypeScript | 6.0.3 |
| Electron / electron-vite | 43.x / 5.x |
| Tailwind CSS | 4.3.3 |
| Vitest / Playwright | 4.1.10 / 1.62.0 |
| 工作区清单 | 38 个 `package.json` |

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
│   ├── app-shell
│   ├── auth / auth-provider
│   ├── electron-shared
│   ├── msw
│   ├── runtime
│   ├── shell
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
- API base 与 8090/8080/8081 target；
- label、category、help key、搜索关键词和角色；
- preload capability；
- display order。

生成脚本将配置转为 app-shell/Electron 可消费的代码，`check:generated` 检查幂等和漂移。

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

| Surface | 主要角色 | 当前职责 |
| --- | --- | --- |
| Portal | 资源消费者 | 资源目录、详情、申请、我的资源、订阅 |
| Provider | 资源提供方 | 创建、版本、发布、授权与使用摘要 |
| Admin | 管理员/运维 | 审批、插件、租户、Executor、治理、监控 |

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
- [x] 保留 `apps/sub-web` 命名，不做无收益的整体迁移。

## 7. 当前缺口

### F0：真实栈基线已恢复（G0 已完成）

2026-08-01 已修复 `ConfigService`、在线 OpenAPI 统一响应和跨事务管理器租约回收问题。`run-real-stack.ps1` 已从两个 demo 切换到三个正式平台应用，并从停止状态完成定向构建、8090/8080/8081 健康、在线契约生成和 1 项无 Mock real-stack 测试。F0 不再是当前阻塞，下一前端重点转为 generated contracts 采用与 W1 真实发布数据链。

### F1：generated contracts 采用率不足（P0）

现状：

- 有 `generate:contracts`；
- 有离线 OpenAPI 与 generated TypeScript；
- 有业务 facade；
- Auth/Plugin 等部分域已迁移；
- System/Integration 等仍有手写兼容契约。

目标：新增 API 100% 经 facade；存量按域迁移；CI 执行生成差异和 breaking change 检查。

### F2：真实数据与前端 ViewModel 未完全闭环（P1）

Portal、Shell 摘要、Settings 和部分管理页已经有 UI 与 mapper，但需在真实三应用栈中验证：

- 字段、分页、状态枚举和错误码；
- 组织/租户切换后的缓存失效；
- 资源申请、审批和发布状态；
- Gateway、订阅、Monitor 与插件安装。

### F3：feature 治理（P1）

当前 `packages/features` 只有 `use-confirm`。提升共享包必须同时满足：

1. 至少两个真实消费者；
2. 不依赖应用 Router；
3. API、mapper、composable 和状态机可独立测试；
4. 有稳定公共入口；
5. 提升后不会造成宿主或 UI 层反向依赖。

优先评估 `plugin-catalog`、`resource-catalog`、`subscription-manager`，但不预设必须全部提升。

### F4：Settings 横向收口（P1）

- 统一 EntityList、筛选、详情抽屉和危险操作说明；
- 对批量操作先补后端契约；
- 配置页面继续展示作用域、默认值、继承、敏感性和影响预览；
- 权限隐藏必须同时覆盖导航、路由和后端 API。

### F5：AuthFlow 后端接入（P1）

等待后端提供预认证事务、MFA 和恢复契约后：

- 以 `nextStep` 和稳定错误码驱动状态，不解析错误文案；
- MFA/组织完成前不保存最终 Token；
- Web/Electron 共用同一状态机；
- 增加重放、过期、锁定和恢复后旧会话失效 E2E。

### F6：类型与构建治理（P2）

- 继续集中环境类型，减少本地重复 `env.d.ts`；
- 保持编辑器异步加载和 bundle budget；
- Electron 自动更新当前仍是占位，只有接入签名、更新源和回滚验证后才能标记完成。

### F7：组件装配层缺失（P0）

现状（2026-08-19 更新）：

- [x] 新增 `packages/ui/nebula-assembly` 与 `apps/sub-web/assembly-boot`（boot 边界显式传入 capability）；
- [x] Web/Electron/sub-web 五入口通过 `wrapSubAppWithAssembly` + `installAssemblyForSubApp` 注册 adapter；
- [x] OverlayRoot + Settings confirm 经 assembly overlay；`use-confirm` 薄转发；
- [x] Code Editor + DAG Editor 试点消费 `EditorHost`（theme/readonly/size/save/diagnostics stub）；
- [x] `applyStyleContract(root)` 仅作用于子应用挂载根，不写 `document.documentElement`；
- [ ] 全量 Dialog/Drawer/Select teleport、layout `useShellHosted` 改读 assembly、Integration 手写 modal 迁移（F7 后续）；
- [ ] 全仓库业务代码无宿主分支 lint（后续静态检查目标）。

三阶段落地边界：

1. 基础骨架：建立 `nebula-assembly` 的 host/style/overlay/editor contract、boot helper 和单元测试；
2. 宿主接线：Web/Electron/sub-web boot 注册 assembly adapter，接入 `NebulaOverlayRoot`，Settings confirm 迁移到 assembly overlay；
3. 编辑器试点：以 Code Editor + DAG 作为最小真实消费，验证编辑器只消费 editor host contract，不直接适配宿主。

后续重点：

- `nebula-layout` 的 `useShellHosted` 优先读取 assembly `host.surface`，无 context 时再 fallback app-shell；
- `NebulaDialog`、Drawer、Select 等基础组件支持可选 overlay container 注入，未注入时仍 fallback body；
- Integration 手写 modal 只按真实收益逐步迁移，不为一次性清理扩大风险；
- 补充静态检查或 lint，阻止页面、feature、editor 新增 `window.electron` / iframe / preload 宿主判断；
- Web mock-regression 与 electron smoke 验证同一 assembly 标记或 overlay root 在两个宿主出现。

## 8. 测试现状

本次在当前提交执行：

```text
vp exec playwright test --list
```

实际枚举 **24 项测试、8 个文件**：

| Project | 数量 | 职责 |
| --- | ---: | --- |
| `mock-regression` | 12 | 快速稳定回归，允许固定网络响应 |
| `experience` | 10 | 亮暗主题、4 个响应式宽度、键盘焦点和性能预算 |
| `real-stack` | 1 | 三后端应用 + Web + 在线契约；禁止业务网络 Mock |
| `electron` | 1 | 启动、会话、preload capability 和窗口切换 |

除 test listing 外，2026-08-01 已实际执行 `vp run test:e2e:real`，1 项 real-stack 测试通过；`vp run build:web` 与 `vp run check:generated` 同时通过。其余 mock、experience、electron 项目未在本次 W0 中全量重跑，不能据此宣称 24 项全部通过。

## 9. 增量实施顺序

### Phase A：恢复真实栈

- [x] 修复 Platform Console Context；
- [x] 三后端应用健康检查；
- [x] 严格在线生成契约并完成幂等检查，在线失败不回退已提交契约；
- [x] real-stack 完整通过。

### Phase B：契约和真实数据

- [ ] 迁移 Platform/System/Integration contracts；
- [ ] Portal/Settings/Camel 关键路径使用真实响应；
- [ ] 组织/租户切换与跨应用失效测试；
- [ ] 新 API 禁止手写重复 DTO。

### Phase C：应用内边界收敛

- [x] 新增 `packages/ui/nebula-assembly`，收口 host adapter、style adapter、overlay service 和 editor host contract（F7 三阶段 1–3）；
- [x] Web/Electron/standalone 启动边界改为提供 assembly adapter（`assembly-boot` 显式 capability；试点页无宿主分支）；
- [x] 选择 Code Editor + DAG 模块作为试点，验证 editors 消费 assembly contract；
- [x] 建立 token/CSS variables/namespace 样式契约（挂载根 `data-nebula-*`；Tailwind 仍为实现工具）；
- [ ] Integration 页面只组合 feature；
- [ ] 为 mapper、composable、状态机增加单元测试；
- [ ] 按真实复用证据提升共享 feature；
- [ ] 统一 Settings 存量实体页面。

### Phase D：认证增强与生产体验

- [ ] 接入后端 MFA/恢复状态机；
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
- 把 Tailwind utility class 当作跨包样式契约。

## 12. 成功标准

前端重构真正完成应满足：

1. 三平台应用真实栈持续通过；
2. 后端字段漂移在生成、编译或 E2E 阶段被阻止；
3. Portal、Provider、Admin 和 Settings 使用真实数据与权限；
4. Web 与 Electron 共用窗口、认证、租户和 API 定义；
5. Web、Electron、standalone 共用底层组件装配层，业务组件和编辑器不再手写宿主适配；
6. App-local feature 边界清晰，共享包只来自真实复用；
7. 样式 token、CSS variables、组件命名空间和暗色/密度配置稳定，Tailwind 只作为实现工具而非跨包契约；
8. AuthFlow 的 MFA/恢复由真实后端状态机驱动；
9. Mock、体验、Electron 和 real-stack 各自承担明确且不互相替代的责任。
