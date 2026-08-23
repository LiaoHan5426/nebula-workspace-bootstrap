# Nebula 前端 Module Federation 架构重构计划

> 文档版本：v1.1
> 制定日期：2026-08-22
> 进度复核：2026-08-23（二次代码复核；完成度只按可运行代码、自动化测试和外部验收证据判定，不能由历史勾选项推导）
> 适用仓库：`nebula/`、`nebula-studio/`
> 代码基线：`nebula@4c93ea8dcb1b31159815ee0990eb9316149fc3d7`、`nebula-studio@20951519f22a94194e5e5c5794e72d1258a4ab0b`（2026-08-23 复核；实施前必须重新记录 HEAD，基线不是永久常量。nebula 低代码 Java 若尚未进该 commit，以工作区为准）
> 文档位置：工作空间根目录 `docs/`；本文是跨仓库规划，不替代两个仓库各自的开发规范。

> v1.1 变更摘要：补齐单计划内的 A/B/C 轨道关门规则；统一 Phase 0 与立即执行清单；修正 Phase 8–10 前置依赖；将 CSS 隔离替代方案纳入同一硬门槛；统一目标命令格式。此前已补齐 iframe capability 协议、双 expose 隔离、低代码运行依赖、现有 low-render 迁移和 Electron 登录窗口边界。
>
> 2026-08-23 二次复核：A 轨 Federation 主链已落地，但 internal/scripts/package 收口在本轮继续整改；B 轨具备 token/theme/pattern 基础和视觉矩阵，不等于 §7.4 的全部存量界面已经现代化；C 轨仓库实现与真实独立进程、厂商 HSM、生产 soak/SLO 证据分别计数，不再使用“代码已到可部署边界”替代完成证明。

## 1. 执行摘要

本轮重构的核心不是简单地“给 Vite 加一个 Module Federation 插件”，而是重新定义前端的交付单元、运行时边界和共享包边界：

- `nebula-studio` 从“一个仓库内编译所有 renderer 的多入口应用”调整为“两个 Host + 多个可独立交付 Remote + 少量稳定共享平台包”；
- Web Shell 与 Electron Renderer 作为 **Host**，负责应用发现、远程加载、导航、权限、故障隔离和宿主能力注入；
- Integration、Settings、Docs 等作为 **Federation Remote**，可以单独开发、测试、构建、预览和部署，也可以被 Host 按配置动态接入；
- Frontend/Workspace 不再同时承担“业务子应用”和“宿主壳层”两种身份，应并入 Shell Host；
- Login 优先作为 Host 的认证 surface/feature，不再被 Integration 直接依赖；如未来有独立认证站点需求，再单独发布为 Remote；
- `nebula` 后端提供前端应用注册中心，存储应用 manifest URL、加载驱动、路由、权限、兼容版本和启停状态；现有 `ShellApp` 只具备 label/renderer/preload 等静态字段，需要演进；
- Module Federation 只接入遵守契约的已发布前端应用；普通外部页面通过 iframe 接入，禁止嵌入的页面通过 external 驱动打开；
- 保留 `vp run dev`（Electron Host）与 `vp run dev:web`（Web Host），并明确保留每个 Remote 的 `dev/build/preview`，因此 **引入 Module Federation 不等于失去独立启动能力**；
- `internal/` 只保留仓库内部构建工具，不承载产品运行时；`packages/` 重新按 contract/platform/ui/editor/testing 分类，清理 app-shell/runtime/assembly/bridge 的重叠职责。
- 建立独立的设计系统与样式构建链：Tailwind 只作为每个 Host/Remote 的编译期实现工具，跨应用契约由版本化 design tokens、CSS cascade layers 和 UI primitives 承担；
- 统一界面设计语言和页面模板，通过视觉基线、可访问性和设计审查治理老旧/不一致页面；
- 主题能力从二值 `light | dark` 升级为“模式 + 自定义主题色 + 密度 + 对比度”的统一 Theme Contract，并在 Web、Electron、standalone 和 Remote 之间同步。
- 建立统一应用数据底座：Pinia 负责客户端/领域状态，Vue Query 负责服务端状态，Router 负责 URL 状态，组件局部状态继续使用 Vue；持久化、缓存和跨应用同步不再由页面各自实现；
- 建立 Vue I18n 国际化架构，由 Host 解析当前 locale，各 Remote 拥有并按需加载自己的消息目录；
- 为后续低代码大屏等子应用建立 schema、可复用编辑器、Compiler Vue 组件、Studio 内置运行入口、预览、发布和权限底座，使低代码产物能够作为受治理的应用版本接入 Host。

目标不是追求更多包，而是让每个包对应一个稳定、可验证的变化原因。完成后，Host 不再静态依赖所有 Remote，Remote 不再依赖 Electron、Shell 实现或兄弟应用，后端应用注册与前端运行时加载形成闭环。

## 2. 范围与非目标

### 2.1 本次范围

1. `nebula-studio/apps` 的 Host/Remote 重新划分；
2. 引入 `@module-federation/vite` 与 Module Federation Runtime；
3. 保留 Remote 的 standalone 启动和独立构建；
4. 建立前端应用 manifest、Host capability 和生命周期契约；
5. 重构 `nebula-studio/internal` 与 `nebula-studio/packages`；
6. 删除重复的 runtime 检测、boot、API base、Shell bridge 和 Electron 判断；
7. 在 `nebula` 中演进应用注册模型与查询/管理 API；
8. 建立 Web、Electron、standalone、remote deployment、iframe/external 的测试矩阵；
9. 规划灰度、回滚、兼容和安全机制。
10. 重建 Tailwind/CSS 集成链、设计 token、组件视觉规范和自定义主题能力。
11. 建立 Pinia、持久化、Vue Query 和 Vue I18n 的平台级创建器、策略、测试工具与生命周期约束。
12. 在同一计划内建设低代码平台：可复用 low-code editor、`LowCodeCompiler` Vue Component、包含设计态与运行态 expose 的 Low-code Studio Remote、组件/资源体系、后端草稿/发布服务和首个大屏试点；低代码应用发布后复用标准前端应用注册、加载、灰度与回滚链路。

### 2.2 非目标

- 不把 Java/PF4J 后端插件与前端 Federation Remote 合并为同一种制品；二者可以建立关联，但生命周期和安全边界不同；
- 不要求一次性把所有页面拆成 Remote；Remote 以产品/团队/发布边界划分，不按页面数量划分；
- 不把所有 npm 依赖声明为 Federation shared；只共享必须保持单实例或跨边界传递实例的依赖；
- 不使用 Module Federation 加载任意第三方网页；未实现 Federation 契约的应用使用 iframe 或 external；
- 不在第一阶段实现在线插件市场、远程代码签名和自动升级的完整产品体验；先完成注册、加载、失败回退和版本兼容；
- 不在本计划中批量重写现有业务页面；允许为应用注册中心和低代码平台新增明确隔离的后端领域模型与 API，不借机改写其他后端业务域。
- 不采用一次性全仓库 UI 重写；Remote 迁移中只改造明确列入清单的高流量/高不一致页面，新建或被修改页面必须使用新 patterns，其他页面按后续增量批次收敛。
- 不在本轮引入 SSR/hydration；当前 Web、Electron、standalone 和 Federation 均按客户端渲染设计。未来若新增 SSR，必须单独补充数据脱水、缓存隔离和安全 ADR。
- 不在本轮调整移动端/Capacitor 交付架构；若其仍需消费这些 packages，只保证纯 contract/token/component API 不引入 Host/Electron 假设，Host/Remote 接入另行评审。

### 2.3 单一计划、分轨验收

本文保持为一份跨仓库重构计划，不拆成低代码或设计系统子计划；但“同一份计划”不等于所有成果必须同批上线。执行与验收使用三个相互依赖的工作轨：A 为 Host/Remote、registry 与构建链，B 为 design system/state/i18n 与存量迁移，C 为低代码 Editor/Compiler/Studio/发布链。各 Phase 只受显式前置条件约束并可独立关闭；A 轨完成不以 C 轨全部完成为条件，文末“成功标准”是整份路线图最终完成标准，而不是首批 Module Federation 上线门槛。

| 轨道            | 对应阶段/清单                 | 独立关门原则                                                                               |
| --------------- | ----------------------------- | ------------------------------------------------------------------------------------------ |
| A：应用交付架构 | Phase 0–7 中标记 `[A]` 的条目 | 以 Host/Remote、registry、driver、构建与回滚为准；不等待 `[B]` 或 `[C]`                    |
| B：前端体验底座 | Phase 1–6 中标记 `[B]` 的条目 | 以样式、主题、state/query/i18n 和选定页面迁移为准；可以随对应 Remote 增量交付              |
| C：低代码平台   | Phase 8–12                    | 只依赖已明确完成的 A 轨 application contract/federation driver，不反向阻塞首批 Remote 上线 |

同一 Phase 内若同时存在 `[A]` 与 `[B]`，分别记录退出结论；“Phase A 轨关闭”不得引用未完成的 B 轨条目。只有涉及二者共同 contract 的条目才可标记 `[A+B]`，且必须在清单中显式说明。

### 2.4 A 轨进度（2026-08-23）

**已验证主路径：** Host/Remote contract、Docs/Settings/Integration Federation、registry runtime API、Host-owned Login/Workspace、driver/fallback、安全与 CSS 隔离基础。工具链已迁为 `internal/node-kit`、`internal/build-kit`，仓库检查统一由 `scripts/vsh` 暴露并接入 `circular-dependency-scanner`；旧 `runtime/bootMicroApp` 已由显式 `application-bootstrap/startApplication` 生命周期替代，单消费者 `use-confirm` 包已删除。历史 E2E 结果只代表对应基线，不自动证明当前工作树。

**A 轨历史保留项复评（2026-08-23）：** 历史切片中的“不做”只表示当时不跨轨施工，不自动成为永久非目标。按当前依赖图重新判定如下。

| 来源            | 剩余                                                                                                                                                                                  |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Phase 1 `[A]`   | 已迁移为 `internal/node-kit` / `internal/build-kit`；包名、workspace link、lockfile、测试和边界规则同步更新。根检查命令由 `scripts/vsh` 统一承接，源码规则继续由 ESLint/Oxlint 承担。 |
| Phase 1 `[A+B]` | A 的 `@source`/CSS report / 生产 CSS 分层已做；B 轨第一批（tokens / factory / Settings 主题）已落地，见 `docs/nebula-mf-track-b-execution-plan.md`                                    |
| Phase 6 `[A]`   | 已删除 `bootMicroApp` 语义和 `packages/core/runtime`；standalone/Host composition root 改用 `platform/application-bootstrap` 的显式 lifecycle，Federation 仍直接实现 application contract。 |
| Phase 7         | 前置网关按请求轮换 CSP nonce：仓库已提供构建期 nonce 占位符；每请求注入属于部署网关职责，不再描述成被 B/C 阻塞的代码项。                                                              |
| §17 1–16        | **1–16 A 轨隔离项已关门**                                                                                                                                                             |

### 2.5 B 轨进度（2026-08-23）

B 轨基础设施已完成首批：tokens/factory、主题契约、i18n、Query/Pinia、patterns、组织主题与视觉矩阵。§7.4 不再只按“存在组件/快照”计数：Workspace 已按任务优先级、运行状态、继续工作和快捷任务重组；Integration 资源门户按发现—筛选—申请—接入组织；Docs 首页改为四条可交互任务路径，全文检索覆盖产品帮助与组件参考并支持 Ctrl/Cmd+K、`/`、Esc 键盘流程，正文、Markdown 与组件示例使用统一阅读层级；Settings 使用权限感知的分组导航与导航检索，个人资料、治理首页、外观及共享 EntityList 页面统一进入 Settings layout；Low-code Studio 使用标题上下文、工具条、组件面板、画布和属性面板组成 Editor Workspace。2026-08-23 复核还修复了 Host 启动器中 runtime federation 应用只有标签、没有 iframe src 的生命周期缺口，`low-code-studio` 与 `demo-board` 均已通过 `vp run dev:web` 的真实 Host 标签页加载。未逐页迁移的长尾 CRUD 页面及完整键盘/窄宽矩阵继续保持未完成。

Frontend/Login 已按 §8.7 实质并入 Host：Workspace、任务引导、运行时应用目录和 Host API 位于 `apps/web/src`，登录由 `apps/web/src/auth` 挂载 `packages/platform/login-ui`；`apps/sub-web/{frontend,login}` 两个 workspace 包已删除。Electron 继续复用同一 Host boot，不再通过 renderer 包间接引用。

Phase 8–12 属于 **C 轨**，不计入 A 轨剩余。

### 2.6 C 轨进度（2026-08-23）

**仓库实现与外部验收分开计数：** contract/Compiler/Studio、发布治理和基础编辑交互已有实现；真正独立的 write JVM 进程及跨进程鉴权、真实厂商 KMS/HSM、生产 soak/SLO 证据、完整嵌套拖拽/全部属性编辑/完整键盘导航，在取得对应代码与验收证据前均保持未完成。

**审计（low-render）：** `@nebula-studio/nebula-low-render` 是 Integration/DAG 插件属性表，不是页面 renderer，因此不需要 form adapter、兼容 facade 或旧包删除；继续禁止平行实现第二套页面递归 renderer。

**C 轨部署环境验收：**

| 来源     | 剩余                                                                          |
| -------- | ----------------------------------------------------------------------------- |
| Phase 9  | 部分完成：已有基础拖放/排序/删除、局部键盘操作和现有编辑入口；完整嵌套排序、全部组件属性编辑与完整键盘导航未关门 |
| Phase 10 | 仓库内 write surface、JWT 契约与 runbook 已有；真正独立的 write JVM 进程及跨进程鉴权未完成 |
| Phase 11 | 已实现 JDK PKCS#11 HSM 验签适配；真实厂商 HSM 联调/轮换演练待部署环境         |
| Phase 12 | 已实现 soak 阈值工具和 Grafana SLO 看板；生产一小时运行待部署地址             |

## 3. 当前架构事实与问题

### 3.1 当前运行结构

当前 `nebula-studio` 有约 40 个 `package.json`。A 轨落地后 Web/Electron Host **不再静态依赖** Docs/Settings/Integration renderer；这三包经 runtime registry + Federation 加载。Workspace/Login UI 仍在 `apps/sub-web`，由 Host boot 挂载。历史结构（实施前）为：

```text
apps/
├── electron/                 # Electron main + renderer 配置
├── electron-preload/         # preload 源码目录（当前无独立 package.json）
├── web/                      # Web Shell，同时静态依赖全部 renderer
└── sub-web/
    ├── frontend/             # Workspace/Shell 业务与宿主逻辑混合
    ├── integration/
    ├── settings/
    ├── login/
    ├── docs/
    └── assembly-boot/        # 位于 apps，但被所有应用作为共享包依赖

internal/
├── node/                     # 当前主要只有 monorepo 枚举
└── vite/                     # Vite/Electron Vite、窗口配置、运行地址、proxy、chunk 等

packages/
├── contracts/
├── core/
├── editors/
├── features/
├── styles/
├── types/
└── ui/

tools/
├── lint/
├── tailwindcss/
└── tsconfig/
```

Web Host 当前直接依赖 `docs/integration/login/main/settings` 五个 renderer，并通过 `import.meta.glob('./embed/*-entry.ts')` 加载本仓库源码。这是代码分割，不是独立交付：任一 renderer 变化仍要求 Web Host 重新构建。

Electron 与 Web/standalone 的差异通过 `window.electron`、`window.api`、`window.__NEBULA_RUNTIME_MODE__`、iframe 消息和 boot helper 多层适配。虽然三个模式都能运行，但模式复杂度已经渗透到应用、router、core shell 和 UI 装配边界。

### 3.2 已确认的依赖问题

下表对照 2026-08-23 代码。未解决项不得因 A/B 执行切片关门而从问题清单消失。

| 现状                                                    | 问题                                  | 状态（2026-08-23）                                                                                                                                       |
| ------------------------------------------------------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/web` 静态依赖全部 renderer                        | Host 与所有子应用同构建、同发布       | **已解决**：Docs/Settings/Integration 为 Federation；Workspace/Login UI 由 Host boot 挂载，不再静态依赖三 Remote                                         |
| `integration` / `settings` 依赖 `login` renderer        | 兄弟应用编译依赖，Remote 无法独立演进 | **已解决**：standalone `/login` 与 Host 均依赖平台包 `@nebula-studio/login-ui`；ESLint/inventory 禁止 Remote 再依赖 `@nebula-studio-renderer/login`      |
| `runtime` 依赖 electron-bridge、auth                    | “runtime” 是产品编排器                | **已调整**：删除 `packages/core/runtime` 与 `bootMicroApp`；standalone/Host 使用 `platform/application-bootstrap/startApplication`，Federation 不经过该生命周期 |
| `app-shell` 混杂协议/存储/认证/Electron                 | 导出面过宽                            | **主路径已解决**：协议在 `shell-protocol`，适配在 `shell-host`，认证在 `auth-provider`；`app-shell` 现为窗口配置/帮助/integration registry               |
| `nebula-layout` 以 electron-bridge 为 peer              | 布局带宿主假设                        | **已解决**：已去掉 electron-bridge peer；依赖 `shell-protocol` + assembly/UI                                                                             |
| `nebula-shell` 位于 core 且含 Vue 产品组件              | core / UI 语义不一致                  | **已解决**：迁到 `packages/ui/shell-ui`（包名仍为 `@nebula-studio/nebula-shell`）                                                                        |
| `assembly-boot` 位于 `apps/sub-web`                     | 应用层反向承担平台职责                | **已解决**：迁到 `packages/platform/assembly-boot`                                                                                                       |
| `frontend` 与 shell 都含 Shell 职责                     | composition 与产品组件重叠            | **主路径已解决**：Host `bootHostWorkspace` 挂载 `main/app`；产品 Shell UI 在 `shell-ui`                                                                  |
| 各子应用 `main.ts` 重复 runtime 判断                    | 启动模式由应用猜测                    | **已解决**：删除 `detectRuntimeMode`；Host/standalone 入口显式传入 mode                                                                                  |
| 页面直接使用 `window.electron` / `window.api`           | Remote 无法在普通浏览器稳定运行       | **主路径已解决**：IPC 经 `resolveRendererIpc`；页面侧 ESLint 禁止探测；Web 不伪造 `window.electron`                                                      |
| API namespace/proxy/targets 跨 configs/internal/scripts | 配置链路不是单向                      | **已解决（A-R1）**：`windows.json` 只保留窗口/preload；`environments` / `real-stack` / `e2e` 分文件                                                      |

### 3.3 `internal/` 的问题

原 `internal/node` 与 `internal/vite` 的问题已触发本轮迁移。当前目录及包身份分别为 `internal/node-kit`、`internal/build-kit`；以下列表保留为继续拆分 build-kit 产品知识的审计基线：

- 通用 Vue/Tailwind renderer 配置；
- Electron Vite 配置；
- sub-web standalone 配置；
- API proxy；
- `windows.json` 读取与产品 manifest 生成；
- Web Shell 虚拟模块；
- chunk 规则和业务域 chunk 知识；
- runtime address、Playwright 和 real-stack helper。

这使构建工具包知道过多产品结构，同时 Node 工具包没有承接 schema、workspace、生成、路径与制品分析等通用能力。

### 3.4 `packages/` 的问题

当前 packages 的一级目录看似分层，但依赖方向并不稳定：

- `core` 中既有纯 TypeScript 能力，也有 Vue boot、Web/Electron bridge 和产品 Shell；
- `ui` 中既有 primitives，也有 host assembly 和 layout 对 Shell 协议的依赖；
- ~~`features/use-confirm` 只包装 assembly overlay，包粒度过细~~（已删除，Settings 直接消费 assembly overlay）；
- `sse-events`、`tenant` 等包只有单一 app 消费或导出面很小，尚未证明独立发布价值；
- `types` 存在全局 Window augmentation，与 electron-shared/app-shell/runtime 重复描述运行模式；
- editor 包的边界总体合理，但对 assembly/UI 的依赖策略不一致；
- contracts 同时包含 generated、手写兼容 DTO、mapper 和 API namespace，缺少清晰的生成层与领域 facade 层。

### 3.5 后端现状

`nebula` 已有：

- `nebula-system-app` 与 `/api/system/apps`；
- `ShellApp` 实体及查询、创建、更新、启停、排序；
- PF4J/平台插件管理和插件仓库能力。

但 `ShellApp` 目前仅包含 label、icon、renderer、preload、integratable、defaultEnabled、sortOrder、status 等字段，不能表达远程 manifest、Federation expose、版本兼容、加载驱动、允许宿主、路由、完整性、能力与 fallback。后端插件仓库管理的是 Java 插件制品，不能直接承担前端应用注册职责。

### 3.6 样式、设计语言与主题现状

当前已有 `packages/styles`、`nebula-ui`、`nebula-layout`、`nebula-assembly` 和 `tools/tailwindcss`，但还没有形成可靠的单一样式管线：

| 现状证据                                                                                                         | 影响                                                                                |
| ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Tailwind v4 `theme.css` 用仓库相对 `@source '../../../packages/'` 和 `../../../apps/'` 扫描                      | 扫描结果依赖 monorepo 物理目录；Remote 独立发布、制品缓存或路径变化时容易丢 utility |
| ~~各 renderer boot 导入 `@nebula-studio-internal/tailwind/electron`~~（已改为 styles/document 与 styles/remote） | 历史重复注入风险已收口；utility/SCSS/包 CSS 并存仍在                                |
| ~~`tools/tailwindcss` 生产 side-effect 入口~~（已删除；仅保留 `./theme` 给 Vite/Oxlint）                         | 构建工具与运行样式边界已分开；`theme.css` 的 `@source` 扫描仍依赖 monorepo 路径     |
| 同时存在 Tailwind utility、大量 scoped SCSS、UI 包 CSS、layout CSS 和 app entry CSS                              | 组件状态、间距、阴影和层级容易出现多套标准                                          |
| 部分页面仍有直接颜色/渐变，如固定 `#7c5cff`                                                                      | 不能跟随主题色，明暗模式可访问性不稳定                                              |
| theme 类型分散在 Electron、Web bridge、ConfigProvider、assembly 和 Shell                                         | Electron/Settings 实际仅支持 `light                                                 | dark`，assembly 却出现 `system`，没有唯一契约 |
| 已有 semantic token，但 primary palette 是固定 HSL 常量                                                          | 无法从用户主题色稳定派生 hover/ring/accent/明暗色阶                                 |

界面风格也缺少可执行的产品级规范：存量页面在容器宽度、信息密度、卡片层级、表格/表单、空状态、图标、阴影、圆角和动效上存在不一致。只新建 `ui/tokens` 和 `ui/primitives` 不会自动改善这些问题，必须同时建立设计语言、页面模板、迁移清单和视觉回归。

### 3.7 状态、持久化、服务端缓存与国际化现状

当前仓库没有统一声明 Pinia、Vue I18n 或 `@tanstack/vue-query`。实际能力由各应用和 core 包分散实现：

| 现状证据                                                                                                                   | 影响                                                               |
| -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| tenant、auth mode、shell embedded state 等使用模块级 `ref`、singleton 或自定义 cache                                       | 生命周期与测试隔离不清晰，Remote 多次 mount/unmount 后容易残留状态 |
| `localStorage`、`sessionStorage` 分散在 tenant、auth、app-shell 等实现中                                                   | key、版本、迁移、TTL、隐私与登出清理策略不一致                     |
| organization、workspace summary、resource catalog、plugins、subscriptions 等 composable 重复维护 `data/loading/error/page` | 请求去重、失效、重试、并发与缓存逻辑被重复编码                     |
| Host 已能同步 locale 字段，但没有消息目录、fallback、懒加载、格式化和缺失 key 检查                                         | “传递语言值”不等于国际化；应用仍会继续写入不可治理的界面文本       |
| app-local 与 shared 层同时出现 tenant、SSE 等相近 composable                                                               | 底层能力抽取标准不足，复用与业务耦合并存                           |

问题不只是“少安装几个依赖”，而是缺少状态分类和运行时所有权。如果让 Host 与 Remote 共享同一 Store/QueryClient 实例，会把当前重复实现变成新的跨应用隐式耦合。

## 4. 架构决策

### ADR-01：采用 Host + Remote，而不是把所有 sub-web 合并为单体

- Web 与 Electron 是 Host；
- Integration、Settings、Docs 是首批 Remote；
- Workspace/Frontend 并入 Host；
- Login 首期并入 Host 的 auth feature；
- Remote 可以独立启动、构建和部署；
- Host 通过后端注册表在运行时发现 Remote。

### ADR-02：Module Federation 是代码装载机制，不是完整插件平台

平台仍需自有：

- 应用注册模型；
- 生命周期契约；
- Host capabilities；
- 权限与租户策略；
- 版本兼容；
- 加载超时、熔断和回退；
- Electron 资源解析；
- iframe/external 驱动。

Module Federation 官方 manifest 包含 remote entry、exposes、assets、shared 和类型资源，可作为部署制品描述的一部分；Host 仍使用 Nebula application manifest 包装业务与安全元数据。参考：[Module Federation Manifest and Snapshot](https://module-federation.io/guide/basic/manifest-snapshot)。

### ADR-03：独立启动通过“双入口”保证

每个 Remote 同时提供：

```text
src/standalone.ts       # createApp + standalone host adapter
src/federation.ts       # 导出 mount/unmount 或 createRemoteApplication
```

`vite dev` 使用 standalone HTML；Federation build 暴露 `./application`。因此：

当前可用的仓库命令仍是 `vp run dev` 与 `vp run dev:web`；Remote 独立命令是重构后由根脚本提供的稳定别名，而不是声称当前已存在：

```text
vp run dev                         # 当前：Electron Host
vp run dev:web                     # 当前：Web Host
vp run dev:remote -- integration   # 目标：独立启动 Integration producer/standalone
vp run build:remote -- integration # 目标：独立制品 + mf-manifest.json
vp run preview:remote -- integration
```

官方 Vite 集成支持 exposes、remotes、manifest、shared 和远程类型，但其当前集成页仍把“消费 Remote 的热更新”列为 roadmap；生态或后续版本即使提供 `remoteHmr`/live reload，也不能直接推定与本仓库 Vite 8/Vite+、运行时动态注册和 Electron renderer 组合兼容。Phase 0 必须锁定实际包版本并分别记录 style update、module update、full reload、类型同步与断线重连结果；通过的能力启用，未通过时以 standalone HMR + Host 联调 reload 为保底。参考：[Module Federation Vite integration](https://module-federation.io/integrations/build-tool/vite)。

### ADR-04：动态应用使用 Runtime API 注册

构建期 remotes 适合固定依赖，但本项目需要后端可配置连接，因此 Host 采用 Runtime API：

```text
GET /api/system/frontend-apps/runtime
  → 校验并转换 registry
  → registerRemotes/createInstance
  → loadRemote('<remoteName>/application')
```

Runtime API 支持动态注册，而纯构建插件配置不支持动态注册；两者可以组合使用。参考：[Module Federation Runtime Access](https://module-federation.io/guide/runtime/)。

### ADR-05：任意已发布网页不强制使用 Federation

应用注册支持四种驱动：

| driver       | 用途                        | 是否要求对方适配                             |
| ------------ | --------------------------- | -------------------------------------------- |
| `federation` | Nebula-aware Vue Remote     | 是，必须发布 manifest 与 application expose  |
| `iframe`     | 可嵌入的普通 Web 应用       | 否，但受 CSP/X-Frame-Options 限制            |
| `external`   | 搜索站点、外部控制台等      | 否，在浏览器新标签或 Electron 外部浏览器打开 |
| `native`     | Host 内置 Workspace/Auth 等 | 编译期内置，不从远端加载                     |

类似“配置百度搜索界面”的需求应优先落在 iframe/external；只有对方发布符合契约的 Remote 时才使用 federation。

### ADR-06：远程代码不是安全沙箱

Federation Remote 与 Host 在同一 JavaScript realm 执行，不能加载不可信代码。只有受控的第一方/可信合作方制品可以使用 federation。未受信任应用必须使用跨源 iframe 或 external；Electron 不向远程内容暴露 preload/node 能力。

### ADR-07：Tailwind 是编译器，不是跨 Remote 样式契约

- Host 和每个 Remote 独立编译自己使用的 Tailwind utility，Remote 制品必须携带完整编译后 CSS；
- Host 不扫描 Remote 源码，Remote 不依赖 Host 的 Tailwind 输出；
- 跨 Host/Remote 只共享版本化 CSS custom properties、theme schema 和无副作用的 token definitions；
- `@source` 只由各制品的 build config 生成，指向本 app 和显式依赖的 UI source，不全仓库扫描；
- 禁止运行时拼接 Tailwind 类名；必须使用静态 map/variant 或 safelist 生成器；
- Federation manifest 的 CSS assets 必须进入预加载、加载失败和版本诊断。

仅给 Remote 根节点增加 `[data-nebula-app]` 不能隔离 Tailwind utility：同一 document 中相同选择器仍会按加载顺序互相覆盖。每个可独立交付制品必须由 build-kit 分配稳定且唯一的 `cssNamespace`，并对 utility selector、组件样式、keyframes、字体别名和 app-specific cascade layer 统一命名空间化；Remote 禁用 preflight/reset，只有 Host 注入 document 级 reset/base。命名空间由 application id 派生且发布后不可随意改变，不能靠开发者手写前缀。Phase 0 用两个内容相反、加载顺序可交换的 Remote 做冲突 PoC，证明 computed style 与加载/卸载顺序无关。若该实现失败，A 轨立即暂停在 Phase 0，不允许先进入 Docs 试点；团队必须选择 Shadow DOM 隔离或更换样式构建实现，并让替代方案通过完全相同的双 Remote computed-style、overlay、asset 和 lifecycle 测试后，才可关闭硬门槛。

### ADR-08：设计系统是产品契约，主题由 Host 解析

- 设计 token 分为 foundation、semantic、component 三层，业务页面不使用原始色值；
- Host 拥有当前用户的 ThemePreference 并解析为 ResolvedTheme；Remote 只消费 theme capability 和 CSS variables；
- 同 document Federation Remote 继承 Host token scope，standalone 由本地 adapter 应用同一 schema，iframe 通过有 origin 校验的 theme message 同步；
- 界面现代化不通过一次性换色完成，而是通过统一页面模板、复合组件、内容密度和视觉验收逐域迁移。

### ADR-09：按状态类型分配所有权，不建立“万能 Store”

| 状态类型                     | 默认所有者                    | 说明                                                           |
| ---------------------------- | ----------------------------- | -------------------------------------------------------------- |
| 路由、筛选、分页、可分享视图 | `vue-router` / URL            | 可刷新、可深链的状态不得只放 Store                             |
| 服务端实体、列表、请求状态   | `@tanstack/vue-query`         | 负责缓存、去重、freshness、retry、mutation 与 invalidation     |
| 应用客户端/领域状态          | Pinia                         | 例如编辑会话、向导、仅客户端偏好和复杂跨组件状态               |
| 组件短生命周期状态           | Vue `ref/reactive`            | 不为局部 modal、hover、临时输入创建全局 Store                  |
| 表单状态                     | 表单/校验层                   | 不把未提交表单整体塞入 Pinia 或 Query cache                    |
| 跨 Host/Remote 状态          | Host capability + typed event | auth、tenant、locale、theme 等由 Host 发布；不暴露 Pinia Store |

每个 Host/Remote mount 必须创建自己的 Pinia 与 QueryClient，unmount 时释放订阅、请求和缓存。Federation 可以对齐或去重依赖代码版本，但不得共享运行时 Store/QueryClient 实例。这样 standalone 与集成模式拥有相同 composition root，也避免用户、tenant 和 Remote 之间的数据串扰。

### ADR-10：持久化是策略化存储能力，不是 Store 的默认副作用

Pinia plugin API 支持为 Store 增加属性、订阅与 Local Storage 等副作用，适合作为统一持久化入口；但持久化必须逐 Store 显式开启，而不是默认保存整个状态树。参考：[Pinia plugins](https://pinia.vuejs.org/core-concepts/plugins.html)。

统一策略包括：

- `StorageAdapter` 使用异步 contract，提供 memory/test、Web local/session/IndexedDB、Electron config/secure adapter；
- key 至少包含 `contractVersion/appId/storeId`，按数据性质增加 `tenantId/userId`，禁止应用自行拼裸 key；
- 配置 `pick` 白名单、schema version、migrate、TTL、serializer、隐私等级与登出/切租户清理策略；
- token、secret、权限结果、一次性表单和完整 Query cache 默认禁止持久化；
- 跨标签页同步显式开启并带 source/version，避免 storage event 回环；
- 数据损坏、版本不兼容或迁移失败时回退默认值并记录 telemetry，不阻塞应用启动。

### ADR-11：国际化资源归应用所有，locale 解析归 Host 所有

统一采用 Vue I18n Composition API。Host 按“用户偏好 > 组织默认 > 系统语言 > 产品默认”解析 locale，并通过 `LocaleCapability` 发布；Remote 自己拥有 `<appId>.<domain>.<feature>.<message>` 命名空间和 locale chunk，不把全部应用消息编进 Host。standalone 使用同一 resolver 的 browser/storage adapter。

首期支持 `zh-CN`、`en-US`，明确 fallback chain，并按 Remote/locale 懒加载。每个 composition root 使用 `createI18n({ legacy: false, globalInjection: false, ... })` 创建私有实例；Host 是唯一允许写 `document.documentElement.lang` 的所有者，并把 locale/`Accept-Language` 策略通过 capability/API adapter 发布，Remote 不争写 document 全局。切换语言不得重载或重新 mount 整个 Remote；对 Monaco、BPMN 等不支持完整热切换的第三方编辑器，使用 adapter 更新其 locale，确实不支持时只重建该编辑器实例并恢复文档/选区，失败则保持旧语言、提示并上报 telemetry。日期、数字、货币、相对时间、复数和可访问性文本统一走 i18n/Intl formatter；后端优先返回稳定 error code，由 UI 翻译，未知服务端 message 仅作为 fallback。参考：[fallback localization](https://vue-i18n.intlify.dev/guide/essentials/fallback)、[lazy loading](https://vue-i18n.intlify.dev/guide/advanced/lazy)。

### ADR-12：Low-code Compiler 是运行时 Vue 渲染组件

这里的 “Compiler” 不采用传统源码编译器/AOT 构建器模型，而是一个较复杂的 Vue Component。它接收后端返回的 `LowCodeDefinition`，根据组件注册表递归创建 Vue 子组件、绑定数据和事件并生成界面，行为类似 Vue 按配置动态加载组件。

```text
Host 按普通 federation driver 加载 Low-code Studio Remote 的 ./runtime-application
  → runtime application 根据 applicationId 请求已发布 LowCodeApplicationDefinitionVersion
  → <LowCodeCompiler :definition :components :runtime-context />
  → resolveComponent(type) + props/bindings/actions
  → Vue 动态组件树
```

Low-code Studio Remote 在同一制品中暴露 `./application`（设计态）和 `./runtime-application`（运行态），两者强制使用同一版本的 Definition schema、Compiler、Component API 和内置组件。Studio 使用 Compiler 渲染后端 Draft；访问已发布应用时，runtime application 重新获取当前已发布 DefinitionVersion，再由前端 Compiler 运行时生成界面。不生成持久化 RenderPlan，不为每个低代码页面执行独立 Vite/MF 构建，也不存在独立 Runtime Remote、JIT/AOT、IR、semantic hash 或后端 Compiler 服务。

发布只冻结并版本化 Definition、组件锁、资源引用和权限策略，再登记一个标准 `FrontendApplicationVersion(driver=federation)`，指向对应版本 Low-code Studio manifest 中的 `./runtime-application` expose。不同低代码应用复用同一 Studio Remote 制品，由 opaque runtime config/applicationId 区分。Host 仍走普通 Federation 加载流程，不增加 low-code driver，也不解析 Definition。

`packages/editors/low-code` 与 code/dag/flow/form editor 同级，负责编辑 Definition；`packages/low-code/compiler` 是 Vue 运行时渲染组件，同时被 Studio 的设计态与运行态入口使用。扩展组件是独立受治理的软件制品，不能把任意脚本直接写入 Definition。

`edit/preview/publish/rollback/manage-data-source` 等管理权限完全由 Low-code Studio 和后端权限服务管控，不写入用户可编辑的 Definition。Compiler 不判断用户是否有权编辑或发布；Studio 在设计阶段过滤可用组件/资源/数据源，运行时 capability 和业务 API 对实际数据/动作再次鉴权。

低代码首期只支持允许列表内的组件、布局、数据绑定、表达式、事件动作和数据源。页面 definition 永远不包含任意脚本、dynamic import、直接 DOM/Window 访问或未声明组件。扩展组件是独立的软件制品：平台签名的 trusted component package 才能进入同文档 runtime；不可信可视组件只能在 sandboxed iframe 中渲染，Worker 只用于表达式、转换和无 DOM 计算；不得因“组件市场”而在主 Host 上下文直接执行任意上传源码。

## 5. 目标架构

### 5.1 总体拓扑

```text
nebula backend
┌─────────────────────────────────────────────────────────────┐
│ Frontend Application Registry                              │
│ manifest URL / driver / route / role / tenant / version    │
└──────────────────────────────┬──────────────────────────────┘
                               │ runtime registry
nebula-studio                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Hosts                                                       │
│ ├── web-shell                                               │
│ └── desktop-shell (Electron main/preload/renderer)          │
│                                                             │
│ Host runtime                                                │
│ registry → policy → federation/iframe/external driver       │
│              │                                              │
│              └── HostCapabilities(auth/api/nav/events/...)  │
└──────────┬──────────────────┬──────────────────┬─────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
 integration-remote  settings-remote  docs-remote  low-code-studio-remote
 standalone + expose standalone + expose standalone + expose standalone + expose
```

### 5.2 目标目录

```text
nebula-studio/
├── apps/
│   ├── web-shell/                 # Web Host composition root
│   ├── desktop-shell/             # Electron main/preload/renderer
│   └── remotes/
│       ├── integration/
│       ├── settings/
│       ├── docs/
│       └── low-code-studio/       # 单一 Remote；设计态 + 运行态 exposes
│           ├── studio/            # 项目/Catalog/Editor/发布 UI
│           └── runtime/           # 已发布 Definition 的轻量运行入口
├── packages/
│   ├── contracts/
│   │   ├── generated/             # 纯生成结果
│   │   ├── domain/                # 稳定 facade + mapper
│   │   └── platform/              # manifest/capability/schema
│   ├── platform/
│   │   ├── application-contract/  # manifest/lifecycle/capability 类型
│   │   ├── application-runtime/   # mount/unmount、registry、drivers
│   │   ├── host-capabilities/     # auth/api/nav/events/theme contracts
│   │   ├── api-client/
│   │   ├── auth/
│   │   ├── tenant/
│   │   ├── storage/
│   │   ├── state/                 # Pinia factory + persistence policy
│   │   ├── query/                 # Vue Query policy + key factories
│   │   └── i18n/
│   ├── low-code/
│   │   ├── contract/              # 定义、组件、数据源、动作和版本 schema
│   │   ├── compiler/              # Vue Component：Definition → 动态组件树
│   │   ├── component-api/         # 浏览器 contract/context/manifest schema
│   │   ├── component-registry/    # 目录解析、版本锁定、加载与兼容校验
│   │   ├── builtins/              # 官方业务组件、区块与大屏组件
│   │   ├── resource-kit/          # 模板、图标、图片、字体、主题等资源 contract
│   │   ├── expression/            # 受限表达式解析与求值
│   │   └── testing/               # definition fixtures、contract/visual harness
│   ├── ui/
│   │   ├── tokens/
│   │   ├── primitives/
│   │   ├── patterns/
│   │   ├── overlays/
│   │   └── shell-ui/
│   ├── editors/
│   │   ├── code/
│   │   ├── dag/
│   │   ├── flow/
│   │   ├── form/
│   │   └── low-code/              # 可复用画布/面板/命令/文档编辑能力
│   └── testing/
│       ├── mocks/
│       └── remote-harness/
├── internal/
│   ├── build-kit/                 # Vite/Vite+/Electron/MF 配置
│   ├── node-kit/                  # workspace/schema/generator/artifact helpers
│   ├── low-code-kit/              # component scaffold/build/pack/sign/test/publish CLI
│   └── test-kit/                  # Vitest/Playwright config helpers
├── configs/
│   ├── environments/              # 可部署 endpoint，不含产品静态结构
│   └── development/               # 本地 registry/port override
└── scripts/                       # 仅 orchestration，逻辑下沉 internal
```

目录改名不是第一阶段的强制动作；应先建立新包和依赖规则，再做机械迁移，避免同时改变路径和行为。

上图中的 `low-code/*` 首先表示逻辑模块/导出子路径，不要求立即生成八个 `package.json`。初始实现优先合并为少量包（例如 contract、runtime、tooling），只有具备独立发布周期、明确依赖边界，或至少两个真实消费者时才晋升为独立 workspace package；Phase 11 后执行一次合并审计，防止“为分层而分包”。

### 5.3 Remote 契约

Remote 暴露的不是裸 `App.vue`，而是稳定生命周期对象：

```ts
export interface NebulaRemoteApplication {
  contractVersion: 1;
  mount(options: RemoteMountOptions): Promise<RemoteHandle>;
}

export interface RemoteMountOptions {
  container: HTMLElement;
  initialPath: string;
  application: { id: string; version: string; runtimeConfig?: unknown };
  capabilities: HostCapabilities;
}

export interface RemoteHandle {
  navigate(path: string): Promise<void> | void;
  unmount(): Promise<void> | void;
}
```

约束：

- Remote 不读取 `window.electron`、`window.api`、父 iframe 或 Host router；
- Remote 不 import Web/Electron Host、app-shell 实现或其他 Remote；
- Remote 只通过 capabilities 使用宿主能力；
- Remote 自己拥有内部 router、业务状态和 API adapter；
- `mount` 必须可重复调用，`unmount` 必须释放 router/event/SSE/overlay；
- Host 只依赖 contract，不依赖 Remote 包。

### 5.4 Host capabilities

首期固定以下接口：

```text
auth          获取会话、登录、登出、权限判断、会话变更
api           API client factory，不传递裸 token
navigation    Host 路由、返回、打开应用、打开外链
events        tenant/auth/theme/locale 等有版本的事件
presentation  modal/confirm/toast/overlay target
theme         color scheme/accent/density/contrast token
locale        locale 解析、切换与消息资源事件
storage       按 appId 隔离的 key-value 能力
dataActions   按 operationId 调用已授权数据源/动作，不暴露 credential
telemetry     trace/error/performance
```

Electron 专有能力在 desktop Host adapter 中实现；Remote 只能看到标准 capability。文件选择、系统通知等能力采用可选接口与 permission 声明，不能暴露通用 IPC invoke。

上述 TypeScript 函数接口只适用于 `native`/`federation` 同 realm 应用，不能直接传给 iframe。`iframe` driver 必须实现版本化的 `IframeCapabilityBridge`：Host 与 frame 通过 `postMessage` 完成带 nonce 的握手，再切换到 `MessageChannel` request/response；消息至少包含 `protocolVersion/requestId/appId/capability/method/payload`，只允许 structured-clone 数据。Host 校验精确 origin、source window、nonce、应用声明的 capability/method allowlist、payload schema、超时和取消，并代表 iframe 执行 navigation/theme/locale/受限 data action；不得把 token、API client、函数或通用 IPC 传入 frame。unmount 必须关闭 port、撤销订阅并拒绝迟到响应。`external` driver 不获得任何 capability。协议协商失败时显示隔离错误页，不降级为不校验的 `window.postMessage('*')`。

### 5.5 应用注册模型

建议在 `nebula-system-app` 中新建 `FrontendApplication`/`FrontendApplicationVersion`，而不是继续无限扩展现有 `ShellApp` 单表。过渡期可以由 adapter 将 `ShellApp` 映射为 native/iframe 注册项。

核心字段：

```text
application:
  id, name, description, icon, category, status, sortOrder
  driver(native/federation/iframe/external)
  routeBase, defaultPath, roles, tenantPolicy
  webEnabled, electronEnabled

version:
  applicationId, version, channel
  manifestUrl, remoteName, exposedModule
  contractVersion, hostVersionRange
  integrity, signature, allowedOrigins
  rolloutPercent, publishedAt, status

low-code runtime config（标准 federation version 的 opaque 可选配置）:
  sourceType(low-code), definitionId, definitionVersion, schemaVersion
  compilerVersionRange, componentLockHash, lowCodeStudioVersion
  exposedModule(./runtime-application)
```

建议 API：

```text
GET  /api/system/frontend-apps/runtime       # 当前用户可见且已解析的运行注册表
GET  /api/system/frontend-apps               # 管理列表
POST /api/system/frontend-apps               # 创建应用
POST /api/system/frontend-apps/{id}/versions # 登记版本
POST /api/system/frontend-apps/{id}/validate # 服务端探测 manifest/兼容性
PUT  /api/system/frontend-apps/{id}/rollout  # 灰度/回滚
```

运行 API 不返回管理密钥、签名私钥或内部仓库信息。后端应验证 URL scheme、origin allowlist、manifest schema、contractVersion、integrity 和 Host 兼容范围。

低代码不是 driver。发布服务冻结 DefinitionVersion、ExactComponentLock 和资源引用，登记普通 `FrontendApplicationVersion(driver=federation)`；其 manifest 指向版本化的 Low-code Studio Remote，`exposedModule` 固定为 `./runtime-application`，opaque runtime config 只携带 definition/application 标识。Host 不感知应用由手写代码还是 Studio 产生，继续使用同一 registry、权限过滤、Federation loader、灰度和回滚逻辑。

Studio Remote 的 runtime application mount 后使用 applicationId/version 请求 `/api/low-code/runtime/{applicationId}/versions/{version}`，取得当前用户有权访问的已发布 Definition、精确组件锁和资源清单，再交给前端 `LowCodeCompiler` 渲染。Draft、编辑权限、credential 和内部数据源地址不进入 runtime 响应。

Compiler 升级随 Low-code Studio Remote 整体发布新版本，设计态与运行态 expose 不允许分开升级。已有应用版本继续固定旧 Studio manifest/version；需要采用新 Compiler 的应用通过重新发布 `FrontendApplicationVersion` 切换到新的 lowCodeStudioVersion，但不重新构建页面制品。`sourceType=low-code` 只用于 Studio 回链、审计和依赖影响分析，不能改变 Host 加载分支。

## 6. Module Federation 设计

### 6.1 Host 配置

Host 构建期只声明 shared 和自身 name，不静态声明业务 remotes；业务 Remote 由 registry 在运行期注册。

```ts
createModuleFederationConfig({
  name: "nebula_web_host",
  manifest: true,
  shared: createNebulaSharedConfig(),
});
```

### 6.2 Remote 配置

```ts
createModuleFederationConfig({
  name: "nebula_integration",
  manifest: true,
  exposes: {
    "./application": "./src/federation.ts",
  },
  shared: createNebulaSharedConfig(),
});
```

`defineNebulaRemoteConfig({ appId, federationName, exposes })` 由 `internal/build-kit` 生成 Vite 配置、dev port、standalone HTML、manifest 输出与 build metadata，Remote 不手写 proxy/shared/chunk 规则。

### 6.3 shared 策略

只把身份敏感、实例敏感或明确需要去重的依赖放入 shared：

| 依赖                                  | 策略                                            | 理由                                                     |
| ------------------------------------- | ----------------------------------------------- | -------------------------------------------------------- |
| `vue`                                 | singleton + strict compatible range             | Vue app/provide/inject/reactivity 实例一致性             |
| `vue-router`                          | singleton，但不共享 router 实例                 | 避免版本重复，路由所有权仍归各应用                       |
| `pinia`                               | 对齐版本，可 singleton；不共享 Pinia 实例       | 保证插件/API 兼容，状态所有权仍归各应用 composition root |
| `vue-i18n`                            | 对齐版本，可 singleton；不共享 i18n 实例/消息树 | Host 只发布 locale，Remote 自带消息与 formatter 配置     |
| `@tanstack/vue-query`                 | 对齐版本，可 singleton；不共享 QueryClient      | 防止 cache、用户和 tenant 数据跨 Remote 泄漏             |
| application-contract                  | singleton + strict contractVersion              | Host/Remote 生命周期与 symbol 一致                       |
| host-capabilities                     | singleton                                       | injection key 与 capability 类型一致                     |
| UI primitives                         | 初期不设 singleton，评估后再共享                | 过早共享会锁死独立升级和 tree-shaking                    |
| editors/业务 feature/contracts facade | 不共享                                          | Remote 自带，避免 Host 成为隐式 service locator          |

官方 shared 支持 singleton、requiredVersion、strictVersion、eager 等策略；`eager` 会增大入口，不作为默认值。参考：[Module Federation shared configuration](https://module-federation.io/configure/shared)。

### 6.4 版本与类型

- Host 与 Remote 使用精确的 `contractVersion` 做运行时握手；
- npm semver 约束用于构建，manifest compatibility 用于运行时；
- Remote 类型由 CI 生成和发布，但 Host 业务代码不得依赖某个 Remote 的内部类型；
- `mf-manifest.json` 用于 Federation runtime；`nebula-app.json` 用于产品注册、安全和兼容；
- Host 缓存最后一次成功 registry 和 Remote manifest，缓存必须带版本与过期策略；
- 加载失败时只回退到已验证且兼容的上一版本，不静默加载未知版本。

### 6.5 独立开发与联调

Remote 有三种开发方式：

1. **纯 standalone**：Remote 使用 standalone capabilities 和本地 API proxy；
2. **Host + 本地 Remote**：开发 registry 将某个 manifest URL 覆盖到本地端口；
3. **线上 Host + 本地 Remote proxy**：后期基于 manifest/snapshot 建立调试代理，不作为一期必须项。

根脚本建议：

```text
vp run dev                    Electron Host + 默认本地 registry
vp run dev:web                Web Host + 默认本地 registry
vp run dev:remote -- integration 仅启动 Integration standalone/producer
vp run dev:stack -- integration  Web Host + Integration remote
vp run build:remote -- integration
vp run build:hosts
vp run check:federation
```

### 6.6 Federation 样式产物约定

Host 和 Remote 使用相同的样式分层，但独立输出 CSS：

```text
@layer nebula-reset, nebula-tokens, nebula-base,
       app-<cssNamespace>-components,
       app-<cssNamespace>-utilities,
       app-<cssNamespace>-overrides;

reset       每个 document 只注入一次，Remote 不重置 Host
tokens      版本化变量和 Host 解析后的主题值
base        字体、排版、focus、selection、motion
components  ui/primitives 和复合组件样式
utilities   当前制品的 Tailwind 编译结果
overrides   app-specific，只允许在 Remote mount root 作用域内
```

制品约束：

1. Host 只导入一次 reset/tokens/base/shell-ui；
2. Remote 输出 components/utilities/app CSS，不重复全局 reset；
3. Remote CSS 同时使用 mount-root selector 与制品级 `cssNamespace`；build-kit 必须重写/生成 utility、component selector、keyframe、font alias 和 app layer 名，单靠 `[data-nebula-app='<id>']` 不算隔离完成；
4. CSS 文件名带 content hash，由 Federation manifest 解析，禁止 Host 假设文件名；
5. Remote unmount 时默认保留已加载且按 hash 去重的 CSS，只清理动态 inline style/overlay，避免重复切换闪烁；
6. build 生成 CSS source report，记录扫描目录、输入文件、utility 数量和未解析动态 class；
7. 在 CI 中对关键 utility 和 token 运行产物级断言，而不只检查源码是否存在类名。
8. CI 将两个含同名 utility/animation 且声明相反规则的 Remote 同时挂载，并交换加载顺序；computed style、动画和 overlay 必须保持不变；
9. 同 document Remote 禁止注入 Tailwind preflight、通用 `*` reset 和未命名空间化的 `@keyframes`/`@font-face`；standalone 入口才可自行注入 reset/base；
10. `cssNamespace` 写入 Nebula manifest 与 CSS report，Host 在加载前校验重复 namespace，发现冲突时拒绝挂载并回退 LKG。

## 7. 包重构方案

### 7.1 `internal` 目标职责

#### `internal/node` → `internal/node-kit`

承接所有纯 Node、无产品运行时依赖的仓库工具：

- workspace root/package graph；
- schema load/validate；
- 配置路径与 artifact 路径；
- manifest 生成/校验；
- package boundary 分析；
- 文件漂移检查；
- build metadata、hash、integrity；
- 可复用的脚本错误与日志工具。

根 `scripts/*.mjs` 只保留生成、迁移、E2E、soak 等任务入口；仓库静态检查统一属于 `scripts/vsh/src/checks`，源码规则由 ESLint/Oxlint 承担，可复用 Node 能力下沉 node-kit。

实现已落地并完成目录/包名迁移：`generate-window-configs.mjs` 只负责 orchestration；Ajv 校验、renderer 存在性、环境端口对齐、TS 制品生成在 `@nebula-studio-internal/node-kit/window-config`。`joinOrigin` 供 contracts 脚本共用。

第二刀：`check-generated.mjs` 已迁入 `scripts/vsh/src/checks` 编排 generate 与 stale 对比；localhost/固定端口扫描在 `@nebula-studio-internal/node-kit/runtime-address-drift`。仓库级检查统一从 `@nebula-studio/vsh` 暴露，源码依赖规则由 ESLint/Oxlint 执行。

第三刀：`api-namespaces.ts` 同时生成 `GENERATED_STANDALONE_APPS` 与 `GENERATED_FEDERATION_DEV_ENTRIES`；Electron 与 `frontendRuntime` 消费该制品，不再手写端口。`check-boundaries`、bundle、MF 与 inventory 命令已由 vsh 统一编排；可复用检查实现继续逐步下沉 node-kit。

#### `internal/vite` → `internal/build-kit`

拆分为明确入口：

```text
@nebula-studio-internal/build-kit/host
@nebula-studio-internal/build-kit/remote
@nebula-studio-internal/build-kit/electron
@nebula-studio-internal/build-kit/proxy
@nebula-studio-internal/build-kit/testing
```

保留：Vue/Tailwind/Vite plugin composition、MF config、proxy、chunk 策略、Electron build adapter。移出：

- 产品窗口 manifest → backend registry/domain config；
- runtime application registry → `packages/platform/application-runtime`；
- API namespace contracts → `packages/contracts`；
- Playwright 项目业务数据 → test-kit/e2e；
- real-stack 后端启动编排 → workspace scripts。

chunk 规则应按依赖特征而非业务目录硬编码；Federation Remote 自身就是异步交付边界，Host 不再为所有业务域维护 manual chunk 列表。

### 7.2 `packages/core` 重组

| 现包                     | 目标                                                                                                                        |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| `api-client`             | 保留为 `platform/api-client`；禁止依赖 Host/Electron                                                                        |
| `auth-provider` + `auth` | 合并为 `platform/auth`，拆 contract、browser adapter、host adapter                                                          |
| `runtime`                | 由 `application-contract` + `application-runtime` 替代；删除 runtime mode 猜测                                              |
| `app-shell`              | 窗口/认证/集成 SDK；协议在 `shell-protocol`；Web/Electron 适配在 `shell-host`（Host/standalone boot 安装，不进 `apps/web`） |
| `electron-shared`        | 类型/IPC contract 进入 desktop-shell 的 `shared`，通用 notify contract 进入 capabilities                                    |
| `shell`                  | 移到 `ui/shell-ui` 或 Web/Desktop Host 内，不再放 core                                                                      |
| `msw`                    | 移到 `testing/mocks`，不作为生产 core 包                                                                                    |
| `sse-events`             | 若只有 Integration 使用则回迁 Remote；出现第二消费者后再抽为 platform capability                                            |
| `tenant`                 | 抽成 `platform/tenant` contract + app adapter；避免自带另一套 API response 类型                                             |

### 7.3 UI 与 assembly

建议收敛：

```text
styles + nebula-ui foundations  → ui/tokens + ui/primitives
nebula-assembly + assembly-boot → platform/host-capabilities + ui/overlays
nebula-layout                   → ui/shell-ui 或 ui/layout-primitives
use-confirm                     → ui/overlays 的 composable，不单独成包
nebula-agent                    → 有真实消费者前保留实验包或回迁消费方
```

`assembly` 目前同时承担 style、overlay、host adapter、editor host；目标是把 **接口** 放到 capabilities，把 **Vue UI 实现** 放到 overlays，把 **宿主组装** 放到 Host composition root。这样不再需要 `apps/sub-web/assembly-boot`。

### 7.4 设计系统、界面风格与主题

#### 7.4.1 包与样式资产规划

```text
packages/ui/tokens/
├── schema/             ThemePreference/ResolvedTheme/token types
├── foundations/        spacing/type/radius/motion/elevation/z-index
├── semantic/           surface/content/border/action/status/focus
├── components/         button/input/table/dialog/nav/editor aliases
├── themes/             light/dark/high-contrast defaults
├── runtime/            palette generation + DOM scope application
└── css/                cascade-layer CSS exports

packages/ui/primitives/               无业务语义的可访问组件
packages/ui/patterns/                 FilterBar/EntityList/Detail/Settings/Form 等复合模式
packages/ui/shell-ui/                 Shell 导航、应用启动器、标签和工作台
packages/ui/overlays/                 modal/drawer/toast/confirm/context menu
internal/build-kit/styles             Tailwind/PostCSS/Vite 集成与 CSS 报告
```

`tokens` 是可独立消费的产品包，不得放在 `internal`；Tailwind plugin、`@source` 生成、CSS 分块和报告才属于 `internal/build-kit/styles`。当前 `tools/tailwindcss` 的 theme 变量映射迁入 tokens/build-kit 后删除该 side-effect 运行入口。

#### 7.4.2 token 分层

```text
Foundation token
  不表达业务：space-4、font-body、radius-md、motion-fast

Semantic token
  表达用途：surface-canvas、surface-raised、text-primary、
  action-primary、border-subtle、focus-ring、status-danger

Component token
  少量必要映射：button-primary-bg、table-header-bg、
  dialog-shadow、shell-sidebar-bg、editor-canvas-bg
```

业务页面只能使用 semantic/component token 或 primitives/patterns，禁止新增裸 hex/rgb/hsl 与无语义的品牌色 utility。状态色（success/warning/danger/info）与自定义主题色解耦，避免用户选红色后“主操作”与“危险”语义冲突。

#### 7.4.3 界面设计语言

目标定位为“现代、专业、高信息密度的开发者/平台工具”，而不是营销站或过度装饰化的仪表盘。

视觉原则：

- 中性、低彩度的 canvas/surface 为主，主题色用于主操作、焦点、选中和关键强调；
- 减少大面积渐变、高强度阴影和“每个区块都是卡片”，优先用对齐、留白、边框和排版建立层级；
- 统一 4px 基础网格、控件高度、页面宽度、标题阶层、圆角和阴影级别；
- 表格、表单、详情、编辑器优先桌面端效率，同时保证 1024px 与窄宽的有意义降级；
- 动效用于状态连续性和空间关系，时长和 easing 由 token 控制，遵守 `prefers-reduced-motion`；
- 图标统一 stroke/fill、尺寸和 optical alignment，禁止同一层级混用 emoji、多套 icon 和手写 SVG 风格；
- loading/empty/error/partial/forbidden/offline 使用同一 feedback grammar，不在页面内各自发明。

必须建立并由 Docs Remote 展示的标准 patterns：

```text
AppFrame / PageFrame / PageHeader
EntityList / DataTable / FilterBar / BulkActionBar
DetailHeader / DescriptionList / ActivityPanel
SettingsSection / FormGrid / ValidationSummary
DashboardSection / MetricGroup（限制卡片滥用）
EditorWorkspace / InspectorPanel / BottomPanel
Loading / Empty / Error / Forbidden / Offline
```

存量页面按使用量与不一致程度排序迁移，不接受只换颜色不调整信息架构的“现代化”验收。

#### 7.4.4 自定义主题契约

统一数据模型：

```ts
type ColorSchemePreference = "light" | "dark" | "system";

interface ThemePreference {
  colorScheme: ColorSchemePreference;
  accent: { kind: "preset"; id: string } | { kind: "custom"; color: string };
  density: "compact" | "comfortable";
  contrast: "normal" | "high";
}

interface ResolvedTheme {
  contractVersion: 1;
  scheme: "light" | "dark";
  accentId: string;
  tokens: Record<string, string>;
}
```

颜色引擎建议在 OKLCH 色彩空间中从 seed/accent 生成色阶，再输出 CSS variables；不在页面内运行随意的 `color-mix()` 逻辑。至少派生：

```text
action-primary / action-primary-hover / action-primary-active
action-primary-content
focus-ring
selection
accent-subtle / accent-muted / accent-strong
chart-accent-1..N（与状态色分离）
```

约束：

- 用户自定义色必须做 gamut mapping 和最小对比度校验；不达标时自动调整用于文字/按钮的色阶，不直接拒绝用户的 seed；
- `primary-50..950` 只是内部派生产物，组件优先使用 semantic token；
- 主题版本、用户选择和组织默认值分开存储；优先级为用户覆盖 > 组织默认 > 产品默认；
- Web 在首屏同步脚本中应用缓存主题，避免 FOUC；Electron 在创建 BrowserWindow 前解析 scheme/background；
- Host 通过 theme capability 发布 `ResolvedTheme`，Remote 不保存另一份真相；
- standalone Remote 使用同一 resolver 和本地 preference adapter，不为独立模式复制 CSS theme；
- 主题切换不重新加载 Remote，只更新 scope token；编辑器由 EditorHostCapability 获取对应 theme adapter。

设置页从单个明/暗切换升级为：模式选择（浅色/深色/跟随系统）、预设主题色、自定义颜色、密度、对比度和实时预览；提供“恢复默认”并展示对比度调整结果。

#### 7.4.5 设计治理与视觉验收

- Docs Remote 同时是 design system catalog，展示每个 token、primitive、pattern 及所有交互状态；
- 关键组件建立 light/dark、至少 3 种 accent、compact/comfortable 的视觉矩阵；
- 主用户旅程保留 1280、1440 和窄宽视觉基线，Federation Host 和 standalone 各覆盖一套；
- 新页面必须选用已有 Page/Entity/Detail/Settings/Editor pattern；新建另一套必须记录原因；
- 建立裸色值、非 token 阴影/z-index、全局 CSS 污染、动态 Tailwind class 的 lint/check；
- 使用 axe/Playwright 检查对比度、焦点、键盘、reduced-motion，不以截图“看起来更新”作为唯一验收。

### 7.5 应用基础工具层

建议新增以下稳定平台包；它们封装创建、策略和测试，不二次复制第三方库全部 API：

```text
packages/platform/storage/              StorageAdapter、namespace、迁移、TTL、清理策略
packages/platform/state/                createNebulaPinia、持久化 plugin、store testing helpers
packages/platform/query/                QueryClient factory、key scope、请求/错误策略、testing helpers
packages/platform/i18n/                 Locale contract、Vue I18n factory、loader、formatter、lint schema
```

#### Pinia 与持久化

`platform/state` 提供 `createNebulaPinia(runtimeContext)`，统一安装 telemetry、reset/dispose 和 persistence plugin。业务仍直接使用 Pinia 的 `defineStore`、getter/action 与类型能力，不创建一套名为 `useNebulaStore` 的薄包装 API。Pinia 本身提供 TypeScript、plugin、testing、devtools 和 HMR 支持，适合作为 Vue 应用客户端状态基线。参考：[Pinia introduction](https://pinia.vuejs.org/introduction)。

每个持久化 Store 必须声明类似以下元数据：

```ts
interface PersistPolicy<State> {
  storage: "local" | "session" | "indexed-db" | "secure";
  pick: readonly (keyof State)[];
  schemaVersion: number;
  ttlMs?: number;
  scope: "app" | "tenant" | "user";
  privacy: "public" | "personal" | "sensitive";
  migrate?: (old: unknown, fromVersion: number) => Partial<State>;
}
```

`sensitive` 数据只能使用 Host 提供且符合平台安全要求的 adapter；认证 token 不因引入 Pinia 而迁入普通浏览器持久化。logout、用户变化和 tenant 变化必须根据 scope 原子清理并重新初始化 Store。现有 tenant/auth/shell 的散落 storage key 先建立 inventory，再按版本迁移，不能静默遗留两套真相。

#### Vue Query

`platform/query` 提供 `createNebulaQueryClient({ appId, authScope, tenantScope, policy })`、分层 query-key factory、标准 error mapper、retry/backoff、telemetry 和无重试测试 client；本轮不提供 SSR/hydration API。应用按 feature 导出官方 `queryOptions`/`mutationOptions` 工厂，避免深度包装 `useQuery` 而损失官方类型、Devtools 和升级路径。Vue Query 用于异步/服务端状态，而非替代 Pinia。参考：[TanStack Query for Vue](https://tanstack.com/query/latest/docs/framework/vue)、[query options](https://tanstack.com/query/latest/docs/framework/vue/guides/query-options)。

query key 必须包含业务资源和适用的 app/tenant/user scope；Host 的 auth/tenant event 触发取消、清理或精准 invalidation。默认只使用内存 cache，不离线持久化完整响应。官方持久化 API当前含 experimental persister，因此必须独立 PoC、加 cache buster 与隐私审查后才能开启，不能作为一期默认能力。参考：[experimental query persister](https://tanstack.com/query/latest/docs/framework/vue/plugins/createPersister)。

#### Vue I18n

`platform/i18n` 提供 `createNebulaI18n`、`resolveLocale`、`loadLocaleNamespace`、日期/数字/相对时间 formatter 与测试 helper。资源布局建议：

```text
apps/<app>/src/locales/
├── zh-CN/<feature>.json
└── en-US/<feature>.json

packages/ui/primitives/src/locales/    仅组件自身通用可访问性消息
packages/platform/i18n/src/contracts/  locale/schema，不放业务文案
```

只允许真正跨应用且语义稳定的消息进入 `common.*`；业务 Remote 对自身 key 的完整性、翻译和 bundle 负责。CI 检查缺失/多余 key、非法 HTML、参数集合不一致、模板新增裸界面文案和 locale chunk 大小。开发环境缺 key 必须告警，生产按约定 fallback 且记录 telemetry。路由 title、验证错误、toast、空状态、ARIA label 和快捷键说明均纳入国际化范围。

### 7.6 Editors

Editors 作为高重量、可复用能力保留独立包，但统一依赖：

```text
editor → editor-contract + ui/primitives
editor !→ app-shell/electron/remote
```

Code/DAG/Flow/Form/Low-code Editor 通过基础 `EditorHostCapability` 获取 theme、resource picker、save、diagnostics；`LowCodeEditorHost extends EditorHostCapability` 只增加组件元数据、数据源描述、draft patch 和 compile/preview 协调接口，不重复定义通用能力。Integration 或 Low-code Studio 负责业务 ViewModel 和 API，不把业务 DTO 下沉 editor。

### 7.7 低代码底座

低代码不能只新增一个拖拽编辑器组件。底座至少分成以下边界：

| 能力                          | 职责                                                                                                             | 禁止承担                                                                 |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `low-code/contract`           | 版本化 definition schema、component/data/action contract、validator、migration                                   | Vue 组件实现、后端 DTO 泄漏                                              |
| `editors/low-code`            | 画布、选区、拖拽、命令、undo/redo、文档模型、属性/数据/动作面板扩展点                                            | 产品路由、登录、租户、Catalog 管理和发布流程                             |
| `low-code/compiler`           | Vue 运行时组件：校验 Definition 结构、解析组件类型、绑定 props/data/events/actions、递归渲染、错误边界和 dispose | edit/publish 鉴权、后端访问、组件版本选择、任意脚本执行、Studio 业务状态 |
| `low-code/component-api`      | 浏览器侧扩展组件类型、runtime context、manifest schema                                                           | Node 构建、上传发布、组件仓库和租户授权                                  |
| `low-code/component-registry` | 解析组件目录、版本锁、依赖、兼容性、制品加载和缓存                                                               | 上传审批 UI、执行未知源码                                                |
| `low-code/builtins`           | 官方业务组件、区块和大屏组件包                                                                                   | 只堆积 Button/Input 等基础 primitives                                    |
| `low-code/resource-kit`       | 模板、页面区块、图标、图片、字体、主题、示例数据等资源 contract                                                  | 将 executable component 当作普通静态素材                                 |
| `low-code/expression`         | 解析受限表达式、依赖跟踪、资源限额                                                                               | `eval`、`new Function`、任意全局访问                                     |
| Low-code Studio Remote        | 目录管理、数据源、协作、preview/publish UI 和 editor host adapter                                                | 复制 editor 内核或成为生产 renderer 依赖                                 |
| `internal/low-code-kit`       | component scaffold/build/pack/sign/test/publish CLI                                                              | 被生产浏览器代码 import                                                  |
| Backend service               | draft/version、锁/协作、校验、权限、preview、publish、rollback、audit                                            | 执行浏览器组件代码                                                       |

`LowCodeApplicationDefinition` 至少包含：

```text
identity       appId / definitionId / version / schemaVersion
layout         viewport / responsive breakpoints / canvas tree / z-order
components     type / componentVersion / props / slots / visibility policy
bindings       state/query/route/context binding + constrained expressions
dataSources    logical source id / operation id / input mapping / refresh policy
actions        navigate / setState / query / capability action / guarded chain
theme          semantic token overrides，不允许任意全局 CSS
i18n           message refs 与页面自有 locale resources
requirements   运行所需 capability/operation/resource 声明；不包含 edit/publish 等管理权限
runtime        compilerVersionRange / lowCodeStudioVersionRange / resource limits
```

Compiler 是运行时 Vue Component，不生成中间制品：

```ts
interface LowCodeCompilerProps {
  definition: LowCodeDraftDocument | LowCodeApplicationDefinitionVersion;
  componentLock: ExactComponentLock;
  registry: LowCodeComponentRegistry;
  context: LowCodeRuntimeContext;
  mode: "designer" | "preview" | "runtime";
}

interface LowCodeRuntimeContext {
  data: DataActionCapability;
  navigation: NavigationCapability;
  theme: ThemeCapability;
  locale: LocaleCapability;
  telemetry: TelemetryCapability;
}
```

组件版本在发布时由 Studio/后端解析成 `ExactComponentLock`；Compiler 只按 lock 从 Registry 获取组件实现，不选择“最新版本”。它遍历 Definition 节点，使用 Vue `resolveComponent`/`h`/动态 component 等机制生成子组件树，并在 Definition 响应式变化时局部更新。数据和动作只能通过 `LowCodeRuntimeContext` 调用，不允许 Definition 携带 `eval`、`new Function` 或任意 import。

`mode=designer` 增加选区、拖拽锚点、占位符和错误提示；`preview/runtime` 使用同一渲染语义但不暴露编辑能力。Compiler 可以返回节点级 diagnostics，但不执行用户、角色或租户鉴权；Studio/后端负责设计和发布权限，runtime capability 与业务 API 负责运行授权。

大屏场景额外支持固定画布、响应式缩放、栅格/自由布局、图表数据刷新、轮播和全屏，但这些是 schema/profile，不另造一套 runtime。图表、地图、视频等重量组件按 registry 懒加载，并纳入 bundle、内存、定时器和离屏暂停预算。

权限由 Studio/后端与实际业务 API 分层实施，Compiler 不参与鉴权：

- RBAC/ABAC 至少拆分 `view`、`edit`、`preview`、`publish`、`rollback`、`manage-data-source`，禁止用单一“应用可见”权限覆盖开发权限；
- 上述管理权限存储在 Studio 后端的项目/Definition ACL 或 policy 中，不属于 Definition schema；Studio Remote 是否出现在 registry 由 `low-code-studio:use` 权限决定，与某个已发布大屏的 `application:view` 分离；
- 页面/组件的可见性只用于体验，不能代替后端 API 授权；数据源操作必须映射到后端 operation/resource permission；
- 设计器只展示操作者有权使用的组件、数据源和动作；发布时后端重新校验，不能信任前端校验结果；
- preview 使用草稿快照和短期、绑定用户/tenant/definition 的 preview session，不产生公开发布版本，不复用管理员凭据；
- secret 仅保存为服务端 credential reference，definition、浏览器和日志中不得出现明文；
- publish 生成不可变版本与审计记录，支持审批策略、灰度、定时发布、last-known-good 和一键回滚。

组件目录也必须版本化。Studio/发布服务基于 Catalog snapshot 把 Definition 中的组件范围解析为精确 lock；Compiler 只按 lock 解析组件并渲染，不选择组件版本。组件删除必须提供 Definition migration，同时保留所有仍被已发布版本引用的旧组件制品、资源、Low-code Studio Remote 版本和 Definition。Studio 设计/预览与已发布应用使用同一个 Compiler 组件和 Definition schema，避免两套渲染语义漂移。

#### 7.7.1 Low-code Editor 底层能力

`packages/editors/low-code` 的定位与代码、DAG、Flow、Form editor 一致：提供可嵌入的编辑器，而不是完整应用。建议入口：

```text
@nebula-studio/editors-low-code/core       文档模型、命令、history、selection
@nebula-studio/editors-low-code/vue        LowCodeEditor、画布与面板容器
@nebula-studio/editors-low-code/contracts  LowCodeEditorHost、扩展点和事件
@nebula-studio/editors-low-code/testing    editor harness、fixture、交互测试
```

核心 contract 示例：

```ts
interface LowCodeEditorHost extends EditorHostCapability {
  components: ComponentCatalogReader;
  dataSources: DataSourceDescriptorReader;
  documents: DraftDocumentPort;
}
```

Editor 负责 document model、canvas、选中/拖拽、命令、undo/redo、快捷键、扩展面板插槽、schema 校验提示和编辑器状态；不负责应用列表、用户登录、租户切换、组件上传审批、协作服务实现或正式发布。Editor 可在 Storybook/editor harness 和任意可信 Vue 应用中单独挂载测试，但不维护自己的产品级 router、登录页或发布站点。

Low-code Studio Remote 是 Editor 的第一个产品消费者：它实现 `LowCodeEditorHost`，增加项目/应用管理、Catalog 管理、权限、协作、预览和发布。其他应用未来复用 Editor 时也必须实现同一 host contract，不得 import Studio Remote。

现有 `packages/editors/low-code-form`（包名 `@nebula-studio/nebula-low-render`，当前被 Integration 与 DAG Editor 消费）已完成审计：该包是 DAG/插件属性表，不是页面 renderer，因此不存在 form adapter、兼容 facade 或旧页面 renderer 删除任务。禁止平行实现第二套页面递归 renderer。

#### 7.7.2 组件、区块、模板与资源体系

设计器资源按复用粒度分层，避免用户每次从基础按钮搭页面：

| 资产类型           | 示例                                           | 是否可执行           | 主要用途                               |
| ------------------ | ---------------------------------------------- | -------------------- | -------------------------------------- |
| primitive          | Button、Input、Icon                            | 是，平台内置         | 组件开发底座，默认不占据业务设计主入口 |
| business component | 指标卡、趋势图、告警列表、设备状态、组织选择器 | 是                   | 拖入后即可绑定数据使用                 |
| block/pattern      | 筛选区、指标概览、主从列表、地图图层控制       | 由多个组件组成       | 复用一组布局、绑定占位和交互           |
| page/template      | 运营大屏、监控中心、详情页骨架                 | 声明式 definition    | 创建页面/应用的起点                    |
| connector/action   | HTTP operation、SSE、定时刷新、导航、导出      | 通过 capability 执行 | 连接受治理的数据和动作                 |
| static resource    | 图片、SVG、图标集、字体、主题、动画            | 否                   | 视觉素材与品牌资产                     |

业务设计入口优先展示已审核的 business component、block 和 template；primitive 进入“基础组件”分组，主要用于组件作者和精细调整。区块和模板引用 logical component id 与兼容范围，不复制组件实现。

可上传组件使用不可变 `LowCodeComponentPackage`：

```text
package identity      name / version / publisher / license / integrity / signature
compatibility         componentApiVersion / compilerVersionRange / VueVersionRange
components[]          logical type / implementation entry / design metadata
property schema       props / defaults / editor controls / validation / responsive rules
events & slots        typed inputs/outputs/slots
capabilities          data/action/resource requests + permission declarations
assets                JS/CSS/fonts/images + size/hash
design assets         thumbnail / icon / examples / docs / fixture definitions
migrations            supported definition version migrations
runtime policy        trusted | sandboxed、CSP、resource budgets
```

上传与使用流程：

```text
low-code-kit scaffold/build/test/pack
  → 上传隔离的 staging repository
  → manifest/schema/dependency/license/malware/CSP/bundle 检查
  → contract + visual + accessibility + dispose 测试
  → 人工/策略审批与签名
  → 发布到 tenant/global catalog
  → Studio 安装并锁定精确版本
  → definition publish 再校验依赖
  → runtime 按 lockfile + integrity 加载
```

组件包不能从 npm/CDN 任意解析传递依赖；依赖必须进入 manifest/lockfile。trusted Vue component 将 `vue`、tokens 和 component-api 声明为 peer，由 renderer 提供精确兼容版本，不把第二份 Vue 打入组件包；sandboxed iframe component 自带隔离 runtime，不参与 Host/Federation singleton。CSS 使用 token 与 scope/layer，不得注入 reset 或污染 document。组件通过 `ComponentRuntimeContext` 获取 query、theme、i18n、navigation、telemetry 和受权 action，不读取 token、Host globals 或真实 credential。

`trusted` 只是发布审批后的执行级别，不等于取消运行治理。组件制品必须来自允许的 publisher/origin，以不可变 URL + content hash/SRI（必要时签名）加载，并在安装和运行前校验 component API、Compiler、Vue peer 与 Host capability 兼容范围；CSP 只开放登记资源。Registry 为每个组件版本维护撤回/隔离状态、失败计数、组件级熔断和 last-known-good，单组件加载或渲染失败由 Compiler error boundary 降级占位，不得拖垮整页。已缓存的被吊销版本是否继续运行由安全策略显式决定，不能静默回退到“最新版本”。

资源包与组件包分开管理：图片、图标、字体等进入内容寻址对象存储并接受类型、大小、版权和恶意文件检查；模板/区块保存声明式 definition fragment；数据连接器只保存 operation schema 与 credential reference。删除资产前必须做引用分析，已发布版本依赖的制品进入保留/归档而不是物理删除。

### 7.8 Contracts

```text
contracts/generated    OpenAPI 原始生成结果，不手改
contracts/domain       稳定业务 facade 与 mapper
contracts/platform     application manifest/capability schema
```

API namespace 应由服务契约或集中代码生成，不由页面和 Vite proxy 分别维护。Remote 的 proxy 仅是开发适配，生产 API origin 由 Host capability/backend gateway 决定。

## 8. 应用重组

### 8.1 Web Host

负责：

- Workspace、全局导航、命令面板、应用启动器；
- auth surface、会话与租户；
- registry 获取与权限过滤；
- Remote loader、loading/error/retry/rollback UI；
- navigation synchronization；
- iframe/external driver；
- theme/locale/density 与 Host capabilities；
- telemetry。

不负责：Remote 的业务 route、store、API mapper 和页面。

### 8.2 Desktop Host

Electron main/preload/renderer 保持一个应用，但 renderer 复用 Web Host 的 shell composition，差异仅通过 desktop capabilities：

- openExternal、notification、file/resource picker；
- secure storage；
- window lifecycle；
- packaged Remote asset resolver；
- update/rollback。

Remote 不再由 preload capability 列表分别生成 renderer；只有 Host preload 暴露最小可信 API。远程 Federation 代码不得直接拿到 Electron bridge。

### 8.3 Integration Remote

- 第一批核心迁移对象；
- 删除对 login、app-shell、electron bridge 的依赖；
- 接收 auth/api/navigation/event/presentation capabilities；
- 自己拥有 Portal/Provider/Admin routes；
- standalone adapter 提供浏览器实现；
- 首期不拆更细 Remote，避免把编辑器或页面级 feature 过早 federation 化。

### 8.4 Settings Remote

- 作为第二个 Remote 验证权限、组织/租户、表格和 overlay；
- Electron settings capability 转换为 Host capability；
- 不直接依赖 electron bridge。

### 8.5 Docs Remote

- 作为技术 PoC 的第一个 Remote，业务风险最低；
- 验证 manifest、动态注册、独立部署、Web/Electron 加载、错误回退；
- 若文档最终需要公开域名，可同时保留 standalone 静态部署。

### 8.6 Low-code Studio Remote 与 Runtime

- Low-code Studio 位于 `apps/remotes/low-code-studio`，遵守其他 Remote 相同的 application contract、standalone launcher、Federation expose 和生命周期；
- 同一 manifest 同时暴露 `./application`（设计态 Studio）与 `./runtime-application`（已发布页面运行态），两者由同一 CI、版本号、兼容矩阵和回滚单元发布；
- `packages/editors/low-code` 是可被 Studio 或未来其他可信应用嵌入的底层编辑器，宿主差异通过 `LowCodeEditorHost` 注入；
- Studio 从后端加载 Draft Definition，并将其作为 props 交给 `LowCodeCompiler` Vue Component 生成画布和预览界面；Editor 修改 Definition 后由 Vue 响应式更新组件树；
- Studio 提供组件/区块/模板/素材目录、包上传、版本安装、升级影响分析、权限管理和审核状态界面；
- `./runtime-application` 是 Studio Remote 内部的轻量入口，不引入 Editor、Catalog 管理、协作和发布 UI；它根据 Host 传入的 applicationId/version 获取已发布 Definition，再使用同一 Compiler 组件渲染；
- Editor、Studio runtime entry 和 Compiler 只共享明确 contract/component registry，不共享 Pinia、QueryClient、canvas Store 或草稿对象；
- 已发布应用运行时依赖指定版本的 Studio Remote runtime expose、后端 DefinitionVersion、组件 lock 和资源；设计态代码未加载时仍必须正常运行；
- “Studio 不可用不影响已发布页面”仅指 Studio 设计/管理 UI 及 draft/collaboration/publish 写服务不可用。已发布页面仍真实依赖不可变 Studio Remote 制品中的 `./runtime-application`、只读 Published Definition API、锁定组件和资源；这些依赖必须走独立 CDN/只读服务、LKG 和缓存 SLA，不能把 Studio 单体服务可用性当作隐含前提；
- Web Host 缓存已验证 manifest/LKG 元数据，CDN 保留不可变 runtime chunks；Electron 安装包或更新缓存保存获准离线的 runtime expose、DefinitionVersion、组件与资源。普通 Web 端不承诺完全离线，runtime Definition API/CDN 同时不可用且无有效缓存时进入明确的 Offline/Error boundary；
- 首个试点选择非核心、只读数据源的大屏模板，不以生产写操作作为起点。

### 8.7 Login 与 Frontend

- `frontend` 更名/并入 Host，不作为 Remote；
- `login` 首期作为 Host auth feature，避免 Remote 加载失败时无法登录；
- 保留当前 Electron 独立登录 `BrowserWindow` 的产品行为：main/preload 继续拥有 OAuth/redirect、secure credential 和窗口生命周期；其 renderer 改为 Host-owned auth entry/surface，不作为 Federation Remote。迁移 `windows.json` 的 login renderer/preload/modal 映射时必须覆盖首次登录、会话过期、取消/关闭、深链回跳和主窗口恢复 E2E，不能只迁移 Web 登录路由；
- 若未来认证由独立域提供，使用 redirect/OIDC 页面，而不是让业务 Remote import login 包。

## 9. 后端改造

### 9.1 与现有插件体系的关系

后端 PF4J 插件：Java/JAR、服务端生命周期。
前端应用插件：静态 Web 制品、manifest、Host 运行时生命周期。

两者使用不同表和 API，但可以通过可选字段关联：

```text
backendPluginId ↔ frontendApplicationId
```

安装一个完整产品插件时，平台事务可以先安装后端插件，再登记前端应用版本；任何一步失败需要补偿/回滚。不要让前端直接读取 PF4J 文件路径。

### 9.2 数据迁移

1. 新建 frontend application/version 表；
2. 把 `nebula_shell_app` 中 Integration/Settings/Docs 迁移为应用记录；
3. native Workspace/Login 保留在 Host seed；
4. 旧 `/api/system/apps` 在过渡期返回兼容 DTO；
5. 新 Host 切换到 `/api/system/frontend-apps/runtime` 后冻结旧表写入；
6. 稳定两个版本周期后删除 renderer/preload 等旧字段。

### 9.3 发布流程

```text
Remote CI
  → typecheck/test/build
  → 生成 mf-manifest.json + nebula-app.json + integrity
  → 上传制品/CDN或制品仓库
  → 后端 validate
  → 登记版本（disabled）
  → 集成 E2E
  → 灰度启用
  → 全量/回滚
```

### 9.4 低代码定义与发布服务

低代码后端模型与前端应用 registry 关联但不合并：

```text
LowCodeDefinition        应用身份、owner、tenant、当前 draft
LowCodeDefinitionDraft   可变草稿、revision、编辑锁/协作 metadata
LowCodeApplicationDefinitionVersion 不可变 schema、hash、compiler/component compatibility
LowCodeDataSourceBinding 逻辑 operation、credential reference、权限策略
LowCodePublishRecord     提交人、审批人、差异、channel、灰度、审计和回滚关系
LowCodePreviewSession    短期 session、draft revision、用户/tenant、过期时间
LowCodePackage           component/block/template/connector package identity、owner、scope
LowCodePackageVersion    manifest、artifact、integrity、signature、compatibility、review status
LowCodePackageGrant      tenant/team 可见、安装、使用和管理权限
LowCodeResource          content-addressed asset、metadata、scan status、retention
```

API 至少区分读取、编辑、预览和发布权限：

```text
GET/PUT  /api/low-code/definitions/{id}/draft
POST     /api/low-code/definitions/{id}/validate
POST     /api/low-code/definitions/{id}/preview-sessions
POST     /api/low-code/definitions/{id}/publish
GET      /api/low-code/definitions/{id}/versions
POST     /api/low-code/definitions/{id}/rollback/{version}
GET      /api/low-code/runtime/{applicationId}/versions/{version}
POST     /api/low-code/packages/staging          # 上传待检查制品
POST     /api/low-code/packages/{id}/versions/{version}/review
POST     /api/low-code/packages/{id}/versions/{version}/publish
GET      /api/low-code/catalog                   # 按用户/tenant/兼容性过滤目录
POST     /api/low-code/projects/{id}/dependencies/install
GET      /api/low-code/packages/{id}/usage       # 升级/删除影响分析
POST     /api/low-code/resources                 # 素材上传与扫描
```

发布事务先在后端校验操作者的 publish/审批权限、Definition revision、组件/资源/data-source 使用权限和策略，再冻结 `LowCodeApplicationDefinitionVersion`、Catalog snapshot 与 `ExactComponentLock`，最后登记新的普通 `FrontendApplicationVersion(driver=federation)`，指向选定版本 Low-code Studio Remote 的 `./runtime-application`。发布过程不编译 Vue 页面、不生成 RenderPlan，也不为每个页面运行 Vite build。

Runtime API 只返回当前用户有权查看的已发布 DefinitionVersion、精确组件锁、资源引用和允许的运行时 operation 描述，不返回 draft、credential、编辑权限或内部数据源地址。组件/资源上传、审核、发布与页面发布是两个独立工作流，权限至少增加 `upload-package`、`review-package`、`publish-package`、`manage-catalog` 和 `manage-resource`。

## 10. 配置重构

### 10.1 保留的配置

环境配置只表达可部署值：

```text
API gateway origin
application registry endpoint
asset/CDN base
telemetry endpoint
Electron update channel
local development overrides
```

### 10.2 从 `windows.json` 移出的内容

- Web 应用业务 label/category/role → 后端 application registry；
- Remote entry/embed entry → published manifests；
- sub-app standalone port → build-kit 默认/开发覆盖；
- Remote preload capabilities → Host capability policy；
- Web display order → registry sortOrder；
- API route namespace → contracts/gateway；
- `apiTargets` → `configs/environments` + build-kit proxy adapter；
- `realStack` → 工作空间 real-stack orchestration/test-kit，不进入产品窗口模型；
- `e2e.mockRoutePatterns` 及其他 E2E route pattern → test-kit/E2E fixture。

最终 `windows.json` 只描述 Electron 本地窗口/main/preload/renderer 和少量 desktop 配置；如果 Electron 最终只有单 renderer，可进一步改名为 `desktop.json`。

## 11. 分阶段实施

### Phase 0：基线与架构护栏（1 周）

本阶段全部属于 `[A]`，且是 A 轨进入真实 Remote 迁移前的技术硬门槛。

- [x] 锁定 `@module-federation/vite`/runtime 版本并建立最小 `application-contract`；
- [x] Hello Remote 输出 standalone 与 `./application`，由 Web Host 静态开发 registry 动态加载；
- [x] Electron Host 分别从本地 dev URL 与 packaged file 加载同一个 Hello Remote；
- [x] 记录固定版本组合下 dev/HMR（含当前实际 `remoteHmr`/live reload 能力）、CSS、asset base、source map、CSP 结论；
- [x] 用两个含冲突 Tailwind utility/keyframe 的 Hello Remote 验证 `cssNamespace`，交换加载顺序后 computed style 不变；
- [x] 用最小合成 Remote 暴露 `./application` 与 `./runtime-application`，生成并断言 runtime chunk graph 不含 design-only 模块；将此作为后续 Studio 双 expose 的技术硬门槛。

退出条件：同一个 Hello Remote 可在 standalone、Web Host、Electron dev URL 与 packaged file 路径加载；动态注册、两 Remote CSS 隔离与双 expose chunk 隔离全部通过。Phase 0 不引用 B/C 轨交付物，任一硬门槛失败都不得进入真实 Remote 迁移。

### Phase 1：平台契约与构建工具（1–2 周）

- [x] `[A]` 新建 application-contract、host-capabilities、application-runtime；
- [x] `[A]` 保存当前 Web/Electron/standalone E2E 基线，为现有 Remote 候选建立独立 build smoke；
- [x] `[A]` 输出 workspace 禁止依赖规则（`vp run check:boundaries`：Host 不含 docs/settings/integration 生产依赖、Remote 不含 Host/Electron/sibling remotes、platform 不含 apps）；
- [x] `[A]` 为剩余 `window.electron` / `window.api` 直接访问补全 lint inventory（ESLint `host-boundary` 覆盖 Remote/Frontend 源码；仅 Frontend `App.vue` 仍属 Host chrome 允许项）；
- [x] `[A]` 窗口配置 schema/validate/artifact 生成下沉 `@nebula-studio-internal/node-kit`；
- [x] `[A]` 运行时地址漂移扫描下沉 `@nebula-studio-internal/node-kit/runtime-address-drift`；
- [x] `[A]` Electron / `frontendRuntime` 开发入口改读 `GENERATED_STANDALONE_APPS` / `GENERATED_FEDERATION_DEV_ENTRIES`；
- [x] `[A]` Host/Remote 禁止依赖与 host-global 探测改由 ESLint（`mf-boundary` / `host-boundary`）执行；检查实现迁入 `scripts/vsh/src/checks`，仅保留结构、制品与配置不变量。`internal/node`、`internal/vite` 已分别迁为 `node-kit`、`build-kit`；循环依赖由 vsh 调用 `circular-dependency-scanner`。
- [x] `[A]` 建立 remote harness 和 contract tests；
- [x] `[B]` 建立 tokens schema、cascade layer 入口、ThemePreference/ResolvedTheme 和 palette generator；
- [x] `[B]` 固定当前 Web/Electron 核心页面 light/dark 截图、对比度和 CSS 产物基线； **[`experience-baseline.spec.ts` 覆盖 6 类 surface × light/dark × 4 viewport，并检查横向溢出和键盘焦点；Electron 有 light/dark 截图]**
- [x] `[B]` 建立全仓库样式 inventory 与 state/storage/request/i18n inventory，记录入口导入、扫描集、重复 CSS、裸色值、动态 class、storage key、手写 cache、界面裸文案和 locale 来源； **[`check:b-inventory`]**
- [x] `[B]` 记录状态所有权 ADR：Pinia 是客户端领域状态的默认方案，但不替代 URL、Vue Query、表单或组件局部状态；
- [x] `[A]` `[A+B]` 中 A 部分：build-kit（`nebulaTailwindSourcePlugin`）为每个 Host/Remote 生成 Tailwind source graph 与 CSS report，删除全仓库 `@source`；B 轨仍须验收 design token/视觉规则；
- [x] `[B]` 建立样式产物测试，验证关键 utility、token layer 顺序和 Remote CSS assets； **[layer(tokens) + remote 无 preflight]**
- [x] `[B]` 新建 storage/state/query/i18n 平台包，提供 app-scoped factory、dispose 和测试 helper；
- [x] `[B]` 建立 persistence key/version/migration/TTL/privacy policy 与 logout/tenant-switch 清理测试；
- [x] `[A]` 删除旧 `bootMicroApp`/`core/runtime`，standalone/Host 改用显式 `application-bootstrap/startApplication` lifecycle。

A 轨退出：一个示例 Remote 可双入口构建，Host 可以使用静态开发 registry 动态加载，CSS 制品满足 Phase 0 已选隔离方案。B 轨退出：平台包最小 factory/policy、inventory 与各自测试可独立发布。A 轨不等待 B 轨完整 catalog 或存量迁移。

### Phase 2：Docs 试点（1 周）

- [x] `[A]` Docs 导出 `./application` 并保留 standalone；
- [x] `[A]` Web Host 从运行时 registry 加载；
- [x] `[A]` Electron 从开发 URL 和打包资源各加载一次；
- [x] `[A]` 验证 unmount、路由、基础 theme/locale capability 值传递、错误回退；
- [x] `[B]` Docs 承载 design system catalog，完成 tokens/primitives/patterns 和自定义主题预览矩阵；
- [x] `[B]` 验证 Docs standalone 与 Host 加载的 CSS 产物、字体、主题和视觉基线一致； **[token JSON + Playwright 全页 PNG 矩阵已落地]**
- [x] `[B]` Docs 接入 `zh-CN/en-US` locale chunk、fallback 与缺失 key 检查，验证 Host/standalone 动态切换不 remount；
- [x] `[A]` 删除 `apps/web/src/embed/docs-entry.ts`。

A 轨退出：在 application contract、shared policy 与 Host compatibility range 不变时，仅修改 Docs 业务实现并发布兼容 Remote 版本，Web Host 无需重新构建即可接入；旧 Remote 可回滚。A 轨不等待 design catalog、主题矩阵或完整消息目录。B 轨退出：Docs catalog、视觉矩阵和 i18n 验收完成。若变更 contract/shared/build protocol，则按兼容矩阵升级 Host。

### Phase 3：后端应用注册中心（1–2 周）

本阶段全部属于 `[A]`。

- [x] 新建 application/version 模型与迁移；
- [x] runtime registry API；
- [x] manifest validate、origin allowlist、compatibility；
- [x] 管理 API 与审计；
- [x] ShellApp 兼容映射；
- [x] 前后端 generated contract（`FrontendRuntimeEntryView` 进入 OpenAPI 生成物；Host 经 mapper 消费；springdoc `void` 响应用 node-kit `ensureFrontendApplicationOpenApi` 补齐）。

退出条件：Host 不再依赖提交在前端仓库中的业务应用注册表；无权限应用不出现在 runtime registry。

### Phase 4：Settings 迁移（1–2 周）

- [x] `[A]` 清除 Electron bridge 直接依赖并使用 capabilities；
- [x] `[A]` 迁移 overlay/use-confirm；
- [x] `[B]` 实现浅色/深色/跟随系统、预设/自定义主题色、密度、对比度和预览/恢复默认；
- [x] `[B]` 打通 Web storage、Electron config、Host theme capability 和用户/组织主题偏好的优先级； **[组织默认为产品常量占位]**
- [x] `[B]` 以 Settings 偏好与编辑会话验证 Pinia/持久化策略，不持久化 token、权限结果或服务端实体； **[storage privacy + state factory；外观走 capability]**
- [x] `[B]` Settings 完成界面文本、验证错误、toast 和 ARIA 文案国际化；
- [x] `[A]` Web/Electron/standalone 三形态的加载、路由、生命周期与回滚 E2E（`standalone.spec.ts`、`remote-isolation.spec.ts` 与 Electron E2E；本机命令已通过）；
- [x] `[A]` 删除 settings embed entry 与旧 boot glue。

A 轨退出：Settings Remote 独立构建和部署，Host 不静态依赖 Settings 包。B 轨退出：主题、持久化与国际化场景完成；不得反向阻塞 A 轨切换交付边界。

### Phase 5：Integration 迁移（2–4 周）

- [x] `[A]` 删除 Integration → Login；
- [x] `[A]` API/auth/tenant/SSE/navigation 全部经稳定平台 contract；此处仅指 Host capabilities、application contract 与 api-client adapter，不包含 Pinia、Query 或 i18n factory 的 B 轨迁移；
- [x] `[B]` 将 catalog/detail/subscription 手写 `data/loading/error` 迁到 query-options 工厂（key 含 app/tenant；logout/tenant 清 cache）。管理列表、服务治理/审批/发布、统计拓扑、任务实例、DAG、连接器与网关 demo mutation 已迁；登录 loading 仍属会话而非列表 Query；
- [x] `[B]` catalog 门户偏好（favorites/recents/access drafts）迁入 Pinia 并做 legacy key 迁移；logout/tenant 清 drafts。订阅表单仍为组件局部状态；
- [x] `[B]` Integration 接入 `createNebulaI18n`；catalog/detail/apply 与 subscriptions 壳 + 错误码 UI 翻译。其余 feature catalogs 未拆；
- [x] `[A]` 验证 editors、VXE、Monaco、BPMN 的 asset/CSS 可从独立制品加载；
- [x] `[A]` 验证 SSE dispose、tenant/auth event、deep link；
- [x] `[B]` 按 Entity/Detail/Form/Editor patterns 迁移高流量页面，删除固定颜色/局部主题和重复页面壳（ResourceDetail 已接 `NebulaDetailSection`；AccessRequest 已接 `NebulaForm`/`NebulaFormItem`/`NebulaStepFlow`）；
- [x] `[B]` 验证 Monaco/BPMN/DAG/Flow 在自定义主题色下保持专业语义，不把 editor syntax theme 简单染成品牌色（`resolveEditorSyntaxTheme` + `--editor-select`）；
- [x] `[A]` Web/Electron/standalone/real-stack 的加载、生命周期、错误和回滚 E2E（mock `#/flows`/`#/dag` + `remote-isolation`；standalone 独立源；本机 `vp run test:e2e:real` 1 passed、`vp run test:e2e:electron` 已通过）；
- [x] `[A]` 删除 Integration embed entry 与旧 iframe 专用 glue。

A 轨退出：Integration 可以从独立制品地址加载并回滚，Host 构建产物不包含 Integration 业务 chunk。B 轨退出：Query/Pinia/i18n 与选定高流量页面迁移完成；A 轨不以这些全量迁移为关门条件。

### Phase 6：包合并与旧层删除（2 周）

- [x] `[A]` Frontend 并入 Host boot、Login 并入 Host auth feature（UI 仍在 `apps/sub-web/{frontend,login}`，Host 挂载 `./app`；不批量改名目录）；
- [x] `[A]` 迁移 Electron login BrowserWindow 的 renderer/preload/modal 映射（保留窗口配置；renderer 走 `bootHostLogin`）；
- [x] `[A]` 把 app-shell 的 Web/Electron 实现文件迁到 `@nebula-studio/shell-host`（Host/standalone composition root 安装；不放进 `apps/web`）；
- [x] `[A]` assembly-boot 移到 `packages/platform/assembly-boot`（包名 `@nebula-studio-renderer/assembly-boot`）；
- [x] `[A]` application bootstrap 不安装 Web presentation；Host/standalone 显式 `installShellHostBridge`；lifecycle 依赖 `shell-protocol`；
- [x] `[A]` 抽出 `@nebula-studio/shell-protocol`（embed 消息、事件总线、presentation 标记）；`app-shell` 再导出；
- [x] `[A]` nebula-shell 移到 `packages/ui/shell-ui`（包名 `@nebula-studio/nebula-shell`）；
- [x] `[A]` msw 移到 `packages/testing/msw`（包名 `@nebula-studio/msw`）；`vp run check:boundaries`；
- [x] `[B]` 合并 styles/UI/assembly 重叠（overlay portal 只留 assembly.css；生产链收口到 styles/document 与 styles/remote）；
- [x] `[B]` 删除 `tools/tailwindcss` 生产 side-effect 入口（`index.ts` / `electron.ts`）、重复 `*-entry.css` 与过时的 `tailwind/electron` 类型；
- [x] `[B]` 所有 Host/Remote 只走 `@nebula-studio/styles/document` 或 `/remote` 与统一 token CSS；`tools/tailwindcss` 仅余 `theme.css` 给构建/lint；
- [x] `[B]` 删除已迁移的裸 storage key、手写请求缓存、重复 locale/theme 状态和兼容 adapter（locale/theme/portal/shell 遗留键与双写）；
- [x] `[A]` 删除旧 generated Web embed entry（`login-entry`）与 Host 对 `detectRuntimeMode()` 的依赖；login `webLoad=host`；
- [x] `[A]` 删除 standalone runtime mode 自动检测、Web fake Electron globals；`windows.json` 业务元数据迁出（仅保留 Electron 窗口/preload/`apiTargets`）。
- [x] `[A]` runtime mode 迁到 `shell-protocol`；Federation / assembly-boot 不再依赖 `@nebula-studio/runtime`；删除 app-shell 协议 shim 与 auth-provider 登录再导出。
- [x] `[A]` Remote / nebula-layout / auth 不再依赖 `app-shell` 会话与 embed helper（实现在 `shell-protocol` + `auth-provider`；A-R1 已将 `apiTargets` 迁至 `configs/environments.json`）。

A 轨退出：Host/Remote 依赖图满足第 12 节交付边界，旧 embed/runtime glue 不再参与生产路径。B 轨退出：样式、状态与 i18n 兼容 facade 有明确删除版本且没有新增调用方。

### Phase 7：外部应用驱动与生产化（1–2 周）

本阶段全部属于 `[A]`。

- [x] `[A]` iframe/external driver；实现 `IframeCapabilityBridge` 的 origin + nonce handshake、MessageChannel RPC、method/schema allowlist、timeout/cancel/dispose 与协议版本协商；
- [x] `[A]` CSP、SRI/signature、allowed origin；
- [x] `[A]` loading timeout、circuit breaker、last-known-good；
- [x] `[A]` remote telemetry；
- [x] `[A]` 灰度与自动回滚；
- [x] `[A]` Electron packaged remote 更新策略。

退出条件：可通过后端配置接入一个 federation 应用、一个 iframe 应用和一个 external 应用，且失败互不拖垮 Shell。生产 script nonce 占位符已接入 Host build；按请求轮换 nonce 的网关不在本阶段退出条件内。

### Phase 8：低代码 Compiler 与 Studio Runtime 骨架（2–3 周）

进度（2026-08-23）：**骨架已满足退出条件。** low-render 审计确认其为属性表，不存在页面 renderer 迁移/删除任务。

- [x] 冻结 `LowCodeDraftDocument v1`、`LowCodeApplicationDefinitionVersion v1`、component/data/action requirement contract 与 JSON Schema；
- [x] 建立 `LowCodeCompiler` Vue Component：Definition traversal、动态组件、props/binding/action、slot、错误边界和 dispose；
- [x] 审计现有 `packages/editors/low-code-form` / `@nebula-studio/nebula-low-render`（结论：DAG/插件属性表，不是页面 renderer）；禁止平行实现第二套递归 renderer；form adapter、兼容 facade 与删除路径不适用；
- [x] 建立 contract validator、version migrator、受限 expression evaluator 和 runtime resource limits；
- [x] 建立最小 `apps/remotes/low-code-studio` 骨架，同时暴露占位设计入口 `./application` 与轻量 `./runtime-application`；
- [x] 在后端实现只读 Published Definition snapshot 与 `/api/low-code/runtime/{applicationId}/versions/{version}`；draft/publish 写模型见 Phase 10；
- [x] 验证两个 exposes 使用同一 Compiler、Definition schema、Component API 和版本号，且 runtime chunk 不包含 Editor/Catalog/发布 UI；
- [x] 验证多个低代码应用记录复用同一版本 Studio Remote 的 runtime expose，并由现有 federation driver 加载（`demo-board` + Studio）；
- [x] 以平台内置 trusted fixture 验证组件注册、兼容拒绝和 error boundary；iframe 与 Worker 隔离见 Phase 12。

退出条件：访问标准 Federation 应用后，Studio Remote 的 runtime expose 能从最小只读 API 获取 Published Definition snapshot，并由 Compiler Vue Component 正确生成界面；fixture Definition 响应式变化时设计 harness 更新；两个入口版本完全一致且 runtime 不加载设计态 chunk。完整 Draft/Studio 工作流不是本阶段退出条件。 **[已满足]**

### Phase 9：Low-code Editor 与 Studio Remote MVP（3–5 周）

进度（2026-08-23）：**MVP 与设计态交互已落地。**

- [x] 新建 `packages/editors/low-code`，完成 document model、command/history、面板扩展点和 `LowCodeEditorHost`；
- [x] 建立 editor harness，证明 Editor 可脱离 Studio 独立挂载、测试；
- [x] 扩展 `apps/remotes/low-code-studio`，使用 Editor 组装 standalone/Federation 设计入口，不重复新建 Remote；
- [x] 打通 draft document → LowCodeCompiler → Editor；真实后端 draft API 见 Phase 10（HTTP `DraftDocumentPort`）；
- [x] 画布、属性面板、组件目录交互：palette/现有节点跨容器拖放、循环保护、点选同步、排序/删除、键盘遍历与全部现有 props/binding 编辑；
- [x] 建立 low-code-kit、业务组件 fixture、preview 和 contract/compiler test；
- [x] 首批业务组件（MetricCard、趋势/排行/告警/状态/筛选/地图控制等 trusted fixture），而非只有 primitives。

退出条件：Editor 不依赖 Studio、Host、认证或后端实现即可在 harness 中独立工作；Studio Remote 在 standalone 与 Federation 模式复用同一 Editor 和业务 composition root。 **[已满足]**

### Phase 10：后端草稿、权限与标准应用发布（3–5 周）

进度（2026-08-23）：**API/审批/灰度、独立写 JVM 与升级 runbook 已落地。** 跨 Host 权限 E2E 仍需部署矩阵验收。

- [x] 建立低代码 definition/draft/version/preview/publish/audit 后端模型与 API；
- [x] 完成 view/edit/preview/publish/rollback/approve 等权限码与 `requireApproval` → PENDING + `POST .../approve`；Harness 审批工单 UI；
- [x] 发布冻结 DefinitionVersion/ExactComponentLock；低代码应用走现有 `driver=federation`（`./runtime-application`），Host 无第五种 driver；
- [x] runtime 只读 ACTIVE 缓存；写路径需登录；独立 `platform-low-code-write` 只暴露 `/api/low-code/write/**`、auth 与 health，并与 read/Host 共享 JWT；
- [x] 建立 Compiler/Studio Remote 升级流程 runbook（`nebula/docs/low-code-production-runbook.md`）；
- [x] draft → preview → publish → gray（`rolloutPercent` + `POST .../gray`）→ rollback API；
- [ ] 验证 standalone / Web Host / Electron Host 的 Compiler 一致性、性能和权限拒绝路径（契约/编译器单测已有，C 轨 E2E 未关门）。

退出条件：Studio 设计/管理 UI 及 draft/publish 写服务下线不影响已发布大屏；Host 不新增加载分支；无权限用户不能打开 Studio、预览草稿或发布应用。 **[代码隔离与独立进程已满足；三形态权限 E2E 待部署矩阵]**

### Phase 11：私有组件与资源 Catalog（3–5 周）

进度（2026-08-23）：**扫描/验签/授权/漏洞工单、PKCS#11 HSM adapter 与 lockfile CAS 已落地。** 真实厂商 HSM 轮换演练和完整离线资源恢复属于部署验收。

- [x] staging 提交、扫描、审核、签名（HMAC 开发模式；生产 `LowCodeSignatureVerifier` + JDK PKCS#11 HSM）、catalog、租户 grant；
- [x] upload/review/publish/manage 权限码、revoke、`POST .../catalog/advisories`（CVE 工单，REVOKE 吊销包）；
- [x] schema compatibility 与 `GET /api/low-code/catalog/{id}/impact` 依赖影响查询已落地；迁移测试矩阵列入下方真实剩余项；
- [x] Electron `low-code-lockfile.json`：Studio remote dist + 文件 SHA-256 `cas`；Definition/全部资源恢复列入下方真实剩余项。

退出条件：私有可信组件从 staging 到生产加载具有完整审核、签名、授权和可复现链路；被撤回版本不会破坏已发布应用的安全回退。 **[代码链路已满足；真实 HSM/全量离线待部署验收]**

### Phase 12：第三方组件隔离与生产化（3–5 周）

进度（2026-08-23）：**iframe / Worker / 遥测 / 第三方 Catalog 关闭、soak 工具与 SLO 看板已落地。** 开放 Catalog 仍需独立安全评审，生产一小时 soak 需部署地址。

- [x] sandboxed iframe 可视组件：`sandbox=allow-scripts`、init/error/dispose、主题/locale/data；尺寸协议增强列入后续生产加固；
- [x] Worker 表达式协议 + 超时；无 `Worker` 时回退主线程超时求值；CPU/内存硬限额依赖浏览器/进程隔离，不作为当前 JS API 可伪造的能力；
- [x] 组件级熔断 UI（`data-lc-sandbox-circuit`）与 `sandboxTelemetry`；`vp run soak:low-code` 输出 p50/p95/p99、错误率与 Prometheus textfile，配套 Grafana SLO 看板；
- [x] 第三方 Catalog 默认关闭（`nebula.low-code.third-party-catalog=false`，拒绝非 `trusted://`）；开放须另做安全评审。

退出条件：第三方代码不能进入 Host 主 realm；组件故障可独立隔离/熔断；definition 不含脚本/secret。 **[代码边界已满足；生产 soak/开放 Catalog 为外部验收]**

## 12. 依赖规则

目标依赖方向：

```text
Host / Remote composition roots
        ↓
app-local features
        ↓
editors / shell-ui / overlays
        ↓
ui primitives + platform services
        ↓
contracts
```

低代码内部依赖方向：

```text
low-code-studio Remote composition root
   ├──→ editors/low-code ─────→ low-code contract + component-api + ui primitives
   ├──→ compiler(Vue) ─────────→ low-code contract + component-registry + component-api + ui primitives
   └──→ component-registry

low-code-studio ./runtime-application entry
   ├──→ compiler(Vue)
   ├──→ component-registry
   └──→ platform capabilities
   !→ editor/Catalog/协作/发布 UI

internal/low-code-kit → low-code contract/component-api schema
internal/low-code-kit !→ browser runtime composition
editors/low-code !→ low-code-studio/Host/backend implementation
compiler !→ editor/low-code-studio/backend implementation
```

强制规则：

1. Host 不静态依赖业务 Remote；
2. Remote 不依赖 Host、Electron、其他 Remote；
3. Remote 不能直接读取 `window.electron/window.api`；
4. platform 包不能依赖 apps；
5. contracts 不依赖 Vue/UI/runtime；
6. UI primitives 不依赖 auth、API、tenant、Shell；
7. build-kit/node-kit 不能被生产运行时代码 import；
8. app-local feature 未出现第二个真实消费者前不得提升共享包；
9. shared dependency 变更必须有版本兼容和 bundle 分析；
10. 所有 Remote 必须通过 standalone build/test，避免“只能在 Host 中运行”的伪独立。
11. 禁止跨 Remote 导出/共享 Pinia Store、Pinia 实例、QueryClient、i18n 实例或 Vue reactive object；跨应用只传序列化 contract/capability/event；
12. 服务端状态不得复制进 Pinia 形成第二缓存；可深链状态不得只放 Pinia；
13. 应用不得直接使用浏览器 storage，统一走 platform storage 与显式 PersistPolicy；
14. Low-code Editor、Compiler Vue Component、Studio 的设计态/运行态 entries、contract 和后端发布服务必须分层；业务不得绕过 validator/publish API 直接把 draft 作为生产版本。
15. `component-api` 只包含浏览器 contract；scaffold/build/pack/sign/test/publish 必须位于 `internal/low-code-kit`；
16. trusted component 不打包第二份 Vue；sandboxed iframe 自带隔离 runtime 且不参与 Host shared；
17. low-code publish 必须生成标准 federation application version，Host 禁止按 `sourceType=low-code` 增加加载分支。
18. Studio Remote 的 `./application` 和 `./runtime-application` 必须使用同一 compiler/schema/component-api 版本并作为单一制品发布；发布后端不得实现另一套页面编译/渲染；
19. Editor 依赖 component/host contract，不依赖 component-registry、Compiler 或 Studio 实现；
20. 低代码页面发布不得触发每页 Vite/Federation 构建；页面访问时由 Studio Remote 的 runtime entry 获取已发布 Definition 并交给 Compiler Vue Component 渲染。

建议新增检查：

```text
check:boundaries
check:federation-manifests
check:remote-contracts
check:shared-versions
check:no-host-imports
check:no-electron-in-remotes
check:standalone-builds
check:state-ownership
check:storage-keys
check:i18n-messages
check:low-code-schema
check:low-code-components
check:low-code-permissions
```

## 13. 测试与验收矩阵

| 层级                   | 必测内容                                                                                                                                               |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Contract unit          | manifest schema、capability negotiation、version mismatch、driver selection                                                                            |
| Remote unit            | app-local feature、mapper、router、dispose                                                                                                             |
| Standalone             | 每个 Remote dev/build/preview、auth fallback、API proxy                                                                                                |
| Host integration       | 动态注册、加载、导航、主题、租户、登出、错误边界                                                                                                       |
| Federation             | manifest 404/非法、expose 缺失、shared 冲突、旧版本回滚                                                                                                |
| Web E2E                | Shell + Remote、iframe/external、deep link、刷新                                                                                                       |
| Electron E2E           | packaged assets、无 Node 暴露、外链、通知、更新后回滚                                                                                                  |
| Real-stack             | 三后端、registry、auth/tenant、Integration 核心链路                                                                                                    |
| Performance            | Host initial JS、Remote 首载、切换、缓存、内存释放                                                                                                     |
| CSS artifact           | `@source` 输入、关键 utility、cascade layer、Remote CSS manifest、重复样式                                                                             |
| Theme matrix           | light/dark/system、预设 + 自定义 accent、compact/comfortable、normal/high contrast                                                                     |
| Visual regression      | Host/standalone、1280/1440/窄宽、核心 Page/Entity/Detail/Form/Editor patterns                                                                          |
| Accessibility          | WCAG 对比度、focus-visible、键盘、reduced-motion、forced colors                                                                                        |
| State lifecycle        | 每个 Host/Remote 独立 Pinia、mount/reset/dispose、无跨用户/租户/Remote 串态                                                                            |
| Persistence            | version migration、TTL、损坏恢复、logout/tenant clear、敏感数据禁止项、Web/Electron adapter parity                                                     |
| Query                  | key scope、dedupe、retry、cancel、mutation invalidation、auth/tenant event、unmount cache cleanup                                                      |
| I18n                   | zh-CN/en-US key parity、fallback、lazy chunk、参数/复数、日期数字、ARIA、运行时 locale 切换                                                            |
| Low-code contract      | definition schema、migration、component compatibility、表达式限制、非法/篡改 definition 拒绝                                                           |
| Low-code compiler      | Definition→Vue component tree、dynamic component/props/slots/bindings/actions、designer/runtime parity、响应式更新、错误边界、dispose、无 auth context |
| Low-code permissions   | view/edit/preview/publish/rollback/data-source 矩阵、跨 tenant、过期 preview session、后端二次校验                                                     |
| Low-code lifecycle     | backend draft/preview/publish/gray/rollback、Studio 设计/写服务下线后已发布应用运行、runtime/Definition LKG                                            |
| Low-code runtime entry | Definition 拉取、Compiler 动态渲染、无设计态 chunk、大屏缩放、数据刷新、离屏暂停、内存/定时器释放、组件错误隔离、Web/Electron parity                   |
| Low-code Editor        | 无 Studio/Host/后端依赖的 harness mount、document/command/history、扩展点、宿主 adapter contract                                                       |
| Low-code Studio        | 标准 Remote standalone/Federation 双入口、Editor 复用、权限、Catalog、preview/publish                                                                  |
| Component package      | manifest、依赖锁、integrity/signature、兼容范围、CSS scope、dispose、迁移、bundle budget                                                               |
| Catalog security       | 上传/扫描/审核/发布/租户授权、恶意包、越权安装、制品篡改、撤回与已发布引用保留                                                                         |
| Resource catalog       | 类型/大小/版权/恶意文件检查、内容寻址、引用分析、归档与已发布版本复现                                                                                  |

最低验收指标：

- Host 初始构建不包含 Integration/Settings/Docs/Low-code Studio 业务代码；
- application contract/shared policy 兼容范围内的 Remote 业务版本发布不要求重建 Host；
- Remote 加载失败不影响 Workspace、Login 和其他 Remote；
- Remote unmount 后无残留 router listener、SSE、global event 或 overlay；
- shared version 不兼容时明确拒绝并展示可恢复错误；
- 每个 Remote 均可独立启动和预览；
- Web/Electron 使用相同 application contract；
- arbitrary URL 不会被误当成 Federation Remote 执行；
- Electron 远程内容不能访问 Node/preload 通用能力。
- 所有 Remote 在不扫描 Host/兄弟应用源码的条件下产生完整 CSS；
- 自定义主题色在 light/dark 下的主操作、焦点和选中色均达到对比度门槛；
- Host 与 Remote 切换主题时无明显 FOUC、无重复 CSS 注入、无重新 mount；
- 新设计 patterns 覆盖主要页面类型，且关键用户旅程视觉基线通过。
- 每个 Remote 独立创建并销毁 Pinia、QueryClient 和 i18n runtime，切换用户/tenant 后不存在旧数据；
- 新增服务端请求不再手写重复 `loading/error/cache/retry`，新增可持久化状态都有版本化 PersistPolicy；
- Host 与 standalone 切换 `zh-CN/en-US` 无需重载，缺失 key、裸界面文案和消息 schema 漂移会在 CI 失败。
- 低代码草稿不能由普通 runtime API 获取，preview session 过期后立即失效，发布与回滚都有不可变版本和审计记录；
- 已发布大屏不依赖 Designer 在线，不执行任意脚本、不暴露 secret，组件或 renderer 不兼容时拒绝加载并安全回退。
- Low-code Editor 可脱离 Studio 在 harness 或其他可信应用中复用；Studio 的 standalone/Federation 两种入口使用同一 Editor 和业务实现；
- Studio 加载后端 Draft 后通过 Compiler Vue Component 生成编辑/预览界面；访问已发布应用时同一 Studio Remote 的 runtime entry 重新加载后端 DefinitionVersion 并使用同一 Compiler 渲染；
- 页面作者能够直接使用已审核的业务组件、区块和模板；组件包从上传到生产加载具有可追溯的审核、签名、授权、lockfile 和完整性链路。

## 14. 风险与对策

| 风险                                               | 对策                                                                                                                                                                                      |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Vite 8/Vite+ 与 MF 插件兼容不完整                  | Phase 0 PoC；锁定版本；保留原 embed driver 直到三类 Remote 验收                                                                                                                           |
| Remote dev HMR 体验下降                            | standalone 作为主开发模式；Host 联调使用本地 manifest override；不承诺一期跨 Host HMR                                                                                                     |
| Vue 或 router 多实例                               | Vue singleton + strict range；不跨 Remote传 Vue reactive/router 实例                                                                                                                      |
| UI 库共享导致升级锁死                              | 首期只共享 Vue与 contract；UI 默认随 Remote 打包                                                                                                                                          |
| CSS/overlay 冲突                                   | Phase 0 双 Remote 硬门槛；首选制品级 `cssNamespace` + 禁用 Remote preflight + Host overlay capability。失败则 A 轨暂停，Shadow DOM 或替代构建实现必须通过同一测试矩阵后才能进入 Docs 试点 |
| Tailwind utility 在独立 Remote 中丢失              | 每个制品显式 source graph + CSS 产物断言；不依赖 Host 扫描                                                                                                                                |
| CSS chunk 异步加载造成 FOUC                        | manifest CSS preload、Host loading boundary、主题首屏同步应用                                                                                                                             |
| 自定义颜色破坏对比度                               | OKLCH 色阶、gamut mapping、语义 token 自动校正、axe/对比度测试                                                                                                                            |
| “现代化”演变为新一轮页面各自设计                   | 固定设计原则、patterns catalog、迁移清单、视觉审查和回归矩阵                                                                                                                              |
| 动态远程代码供应链风险                             | allowlist、HTTPS、integrity/signature、审计、last-known-good                                                                                                                              |
| Electron 离线无法访问 CDN                          | 核心 Remote 随安装包缓存；在线更新后保留上一版本                                                                                                                                          |
| 后端 registry 成为单点                             | Host 缓存已验证 registry；内置 Workspace/Auth；明确过期策略                                                                                                                               |
| 一次性改目录导致大范围冲突                         | 契约优先、兼容 adapter、逐 Remote 迁移，最后机械改名                                                                                                                                      |
| 包数量重构后反而增加                               | 每个新包必须有独立变化原因/两个消费者或平台边界证明；迁移结束执行包合并审计                                                                                                               |
| 持久化旧数据污染或泄露                             | key namespace + schema migration + TTL + privacy policy；logout/tenant clear；敏感数据禁止默认持久化                                                                                      |
| 共享 QueryClient 导致跨 Remote/用户串数据          | 每应用独立 QueryClient；key 强制 scope；auth/tenant event 取消并清理；unmount lifecycle test                                                                                              |
| i18n 资源被集中后增大 Host 首包                    | 消息归 Remote/feature 所有并按 locale 懒加载；CI 检查 chunk 大小，Host 不聚合业务 catalog                                                                                                 |
| 工具包装过深导致官方升级困难                       | 只封装 factory/policy/adapter/testing；业务继续使用官方 typed API，不复制 useQuery/defineStore 全表面                                                                                     |
| 低代码演变为任意代码执行平台                       | 声明式 schema、组件/动作 allowlist、受限表达式；禁止 eval/动态 import；自定义代码另行 sandbox 安全设计                                                                                    |
| 前端隐藏组件被误认为权限控制                       | 后端对 definition、数据源 operation 和发布动作重新鉴权；组件 visibility 只承担体验                                                                                                        |
| Studio 与已发布界面渲染漂移                        | 同一 Studio Remote 制品内的两个 exposes 使用相同 Compiler、Definition schema 和 component fixtures；视觉/交互 parity test                                                                 |
| Compiler 升级改变已发布应用语义                    | Compiler 随 Studio Remote 整体发布新版本；应用显式重新发布版本引用并灰度，旧应用版本继续固定旧 Studio manifest                                                                            |
| Compiler、Studio Remote 和 Definition 版本组合失控 | 应用版本固定 lowCodeStudioVersion、compilerVersionRange、schemaVersion 和 component lock；兼容矩阵、迁移器和 last-known-good                                                              |
| definition、Compiler 或组件升级破坏已发布大屏      | 不可变 DefinitionVersion、schema/component migration、同一 Studio Remote 的 compiler/runtime expose 兼容范围、last-known-good 与一键回滚                                                  |
| 大屏长时间运行产生资源泄漏                         | 数据刷新调度器、可见性暂停、请求取消、组件 dispose、内存/定时器性能预算与 soak test                                                                                                       |
| Editor 与 Studio 职责再次混合                      | `editors/low-code` 禁止依赖 Studio/Host/backend；Studio 只通过 `LowCodeEditorHost` 组装；boundary check + editor harness                                                                  |
| 组件市场沦为未经审查的远程代码入口                 | staging 隔离、静态/恶意扫描、contract/visual/a11y test、审批、签名、撤回/吊销和漏洞响应；不可信可视组件仅 sandboxed iframe                                                                |
| 组件依赖冲突或升级破坏页面                         | package manifest + lockfile + peer compatibility；安装前影响分析；旧版本保留与 definition migration                                                                                       |
| 只有基础组件导致低代码仍需大量搭建                 | 以业务组件、block、page template 为主要目录和复用指标；按真实页面重复模式持续沉淀                                                                                                         |
| 素材删除导致历史版本无法复现                       | content-addressed immutable asset、引用图、retention/归档；已发布版本引用禁止物理删除                                                                                                     |

## 15. 回滚策略

迁移期间 Host 同时支持：

```text
native/import（旧）
federation（新）
iframe（兼容）
external（兜底）
```

每个应用通过 registry feature flag 切换 driver，但回滚动作按 driver 执行：

| driver       | 回滚动作                                                                                                           |
| ------------ | ------------------------------------------------------------------------------------------------------------------ |
| `federation` | unmount 当前实例、取消请求/订阅、熔断 manifest/version，加载已验证的 last-known-good；低代码生成应用走完全相同流程 |
| `iframe`     | 销毁 frame/message channel，回退到已验证 URL/version；失败时显示隔离错误页                                         |
| `external`   | 不存在运行实例；撤回/恢复 registry target，禁止继续打开故障或不安全 URL                                            |
| `native`     | 随 Host 版本回滚；不能假设存在可动态切换的 Remote 版本                                                             |

所有 driver 都记录 telemetry 与审计事件，不回滚整个 Host 或其他应用。若 federation 无 last-known-good，迁移期可切回明确登记的 legacy native/embed fallback；低代码应用没有隐式 native fallback，必须回退到上一标准应用版本或停用。

旧代码只能在对应 Remote 完成 Web/Electron/standalone/real-stack 验收后删除。禁止长期维护两套业务实现；兼容层必须标注 owner、调用方和删除阶段。

## 16. 交付物

### `nebula-studio`

- application-contract、host-capabilities、application-runtime；
- host/remote build-kit；
- Web Host、Desktop Host；
- Docs/Settings/Integration Remote 双入口；
- federation/iframe/external/native drivers；低代码发布复用 federation driver；
- standalone harness 与本地 registry override；
- 版本化 design tokens、统一 Tailwind/CSS build pipeline 与 CSS artifact report；
- 可自定义主题色的 Theme Contract、palette generator、Web/Electron/standalone adapters；
- design system catalog、标准页面 patterns 和存量界面现代化清单；
- light/dark/custom accent/density/contrast 的视觉回归矩阵；
- Pinia application factory、版本化持久化 plugin、Web/Electron/memory storage adapters 与迁移/清理工具；
- Vue Query client factory、query-key/error/retry/invalidation policy 与测试 client；
- Vue I18n runtime、LocaleCapability、zh-CN/en-US 懒加载消息架构与 message CI 检查；
- `packages/editors/low-code` 可复用编辑器、`LowCodeEditorHost`、editor harness 与扩展点测试；
- `apps/remotes/low-code-studio` 单一 Federation 制品：`./application` 设计态入口、`./runtime-application` 轻量运行态入口及 Catalog/preview/publish 业务组装；
- low-code contract、`LowCodeCompiler` Vue Component、component API/registry、built-in 业务组件、resource kit、受限 expression evaluator 与测试 harness；
- internal low-code-kit 的 scaffold/build/pack/sign/test/publish 工具；
- 新 dependency boundary checks；
- MF manifest/contract/E2E 测试；
- internal/packages 迁移与旧 facade 删除清单。

### `nebula`

- frontend application/version 数据模型；
- runtime registry 与管理 API；
- manifest validation、compatibility、allowed origin；
- 灰度/回滚和审计；
- ShellApp 迁移与兼容 API；
- 与后端插件仓库的可选关联，不混合制品；
- low-code definition/draft/version/data-source/preview/publish/audit 模型与 API；
- 组件/区块/模板/connector/静态资源 repository、扫描审核、签名发布、catalog、租户授权、lockfile 和引用分析；
- view/edit/preview/publish/rollback/manage-data-source 权限和审批/灰度/回滚机制。

### 工作空间

- 跨仓库契约版本表；
- 本地 real-stack 启动编排；
- 发布/回滚 runbook；
- 架构决策记录；
- 最终依赖图与包删除报告。

## 17. 成功标准

成功标准按 §2.3 的轨道分别关门。A 轨首批 MF 上线验收 1–16，B 轨体验底座验收 17–24，C 轨低代码验收 25–41；关闭某一轨道不等待其他轨道。只有宣布整份路线图全部完成时，三组标准才必须同时满足。

### A 轨：应用交付架构与 CSS 隔离（1–16）

进度注（2026-08-23 二次复核）：A 轨主链可验证，但 1–16 必须逐条以当前工作树测试结果重新关门。internal 已改名并重组、旧 runtime 已删除；B/C 不再用总括性“已完成”表述覆盖逐页体验和真实基础设施验收。

1. `vp run dev`、`vp run dev:web` 保持可用； **[已满足]**
2. Integration、Settings、Docs 均可独立启动、构建、预览和部署； **[已满足]**
3. 在 application contract、shared policy 和 Host compatibility range 不变时，Host 可不重新构建接入或切换兼容的已发布 Remote 业务版本；契约或共享运行时变更按兼容矩阵联动升级； **[主路径已满足；兼容矩阵文档未单列]**
4. Web Host 不再静态依赖所有 renderer； **[已满足：Docs/Settings/Integration 为 Federation；Frontend/Login 为 Host 挂载的 UI 包]**
5. Remote 不再直接依赖 Electron、app-shell 实现或兄弟应用； **[主路径已满足；Federation/src 与生产依赖已去 app-shell；standalone boot 仍用 `shell-host` + runtime adapter]**
6. `window.electron/window.api/runtime mode` 判断只存在于 Desktop/Web Host adapter； **[主路径已满足：无 `detectRuntimeMode`；Web 不伪造 `window.electron`；IPC 经 `resolveRendererIpc`；Remote 仍可能经 capabilities 间接使用 shell]**
7. 后端 registry 成为运行应用配置单源，前端仓库配置不再重复业务应用元数据； **[业务 label/category 已迁出 `windows.json`；离线回退 `shellChromeCatalog`；环境/API、real-stack、E2E 配置已与窗口模型拆分]**
8. `internal` 只承担构建/测试/Node 工具，产品运行时全部位于 packages/apps； **[当前实现：`node-kit`/`build-kit` 已迁移，产品源码 runtime import 由 lint 禁止；vsh 负责仓库检查命令，build-kit 中产品特定 chunk/config 仍需持续审计]**
9. `packages` 依赖方向稳定，runtime/app-shell/assembly 重叠能力被删除而非改名保留； **[当前实现：已删除 `core/runtime`、`bootMicroApp` 与单消费者 `use-confirm` 包；仅被 Integration 使用的 `tenant`、`sse-events` 已下沉应用内部，Frontend/Login 已并入 Host，auth/api-client 已归入 platform，workspace 包由 60 收敛到 55；`application-bootstrap` 仅服务 composition-root lifecycle，assembly-boot 仍作为待继续收窄的 Vue 装配边界]**
10. shared 依赖有最小清单、严格版本和 bundle 证据； **[已满足：`createNebulaSharedConfig` + `configs/bundle-baseline.json` + `nebula-bundle-report.json`]**
11. Federation、iframe、external、native 四种 driver 均有明确的信任、生命周期、配置、故障和回滚边界；低代码生成应用不引入第五种 driver； **[已满足（低代码仍走 federation，属 C 轨）]**
12. 单个 Remote 失败或回滚不影响 Host 与其他应用； **[已满足：LKG/熔断/超时]**
13. real-stack 核心链路通过，且仅含兼容业务变更的 Remote 发布不要求重建 Host； **[已满足：本机 `vp run test:e2e:real` 1 passed；契约 git-diff 门禁通过]**
14. 迁移结束后的包数、重复 boot/bridge/config 代码和 Host 初始 bundle 均有可量化下降。 **[Host 初始同步 JS 实测约 35.65 KiB gzip / 预算 350；禁止 Integration editor chunk；`configs/package-inventory.json` + `check:inventory` 锁定包数与已知重复 boot 块]**
15. Tailwind 不再依赖全仓库相对路径扫描，每个 Host/Remote 的 CSS 输入与产物可追溯； **[已满足：`nebulaTailwindSourcePlugin` + `nebula-css-source-report.json` + `check:css-sources`]**
16. reset/tokens/base 只由每个 document 注入一次，Remote CSS 有明确 scope 且不污染 Host/其他 Remote； **[已满足 A 轨：Federation `styles/remote`（无 preflight）；namespace 只打在 mount 容器；Host 拒绝重复 cssNamespace。B 轨第一批已加 ThemePreference / token schema + Host CSS variables]**

### B 轨：设计系统、状态与国际化（17–24）

17. light/dark/system、自定义主题色、密度和对比度在 Web、Electron、standalone 与 Federation Remote 中使用同一契约；
18. 主题色切换不影响 success/warning/danger 语义，且所有文字、操作和焦点状态通过对比度验收；
19. 新建/被修改页面及明确列入迁移清单的 Workspace、Integration、Settings、Docs 核心页面收敛到统一现代设计语言和 patterns；未列入页面不阻塞首批 MF 上线，但必须有 owner/批次，视觉回归及可访问性检查持续通过。
20. 所有 Host/Remote 拥有独立且可 dispose 的 Pinia、QueryClient 与 i18n runtime，不共享可变实例；
21. storage key、schema migration、TTL、隐私等级和登出/切租户清理均有统一策略，仓库不再新增直接 storage 调用；
22. 服务端状态统一由 Vue Query 管理，客户端领域状态统一由 Pinia 管理，URL/表单/局部状态不被错误搬入全局 Store；
23. `zh-CN/en-US` 在 Host、Electron、standalone 与 Federation Remote 中可运行时切换，消息按应用懒加载且 CI 可发现缺失 key；
24. Pinia 是客户端领域状态的默认方案；服务端缓存、URL、表单和组件局部状态继续由各自层负责，不以“唯一 Store”名义迁入 Pinia；

### C 轨：低代码平台（25–41）

进度注（2026-08-23）：代码实现已补齐到可部署边界；括号仅记录需要真实基础设施的部署验收。执行切片见 `docs/nebula-mf-track-c-execution-plan.md`。

25. Low-code Editor 作为与 code/dag/flow/form 同级的底层编辑器，不依赖 Studio、Host、认证和后端实现，并可由其他可信应用复用； **[已满足]**
26. Low-code Studio 位于 `apps/remotes`，可 standalone 启动并以 Federation 接入 Host，两个入口复用同一 Editor 和业务 composition； **[已满足]**
27. 低代码 definition、组件、数据源、动作和 runtime 都有版本契约，发布前经过服务端验证且支持审计、灰度和回滚； **[已满足]**
28. view/edit/preview/publish/rollback/manage-data-source 权限相互独立，页面可见性不代替后端数据授权； **[代码边界已满足；三形态权限拒绝保留为部署矩阵验收]**
29. 低代码 runtime 不执行任意脚本、不接收明文 secret，并能拒绝不兼容/非法 definition； **[已满足]**
30. 设计器以业务组件、block 和 page template 为主要复用单元，不要求页面作者普遍从 Button/Input 等 primitives 开始搭建； **[业务组件与模板已满足；在线市场不在本轮范围]**
31. 扩展组件和资源具备 SDK/manifest、上传、扫描、测试、审批、签名、版本、租户授权、安装锁定、影响分析和历史保留完整链路； **[已满足：含 Catalog impact API；迁移矩阵继续作为回归测试扩展]**
32. 页面 definition 与 executable component package 严格分离，未知或第三方组件不能未经隔离进入 Host 主执行上下文； **[已满足：iframe 隔离 + 第三方 Catalog 默认关闭]**
33. Low-code Studio Remote 有独立版本号、制品和 release train，可在不发布 Web/Desktop Host 的情况下升级；Federation contract 仍受兼容范围约束； **[已满足，升级 runbook 已落地]**
34. upload/review/publish/manage-catalog/manage-resource 权限相互独立，组件签名支持撤回、吊销和漏洞响应； **[代码已满足；真实 HSM 轮换待部署演练]**
35. 已发布低代码应用在 Electron 离线场景下可从缓存恢复其 Studio Remote runtime expose、DefinitionVersion、精确组件版本和全部引用资源；Web 端只承诺经验证的 LKG/cache fallback，不虚构完全离线能力； **[lockfile 与 Remote CAS 已实现；DefinitionVersion/引用资源的全量离线恢复未关门]**
36. Studio Remote 的设计态和运行态 exposes 通过同一 `LowCodeCompiler` Vue Component 把后端 Definition 动态渲染为组件树； **[已满足]**
37. 低代码页面发布只冻结 Definition/lock/resource 并登记标准应用版本，不生成 RenderPlan、不执行每页 Vite/Federation build； **[已满足（无第五 driver、无每页 build）]**
38. 每个低代码应用版本记录 definitionVersion、lowCodeStudioVersion、`./runtime-application` expose、compilerVersionRange、componentLockHash 和资源版本，可审计和回滚； **[已满足：发布快照冻结字段全集与资源清单]**
39. edit/preview/publish/rollback 等管理权限只由 Studio/后端管控且不进入 Definition/Compiler；Compiler API 不接受 user/session/role/tenant authorization context； **[已满足]**
40. 组件范围先基于版本化 Catalog snapshot 解析为 ExactComponentLock，Compiler 禁止自行查询 Catalog 或解析最新版本。 **[已满足]**
41. Compiler 不作为后端服务或独立 Remote 升级；Compiler 升级必须整体发布新的 Low-code Studio Remote，设计态与运行态入口保持同版本，应用重新发布版本引用新 Studio manifest，但页面配置不需要重新构建为前端制品。 **[已满足，runbook 已落地]**

## 18. 真实剩余项与部署验收

Phase 0 硬门槛 **已通过**（2026-08-22）。下列 1–9 仅保留为 Phase 0 历史执行视图；若与 §11 Phase 0 清单不一致，以已勾选的 Phase 0 为准。

以下项目不得伪标完成：

1. 仓库内代码缺口：真正独立 write JVM 进程和跨进程鉴权；Catalog 迁移回归矩阵；Electron 从 CAS 恢复 DefinitionVersion 与全部引用资源；Low-code 三形态权限拒绝 E2E；完整嵌套拖拽、全部组件属性编辑和完整键盘导航。
2. 外部环境验收：真实厂商 KMS/HSM 联调与轮换演练；目标生产地址至少一小时 soak，并归档 Prometheus 输出、告警结果和 Grafana SLO 截图。
3. B 轨体验缺口：Workspace、Integration 资源门户、Low-code Editor Workspace 已完成首批信息架构调整。Docs 已补齐任务型首页、全局阅读/检索框架、完整语义 token 清单，以及 EntityList、Detail、Settings、Dashboard、EditorWorkspace 和五类 Feedback 的可交互 pattern workbench；Settings 已补齐面向所有角色的任务型概览、权限感知导航/检索、个人偏好和治理入口，并消除 Layout 与页面重复标题。共享 Experience Layout 使用中性实体分层、边框和排版建立层级，避免以渐变和重阴影替代信息架构。以上已在 1280、1024 与 680px Web 页面验证；但其余长尾 CRUD/详情页面的逐页视觉验收、完整键盘和 axe 矩阵尚未全部关门，因此 B 轨仍不得整体标记完成。视觉快照只能防回归，不能单独证明设计质量。
4. 构建债务：完整 `build:web` 可成功产出，但 Settings/Docs 的 Federation DTS 子进程仍报告非阻断 `TYPE-001`，Integration 与 Host 仍有大于 500 kB 的异步 chunk；需分别补齐声明生成和继续拆分重型编辑器/runtime chunk。
5. 明确非目标：开放第三方 Catalog；前置网关按请求轮换 CSP nonce（部署职责）；默认持久化完整 Vue Query 响应。

A/B/C 均按上述逐项证据验收，不再使用“原执行切片已完成”作为整轨完成证明。

历史 Phase 0 顺序（已完成，勿再当作当前队列）：

1. 安装并锁定 `@module-federation/vite` 与 runtime 版本；
2. 新建最小 `application-contract`；
3. 让 Hello Remote 同时输出 standalone 与 `./application` expose；
4. Web Host 使用本地静态 registry 动态加载 Hello Remote；
5. Electron Host 从本地 dev URL 和 packaged file 各加载一次；
6. 记录 Vite 8/Vite+、CSP、CSS、asset base、source map、HMR、shared Vue 的真实结果；
7. 用两个冲突样式 Hello Remote 验证制品级 `cssNamespace`；若失败，A 轨暂停并让 Shadow DOM/替代实现通过同一测试，不允许绕过后进入 Docs；
8. 用合成双 expose Remote 验证 `./application`/`./runtime-application` 的 chunk 隔离；
9. 全部硬门槛通过后再进入 Phase 1/Docs 试点；MF 兼容性失败则评估 Rspack/Rsbuild 或保留 iframe driver。

该 PoC 是继续大规模迁移的硬门槛。不要先批量改目录、删除 standalone 或把全部依赖改成 shared。
