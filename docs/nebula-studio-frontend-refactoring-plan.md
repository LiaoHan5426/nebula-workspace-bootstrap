# Nebula Studio 前端架构现状与增量重构计划

> 文档版本：v3.0
> 最后更新：2026-08-01
> 代码基线：`nebula-studio@5a36a7e09787889607d53ddea65b3e25b98b5397`
> 本文只描述当前代码和剩余增量工作；已完成的历史阶段不再作为待办重复保留。

## 1. 当前结论

Nebula Studio 已完成宿主、窗口配置、preload、认证、运行时、基础布局、主要产品界面和测试分组的基础重构。下一阶段不需要再次搬迁目录，而应集中解决：

1. 真实后端栈尚未通过；
2. generated contracts 业务采用不完整；
3. Integration 的 feature 主要仍是应用内边界；
4. MFA/恢复只有前端状态容器，后端契约未实现；
5. Settings 存量实体页面和跨应用真实数据仍需收口。

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

### F0：真实栈尚未通过（P0）

最后一次记录的真实运行在 `platform-console` 缺少 `ConfigService` Bean 处失败；当前后端源码已有候选装配，但没有当前 HEAD 的启动证据。本次审查只执行了 Playwright test listing，没有重新运行真实栈。核实装配并在必要时修复后，必须重新执行 `vp run test:e2e:real`。

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

“测试已列出”不等于“测试在当前提交全部通过”。仓库文档记录的历史通过结果可作为回归参考，但完成报告必须附本次实际命令和退出码。

## 9. 增量实施顺序

### Phase A：恢复真实栈

- [ ] 修复 Platform Console Context；
- [ ] 三后端应用健康检查；
- [ ] 在线生成契约无漂移；
- [ ] real-stack 完整通过。

### Phase B：契约和真实数据

- [ ] 迁移 Platform/System/Integration contracts；
- [ ] Portal/Settings/Camel 关键路径使用真实响应；
- [ ] 组织/租户切换与跨应用失效测试；
- [ ] 新 API 禁止手写重复 DTO。

### Phase C：应用内边界收敛

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
- 在真实数据闭环前继续扩大视觉组件数量。

## 12. 成功标准

前端重构真正完成应满足：

1. 三平台应用真实栈持续通过；
2. 后端字段漂移在生成、编译或 E2E 阶段被阻止；
3. Portal、Provider、Admin 和 Settings 使用真实数据与权限；
4. Web 与 Electron 共用窗口、认证、租户和 API 定义；
5. App-local feature 边界清晰，共享包只来自真实复用；
6. AuthFlow 的 MFA/恢复由真实后端状态机驱动；
7. Mock、体验、Electron 和 real-stack 各自承担明确且不互相替代的责任。
