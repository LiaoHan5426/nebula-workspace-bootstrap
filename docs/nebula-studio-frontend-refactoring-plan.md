# Nebula Studio 前端架构分析与重构方案

## 1. 现状分析

### 1.1 项目定位

Nebula Studio 是 Nebula 平台的管理控制台前端，采用 **Monorepo + Electron + Web** 双启动模式：

- **Electron 模式** (`apps/electron`)：桌面客户端，支持离线运行、系统级能力集成
- **Web 模式** (`apps/web`)：浏览器访问，单页应用通过 iframe 嵌入子应用

### 1.2 当前架构概览

```
J:/Code/nebula-workspace/nebula-studio/
├── apps/
│   ├── electron/              # J:/Code/nebula-workspace/nebula-studio/apps/electron
│   ├── electron-preload/      # J:/Code/nebula-workspace/nebula-studio/apps/electron-preload
│   ├── web/                   # J:/Code/nebula-workspace/nebula-studio/apps/web
│   └── sub-web/               # J:/Code/nebula-workspace/nebula-studio/apps/sub-web
│       ├── frontend/          # @nebula-studio-renderer/main
│       ├── integration/       # @nebula-studio-renderer/integration
│       ├── settings/          # @nebula-studio-renderer/settings
│       ├── login/             # @nebula-studio-renderer/login
│       └── docs/              # @nebula-studio-renderer/docs
├── packages/                  # J:/Code/nebula-workspace/nebula-studio/packages
│   ├── contracts/             # OpenAPI 生成契约（scripts/generate-contracts.mjs）
│   ├── core/app-shell/        # Shell 运行时 SDK
│   ├── core/shell/            # Shell 页面容器组合
│   ├── features/plugin-installer/
│   └── ui/nebula-ui/
├── internal/vite/             # defineNebulaConfig、standardApiProxy
└── e2e/                       # Playwright 验收（含 g5-smoke.spec.ts）
```

### 1.3 Electron Preload 层分析

Electron Preload 是 Electron 安全架构的核心，负责在主进程（Node.js）与渲染进程（浏览器）之间建立安全的 IPC 桥梁。

#### 当前 Preload 结构

| 包名                              | 作用域   | 暴露的 API                                                                                                                    | 依赖                                           |
| --------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `@nebula-studio-preload/main`     | 主窗口   | `shell.openLogin`、`auth.*`（login/getSession/establishSession/logout）、`notify.*`（app/system/onApp/respond/onAppResponse） | `@electron-toolkit/preload`、`electron-shared` |
| `@nebula-studio-preload/docs`     | 文档窗口 | `notify.*`（仅 notify bridge，无 auth）                                                                                       | `@electron-toolkit/preload`、`electron-shared` |
| `@nebula-studio-preload/settings` | 设置窗口 | `settings.*`（getTheme/setTheme/onThemeChanged）                                                                              | `@electron-toolkit/preload`                    |

#### Preload 与窗口的绑定关系

```
app.config.ts (shellPresentationConfig)
    │
    ├── windows.main     → preload: 'main'    → @nebula-studio-preload/main
    ├── windows.docs     → preload: 'docs'    → @nebula-studio-preload/docs
    ├── windows.settings → preload: 'settings'→ @nebula-studio-preload/settings
    └── windows.integration → preload: 'main' → @nebula-studio-preload/main（复用）
```

#### 问题分析

1. **代码重复严重**：三个 Preload 脚本中 `contextBridge.exposeInMainWorld` 逻辑完全相同，仅 API 定义不同
2. **Notify Bridge 重复**：`main` 和 `docs` 都实现了 notify bridge（app/system/onApp/respond/onAppResponse），但 IPC 通道名不同（`notify:app` vs `notify:bridge:app`）
3. **类型定义分散**：`preload.d.ts` 仅存在于 `main` 和 `docs`，`settings` 缺少类型声明
4. **新增窗口需手动创建 Preload**：违反开闭原则，每次新增子应用都要创建新的 Preload 包

---

## 2. Code Review Graph 架构分析结果

### 2.1 社区结构（Communities）

通过 code-review-graph 的 Leiden 算法检测，nebula-studio 识别出 **18 个代码社区**：

| 社区名称             | 节点数 | 内聚度 | 主导语言   | 说明                                           |
| -------------------- | ------ | ------ | ---------- | ---------------------------------------------- |
| `api-handle`         | 545    | 0.21   | Vue        | API 处理逻辑（集中在 integration 子应用）      |
| `utils-setup`        | 125    | 0.22   | TypeScript | 工具函数与初始化逻辑                           |
| `web-shell`          | 97     | 0.29   | TypeScript | Web 壳层核心（shell-entry、presentation 安装） |
| `modules-window`     | 79     | 0.27   | TypeScript | Electron 窗口管理模块                          |
| `crypto-generate`    | 61     | 0.36   | TypeScript | 加密相关工具                                   |
| `utils-node`         | 60     | 0.30   | TypeScript | Node 环境工具                                  |
| `src-theme`          | 33     | 0.21   | TypeScript | 主题管理                                       |
| `composables-toggle` | 30     | 0.04   | Vue        | 组合式函数（内聚度低，需重构）                 |
| `src-api`            | 26     | 0.28   | TypeScript | API 客户端封装                                 |
| `rules-nebula`       | 25     | 0.26   | TypeScript | 代码规范规则                                   |
| `src-app`            | 21     | 0.00   | TypeScript | 应用根组件（内聚度为 0，分散严重）             |
| `configs-sort`       | 18     | 0.40   | TypeScript | 配置排序工具                                   |
| `components-handle`  | 8      | 0.03   | Vue        | 组件处理逻辑（内聚度极低）                     |
| `src-monorepo`       | 7      | 0.21   | TypeScript | Monorepo 工具                                  |
| `embed-mount`        | 5      | 0.00   | TypeScript | Embed 挂载逻辑                                 |

**关键发现**：

- `api-handle` 社区规模最大（545 节点），表明 **integration 子应用承载了过多业务逻辑**
- `composables-toggle` 和 `components-handle` 内聚度极低（< 0.05），存在**职责混乱**
- `src-app` 内聚度为 0，说明**根组件缺乏统一架构约束**

### 2.2 Hub Nodes（架构热点）

Top 15 最高连接度节点（修改影响范围最大）：

| 节点                                   | 总度数 | 入度 | 出度 | 所属社区       | 风险等级 |
| -------------------------------------- | ------ | ---- | ---- | -------------- | -------- |
| `WindowManager.registerCoreIpc`        | 87     | 1    | 86   | modules-window | 🔴 极高  |
| `consoleRequest` (integration)         | 37     | 36   | 1    | api-handle     | 🟡 高    |
| `list` (consoleApi)                    | 37     | 6    | 31   | api-handle     | 🟡 高    |
| `setup` (NebulaDropdown)               | 37     | 3    | 34   | utils-setup    | 🟡 高    |
| `systemRequest` (settings)             | 35     | 34   | 1    | api-handle     | 🟡 高    |
| `setup` (NebulaAnchor)                 | 31     | 1    | 30   | utils-setup    | 🟡 高    |
| `IpcNotificationModule.setup`          | 30     | 1    | 29   | modules-window | 🟡 高    |
| `connect` (useSubscriptionEvents)      | 30     | 1    | 29   | api-handle     | 🟡 高    |
| `installWebPresentation`               | 27     | 1    | 26   | web-shell      | 🟢 中    |
| `createEditor` (use-diff-editor)       | 26     | 3    | 23   | api-handle     | 🟢 中    |
| `applyDefinitionFromProps` (DagEditor) | 26     | 2    | 24   | utils-node     | 🟢 中    |

**关键发现**：

- `WindowManager.registerCoreIpc` 是**最大架构热点**（87 度），任何 IPC 通道变更都会波及大量代码
- `api-handle` 社区占据 Top 15 中的 5 席，表明 **API 客户端层耦合严重**
- UI 组件（NebulaDropdown、NebulaAnchor）的 `setup` 函数出度过高，存在**组件初始化逻辑泄漏**

### 2.3 Bridge Nodes（架构瓶颈）

Betweenness Centrality 最高的节点（跨社区通信 chokepoints）：

| 节点                                  | Betweenness | 所属社区   | 说明                             |
| ------------------------------------- | ----------- | ---------- | -------------------------------- |
| `it:invokes onUnauthorized...` (test) | 0.0019      | src-api    | 认证失败测试用例成为桥梁（异常） |
| `beforeEach` (authGuard test)         | 0.0019      | api-handle | 路由守卫测试                     |
| `computeAutoLayout`                   | 0.0018      | utils-node | DAG 自动布局算法                 |
| `clearAuthSession`                    | 0.0013      | api-handle | 清除认证会话                     |

**关键发现**：

- **测试代码出现在 Bridge Nodes 中是不正常的**，说明生产代码与测试代码边界模糊
- `clearAuthSession` 作为桥梁节点，表明**认证状态管理分散**，多处直接操作 Session

### 2.4 跨社区耦合

当前图谱显示 **0 条跨社区边**，这可能是因为：

1. 图谱构建时未启用跨文件依赖追踪
2. 或项目确实存在严重的**模块隔离问题**（各子应用独立打包，缺少共享层）

结合代码审查，实际问题是：**子应用之间通过 `app-shell` 隐式耦合**，但 graph 未能捕捉这种运行时依赖。

---

## 3. 与后端规划的匹配度评估

### 3.1 后端规划回顾（来自 `docs/模块规划.md`）

后端 Nebula 平台的核心域包括：

| 后端模块            | 职责                             | 对应前端功能                   |
| ------------------- | -------------------------------- | ------------------------------ |
| `nebula-camel`      | 接口集成平台（Route、DAG、插件） | Integration 子应用             |
| `nebula-task`       | 任务调度                         | （缺失）                       |
| `nebula-plugin`     | 动态插件体系                     | （部分在 Integration 中）      |
| `nebula-config`     | 动态配置（CORS、CSP、策略）      | Settings 子应用                |
| `nebula-system`     | 系统域（用户、组织、配置项）     | Settings 子应用                |
| `nebula-governance` | 资源治理（审批、审计）           | （缺失）                       |
| `nebula-release`    | 发布管理                         | （缺失）                       |
| `nebula-subscribe`  | 事件订阅                         | Integration 中的 Subscriptions |
| `nebula-security`   | 安全认证                         | Login + app-shell 认证层       |

### 3.2 匹配度分析

#### ✅ 已匹配部分

1. **Integration 子应用 ↔ `nebula-camel`**

   - DAG 编辑器（`nebula-dag-editor`）对应 Camel DAG 编排
   - BPMN 编辑器（`nebula-flow-editor`）对应治理工作流
   - 订阅管理对应 `camel-subscribe`

2. **Settings 子应用 ↔ `nebula-system` + `nebula-config`**

   - 用户管理、组织管理
   - 配置项管理

3. **Login ↔ `nebula-security`**

   - JWT 认证、Session 管理

#### ❌ 缺失部分

| 后端模块                 | 前端缺失功能                     | 影响                                 |
| ------------------------ | -------------------------------- | ------------------------------------ |
| `nebula-task`            | 任务调度管理界面                 | 无法可视化配置 Cron 任务、依赖触发器 |
| `nebula-governance`      | 资源申请、审批流、审计日志       | 缺少治理闭环                         |
| `nebula-release`         | 发布管理、版本对比、回滚         | 缺少发布流水线可视化                 |
| `nebula-plugin`          | 插件市场、在线安装、生命周期管理 | 插件能力未暴露给管理员               |
| `nebula-cluster`         | 集群节点监控、分布式锁状态       | 运维能力缺失                         |
| `nebula-version-control` | 资源版本历史、差异对比           | 缺少版本管理能力                     |

#### ⚠️ 不合理部分

1. **子应用集成方式混乱**

   - 当前新增子应用需要同时修改：
     - `packages/app-shell/src/common/shellPresentationConfig.ts`（窗口声明）
     - `apps/sub-web/frontend/src/platform/integratedApps.ts`（集成元数据）
     - `apps/web/vite.config.ts`（Vite 别名映射）
     - `apps/electron/app.config.ts`（Electron 窗口配置）
   - **违反开闭原则**：每次新增子应用都要改动多个配置文件

2. **Packages 依赖关系不合理**

   - `nebula-integration-panel` 依赖 `nebula-flow-editor`，但后者又依赖 `nebula-ui`
   - 形成**深层嵌套依赖**，导致单个组件更新触发全量重建
   - `electron-shared` 和 `electron-shared-vue` 职责不清，前者纯 TS，后者引入 Vue

3. **Web 与 Electron 启动路径不一致**

   - Web 通过 `web-boot.ts` 的 `?embed` 参数动态挂载子应用
   - Electron 通过 `boot.ts` 的 `import.meta.glob` 动态加载
   - 两者逻辑重复，但实现细节不同，**维护成本高**

4. **认证状态管理分散**

   - `app-shell` 提供 `readWebAuthSession` / `writeWebAuthSession`
   - `integration` 子应用有自己的 `bootstrap-auth.ts`
   - `settings` 子应用没有独立的认证引导
   - **缺少统一的 Auth Provider**

---

## 4. 重构方案

### 4.1 目标架构

```
nebula-studio/
├── apps/
│   ├── electron/              # Electron 壳层（不变）
│   ├── electron-preload/      # 【重构】统一 Preload 生成器（见 4.3 节）
│   │   └── src/
│   │       ├── index.ts       # 统一入口（根据窗口配置动态生成 API）
│   │       ├── capabilities/  # 能力模块（auth、notify、settings 等）
│   │       └── types.ts       # 统一类型定义
│   ├── web/                   # Web 壳层（简化为纯路由分发器）
│   └── renderers/             # 【新增】统一子应用目录
│       ├── shell/             # 壳层主界面（原 sub-web/frontend）
│       ├── integration/       # 集成平台
│       ├── settings/          # 设置中心
│       ├── login/             # 登录页
│       ├── docs/              # 文档中心
│       ├── tasks/             # 【新增】任务调度管理
│       ├── governance/        # 【新增】资源治理
│       ├── release/           # 【新增】发布管理
│       └── plugins/           # 【新增】插件市场
├── packages/
│   ├── core/                  # 【重组】核心共享层
│   │   ├── app-shell/         # 壳层抽象（从原位置迁移）
│   │   ├── api-client/        # API 客户端
│   │   ├── auth-provider/     # 【新增】统一认证提供者
│   │   └── electron-bridge/   # 【合并】electron-shared + electron-shared-vue
│   ├── ui/                    # 【重组】UI 层
│   │   ├── nebula-ui/         # 基础组件库
│   │   ├── nebula-layout/     # 布局组件
│   │   └── icons/             # 【新增】图标库（从 integratedApps.ts 提取）
│   ├── editors/               # 【重组】编辑器集合
│   │   ├── dag-editor/        # DAG 编辑器
│   │   ├── flow-editor/       # BPMN 编辑器
│   │   ├── code-editor/       # 【重命名】原 nebula-editor → code-editor
│   │   └── low-code-form/     # 【重命名】原 nebula-low-render
│   ├── features/              # 【新增】业务特性包（可被多个子应用复用）
│   │   ├── subscription-manager/  # 订阅管理
│   │   ├── route-designer/    # Route 设计器
│   │   ├── plugin-installer/  # 插件安装器
│   │   └── version-diff/      # 版本对比器
│   └── shared-utils/          # 【新增】工具函数
│       ├── monorepo/          # 原 internal/node
│       └── vite-helpers/      # 原 internal/vite 中的通用插件
├── internal/                  # 【精简】仅保留构建工具
│   ├── vite/                  # Vite 配置封装
│   └── scripts/               # 构建脚本
└── configs/                   # 【新增】集中配置
    ├── windows.json           # 【关键】窗口声明集中管理
    ├── integrations.json      # 【关键】子应用集成元数据
    └── aliases.json           # 【关键】Vite 别名映射
```

### 4.2 关键改进点

#### 改进 1：子应用配置集中化

**问题**：当前新增子应用需要修改 4+ 个文件

**解决方案**：引入集中配置文件

**`configs/windows.json`**：

```json
{
  "windows": {
    "main": {
      "preload": "main",
      "renderer": "shell",
      "label": "工作台",
      "iconSvg": "<svg>...</svg>",
      "defaultEnabled": true,
      "integratable": true,
      "requiresAuth": true
    },
    "integration": {
      "preload": "main",
      "renderer": "integration",
      "label": "集成平台",
      "iconSvg": "<svg>...</svg>",
      "defaultEnabled": true,
      "integratable": true,
      "requiresAuth": true
    },
    "tasks": {
      "preload": "main",
      "renderer": "tasks",
      "label": "任务调度",
      "iconSvg": "<svg>...</svg>",
      "defaultEnabled": false,
      "integratable": true,
      "requiresAuth": true
    }
  },
  "displayOrder": ["main", "integration", "tasks", "settings", "docs"]
}
```

**自动生成机制**：

1. 构建时读取 `configs/windows.json`
2. 自动生成：
   - `packages/core/app-shell/src/common/shellPresentationConfig.ts`
   - `apps/renderers/shell/src/platform/integratedApps.ts`
   - `apps/web/vite.rendererAlias.ts` 的映射表
   - `apps/electron/app.config.ts` 的窗口声明

**新增子应用流程**（从 4 步缩减为 1 步）：

```bash
# 1. 在 configs/windows.json 中添加新窗口（含 preloadCapabilities 声明）
# 2. 创建 apps/renderers/tasks/ 目录并开发
# 3. 运行 pnpm run generate:config（自动生成所有配置，包括统一 Preload 的能力注入）
# 4. 完成！无需手动创建 Preload 包
```

#### 改进 2：统一认证提供者

**问题**：认证状态管理分散在 `app-shell`、`integration/bootstrap-auth`、各子应用

**解决方案**：新建 `packages/core/auth-provider`

**`packages/core/auth-provider/package.json`**：

```json
{
  "name": "@nebula-studio/auth-provider",
  "version": "0.0.0",
  "type": "module",
  "exports": {
    ".": "./src/index.ts",
    "./vue": "./src/vue/AuthProvider.vue"
  },
  "dependencies": {
    "@nebula-studio/api-client": "workspace:^",
    "vue": "catalog:vue"
  }
}
```

**`packages/core/auth-provider/src/index.ts`**：

```typescript
export interface AuthSession {
  accessToken: string;
  refreshToken?: string;
  userId: string;
  tenantId?: string;
  expiresAt: number;
}

export class AuthProvider {
  private session: AuthSession | null = null;
  private listeners: Array<(session: AuthSession | null) => void> = [];

  async login(username: string, password: string): Promise<void> {
    // 统一登录逻辑
  }

  async logout(): Promise<void> {
    this.session = null;
    this.notifyListeners();
  }

  getSession(): AuthSession | null {
    return this.session;
  }

  onSessionChange(callback: (session: AuthSession | null) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== callback);
    };
  }

  private notifyListeners(): void {
    for (const listener of this.listeners) {
      listener(this.session);
    }
  }
}

export const globalAuthProvider = new AuthProvider();
```

**`packages/core/auth-provider/src/vue/AuthProvider.vue`**：

```vue
<script setup lang="ts">
import { provide, ref } from "vue";
import { globalAuthProvider, type AuthSession } from "../index";

const session = ref<AuthSession | null>(globalAuthProvider.getSession());

globalAuthProvider.onSessionChange((newSession) => {
  session.value = newSession;
});

provide("auth", globalAuthProvider);
</script>

<template>
  <slot :session="session" :login="globalAuthProvider.login" :logout="globalAuthProvider.logout" />
</template>
```

**使用方式**（所有子应用统一）：

```vue
<!-- apps/renderers/integration/src/App.vue -->
<script setup lang="ts">
import AuthProvider from "@nebula-studio/auth-provider/vue";
</script>

<template>
  <AuthProvider v-slot="{ session, login, logout }">
    <RouterView v-if="session" />
    <LoginPage v-else @login="login" />
  </AuthProvider>
</template>
```

#### 改进 3：Packages 依赖优化

**当前问题**：

```
nebula-integration-panel
  └─ nebula-flow-editor
       └─ nebula-ui
            └─ codemirror, vxe-table, wangeditor...
```

**重构后**：

```
packages/editors/
├── dag-editor/          # 仅依赖 @vue-flow/* + nebula-ui（轻量）
├── flow-editor/         # 仅依赖 bpmn-js + nebula-ui
├── code-editor/         # 仅依赖 monaco-editor
└── low-code-form/       # 仅依赖 nebula-ui

packages/features/
├── subscription-manager/  # 依赖 api-client + dag-editor
├── route-designer/        # 依赖 api-client + code-editor + dag-editor
└── plugin-installer/      # 依赖 api-client + nebula-ui
```

**关键原则**：

- **编辑器包不互相依赖**，避免传递性依赖爆炸
- **业务特性包（features）** 组合多个编辑器，供子应用按需引入
- **nebula-ui** 拆分为更细粒度的组件包（可选）：
  ```
  packages/ui/nebula-ui-base/     # 按钮、输入框等基础组件
  packages/ui/nebula-ui-data/     # VxeTable、图表等数据组件
  packages/ui/nebula-ui-editor/   # CodeMirror、WangEditor 封装
  ```

#### 改进 4：Web 与 Electron 启动路径统一

**当前问题**：

- Web：`web-boot.ts` → `embed/*-entry.ts` → 手动 mount Vue App
- Electron：`boot.ts` → `import.meta.glob` → 动态 import `main.ts`

**统一方案**：

**`apps/renderers/*/src/boot.ts`**（所有子应用统一入口）：

```typescript
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { AuthProvider } from "@nebula-studio/auth-provider/vue";
import { installPresentation } from "@nebula-studio/app-shell";

// 1. 安装 Presentation 层（Web/Electron 通用）
installPresentation({
  scope: import.meta.env.VITE_RENDERER_SCOPE,
});

// 2. 创建 Vue App
const app = createApp(App).use(AuthProvider).use(router);

// 3. 路由守卫（统一认证检查）
router.beforeEach(async (to) => {
  if (to.meta.requiresAuth) {
    const session = globalAuthProvider.getSession();
    if (!session) {
      return "/login";
    }
  }
});

// 4. 挂载
app.mount("#app");
```

**Web 宿主简化**（`apps/web/src/web-boot.ts`）：

```typescript
const surface = new URLSearchParams(location.search).get("embed") || "shell";
await import(`../renderers/${surface}/src/boot.ts`);
```

**Electron 简化**（`apps/electron/src/renderer/boot.ts`）：

```typescript
const windowId = new URLSearchParams(window.location.search).get("renderer") || "main";
await import(`../../../renderers/${windowId}/src/boot.ts`);
```

**优势**：

- 子应用无需关心运行在 Web 还是 Electron
- 认证、路由、Presentation 层统一处理
- 新增子应用只需创建 `apps/renderers/<name>/src/boot.ts`

#### 改进 4.5：Electron Preload 层重构

**当前问题**：

1. 三个 Preload 脚本（`main`、`docs`、`settings`）中 `contextBridge.exposeInMainWorld` 逻辑完全重复
2. Notify Bridge 在 `main` 和 `docs` 中重复实现，仅 IPC 通道名不同
3. 类型定义分散，`settings` 缺少 `preload.d.ts`
4. 新增窗口需手动创建新的 Preload 包，违反开闭原则

**重构方案**：统一 Preload 生成器 + 能力模块化

**`apps/electron-preload/package.json`**：

```json
{
  "name": "@nebula-studio-preload/unified",
  "version": "0.0.0",
  "type": "module",
  "main": "./src/index.ts",
  "dependencies": {
    "@electron-toolkit/preload": "catalog:electron",
    "@nebula-studio-electron/electron-shared": "workspace:^"
  },
  "devDependencies": {
    "@types/node": "catalog:types",
    "electron": "catalog:electron"
  }
}
```

**`apps/electron-preload/src/index.ts`**（统一入口）：

```typescript
import { contextBridge } from "electron";
import { electronAPI } from "@electron-toolkit/preload";
import { createAuthCapability } from "./capabilities/auth";
import { createNotifyCapability } from "./capabilities/notify";
import { createSettingsCapability } from "./capabilities/settings";
import { getWindowConfig } from "./config";

const windowConfig = getWindowConfig();

const api = {
  electron: electronAPI,
  auth: windowConfig.capabilities.includes("auth") ? createAuthCapability() : undefined,
  notify: windowConfig.capabilities.includes("notify") ? createNotifyCapability() : undefined,
  settings: windowConfig.capabilities.includes("settings") ? createSettingsCapability() : undefined,
};

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld("electron", api.electron);
    contextBridge.exposeInMainWorld("api", api);
  } catch (error) {
    console.error("[preload] Failed to expose APIs:", error);
  }
} else {
  // @ts-expect-error — non-isolated fallback
  window.electron = api.electron;
  // @ts-expect-error — non-isolated fallback
  window.api = api;
}
```

**`apps/electron-preload/src/capabilities/auth.ts`**：

```typescript
import { ipcRenderer } from "electron";
import { electronAPI } from "@electron-toolkit/preload";

export function createAuthCapability() {
  return {
    async login(payload: { user: string; password: string }) {
      const r = await electronAPI.ipcRenderer.invoke("auth:login", payload);
      if (!r.ok) throw new Error(r.error);
      return r;
    },
    getSession(): Promise<{ user: string; token?: string } | null> {
      return electronAPI.ipcRenderer.invoke("auth:get-session");
    },
    establishSession(payload: { user: string; token: string }): Promise<boolean> {
      return electronAPI.ipcRenderer.invoke("auth:establish-session", payload);
    },
    logout(): Promise<boolean> {
      return electronAPI.ipcRenderer.invoke("auth:logout");
    },
  };
}
```

**`apps/electron-preload/src/capabilities/notify.ts`**：

```typescript
import { ipcRenderer } from "electron";
import type { IpcRendererEvent } from "electron";
import { electronAPI } from "@electron-toolkit/preload";
import type {
  AppNotifyPayload,
  AppNotifyResponsePayload,
  NotifyBridgePayload,
} from "@nebula-studio-electron/electron-shared";
import { getWindowConfig } from "../config";

export function createNotifyCapability() {
  const SOURCE = getWindowConfig().id;
  const useBridge = SOURCE !== "main"; // main 窗口直接使用 IPC，其他窗口走 bridge

  return {
    app(payload: AppNotifyPayload) {
      const req: NotifyBridgePayload<AppNotifyPayload> = { source: SOURCE, payload };
      const channel = useBridge ? "notify:bridge:app" : "notify:app";
      return electronAPI.ipcRenderer.invoke(channel, req);
    },
    system(payload: { title: string; body: string }) {
      const req: NotifyBridgePayload<{ title: string; body: string }> = { source: SOURCE, payload };
      const channel = useBridge ? "notify:bridge:system" : "notify:system";
      return electronAPI.ipcRenderer.invoke(channel, req);
    },
    onApp(listener: (payload: AppNotifyPayload) => void) {
      const handler = (_event: IpcRendererEvent, payload: AppNotifyPayload) => listener(payload);
      ipcRenderer.on("notify:app", handler);
      return () => ipcRenderer.removeListener("notify:app", handler);
    },
    respond(payload: AppNotifyResponsePayload) {
      const req: NotifyBridgePayload<AppNotifyResponsePayload> = { source: SOURCE, payload };
      const channel = useBridge ? "notify:bridge:app:response" : "notify:app:response";
      return electronAPI.ipcRenderer.invoke(channel, req);
    },
    onAppResponse(listener: (payload: AppNotifyResponsePayload) => void) {
      const handler = (_event: IpcRendererEvent, payload: AppNotifyResponsePayload) =>
        listener(payload);
      ipcRenderer.on("notify:app:response", handler);
      return () => ipcRenderer.removeListener("notify:app:response", handler);
    },
  };
}
```

**`apps/electron-preload/src/capabilities/settings.ts`**：

```typescript
import { ipcRenderer } from "electron";
import type { IpcRendererEvent } from "electron";
import { electronAPI } from "@electron-toolkit/preload";

type ThemeMode = "light" | "dark";

export function createSettingsCapability() {
  return {
    getTheme(): Promise<ThemeMode> {
      return electronAPI.ipcRenderer.invoke("settings:theme:get");
    },
    setTheme(theme: ThemeMode): Promise<ThemeMode> {
      return electronAPI.ipcRenderer.invoke("settings:theme:set", { theme });
    },
    onThemeChanged(listener: (payload: { theme: ThemeMode }) => void) {
      const handler = (_event: IpcRendererEvent, payload: { theme: ThemeMode }) =>
        listener(payload);
      ipcRenderer.on("settings:theme:changed", handler);
      return () => ipcRenderer.removeListener("settings:theme:changed", handler);
    },
  };
}
```

**`apps/electron-preload/src/config.ts`**：

```typescript
export interface WindowPreloadConfig {
  id: string;
  capabilities: Array<"auth" | "notify" | "settings" | "shell">;
}

// 从环境变量或构建时注入
const PRELOAD_CONFIG: Record<string, WindowPreloadConfig> = {
  main: { id: "main", capabilities: ["auth", "notify", "shell"] },
  docs: { id: "docs", capabilities: ["notify"] },
  settings: { id: "settings", capabilities: ["settings"] },
  integration: { id: "integration", capabilities: ["auth", "notify"] },
  tasks: { id: "tasks", capabilities: ["auth", "notify"] },
  governance: { id: "governance", capabilities: ["auth", "notify"] },
  release: { id: "release", capabilities: ["auth", "notify"] },
  plugins: { id: "plugins", capabilities: ["auth", "notify"] },
};

export function getWindowConfig(): WindowPreloadConfig {
  const windowId = new URLSearchParams(window.location.search).get("renderer") || "main";
  return PRELOAD_CONFIG[windowId] || PRELOAD_CONFIG.main;
}
```

**Electron 主进程侧配置更新**（`apps/electron/app.config.ts`）：

```typescript
export default {
  electron: import.meta.dirname,
  renderers: "renderers",
  ...shellPresentationConfig,
  modalRenderers,
  // 新增：Preload 能力映射
  preloadCapabilities: {
    main: ["auth", "notify", "shell"],
    docs: ["notify"],
    settings: ["settings"],
    integration: ["auth", "notify"],
    tasks: ["auth", "notify"],
    governance: ["auth", "notify"],
    release: ["auth", "notify"],
    plugins: ["auth", "notify"],
  },
} as const;
```

**优势**：

1. **单一 Preload 包**：从 3 个独立包合并为 1 个，减少维护成本
2. **能力模块化**：auth、notify、settings 等能力按需组合，新增窗口无需创建新包
3. **类型统一**：所有窗口共享同一套类型定义
4. **开闭原则**：新增子应用只需在 `preloadCapabilities` 中声明所需能力

---

#### 改进 5：新增缺失的后端域对应前端模块

根据后端规划，补充以下子应用：

##### 5.1 Tasks 子应用（对应 `nebula-task`）

**`apps/renderers/tasks/package.json`**：

```json
{
  "name": "@nebula-studio-renderer/tasks",
  "version": "0.0.0",
  "dependencies": {
    "@nebula-studio/api-client": "workspace:^",
    "@nebula-studio/auth-provider": "workspace:^",
    "@nebula-studio/nebula-ui": "workspace:^",
    "@nebula-studio/nebula-layout": "workspace:^",
    "vue": "catalog:vue",
    "vue-router": "catalog:vue"
  }
}
```

**功能模块**：

- 任务列表（分页、过滤、状态管理）
- 任务编辑器（Cron 表达式生成器、依赖图可视化）
- 执行日志（实时日志流、错误堆栈展示）
- 集群节点分配（依赖 `nebula-cluster`）

##### 5.2 Governance 子应用（对应 `nebula-governance`）

**`apps/renderers/governance/package.json`**：

```json
{
  "name": "@nebula-studio-renderer/governance",
  "version": "0.0.0",
  "dependencies": {
    "@nebula-studio/api-client": "workspace:^",
    "@nebula-studio/auth-provider": "workspace:^",
    "@nebula-studio/nebula-ui": "workspace:^",
    "@nebula-studio/nebula-flow-editor": "workspace:^",
    "vue": "catalog:vue",
    "vue-router": "catalog:vue"
  }
}
```

**功能模块**：

- 资源申请列表（创建、修改、删除、发布申请）
- 审批工作台（待审批、已审批、审批历史）
- BPMN 流程设计器（复用 `nebula-flow-editor`）
- 审计日志查询（操作者、时间、内容、结果）

##### 5.3 Release 子应用（对应 `nebula-release`）

**`apps/renderers/release/package.json`**：

```json
{
  "name": "@nebula-studio-renderer/release",
  "version": "0.0.0",
  "dependencies": {
    "@nebula-studio/api-client": "workspace:^",
    "@nebula-studio/auth-provider": "workspace:^",
    "@nebula-studio/nebula-ui": "workspace:^",
    "@nebula-studio/features/version-diff": "workspace:^",
    "vue": "catalog:vue",
    "vue-router": "catalog:vue"
  }
}
```

**功能模块**：

- 发布流水线可视化（Draft → Version → Approval → Deploy）
- 版本对比器（JSON Diff、Camel Route XML Diff）
- 回滚管理（选择历史版本、一键回滚）
- 部署目标管理（本地、K8s、远程集群）

##### 5.4 Plugins 子应用（对应 `nebula-plugin`）

**`apps/renderers/plugins/package.json`**：

```json
{
  "name": "@nebula-studio-renderer/plugins",
  "version": "0.0.0",
  "dependencies": {
    "@nebula-studio/api-client": "workspace:^",
    "@nebula-studio/auth-provider": "workspace:^",
    "@nebula-studio/nebula-ui": "workspace:^",
    "@nebula-studio/features/plugin-installer": "workspace:^",
    "vue": "catalog:vue",
    "vue-router": "catalog:vue"
  }
}
```

**功能模块**：

- 插件市场（本地仓库、远程 Maven 仓库搜索）
- 插件详情（描述、版本、依赖、扩展点）
- 在线安装/卸载/更新
- 插件生命周期管理（启用、禁用、热加载）

---

## 5. 实施步骤

### 阶段一：基础设施重构（2 周）

**Week 1**：

1. 创建 `configs/` 目录，定义 `windows.json` schema（含 `preloadCapabilities` 声明）
2. 实现配置生成脚本（TypeScript + JSON Schema 验证）
3. 迁移 `packages/app-shell` → `packages/core/app-shell`
4. 合并 `packages/electron-shared` + `packages/electron-shared-vue` → `packages/core/electron-bridge`

**Week 2**：

1. 创建 `packages/core/auth-provider`
2. **重构 `apps/electron-preload` 为统一 Preload 生成器**：
   - 创建 `capabilities/` 目录，拆分 auth、notify、settings 能力模块
   - 实现 `config.ts` 根据窗口配置动态生成 API
   - 删除旧的 `main/`、`docs/`、`settings/` 三个独立包
   - 更新 `apps/electron/electron.vite.config.ts` 的 Preload 构建配置
3. 重构 `apps/renderers/shell`（原 `sub-web/frontend`）使用新 AuthProvider
4. 统一所有子应用的 `boot.ts` 入口
5. 更新 `apps/web` 和 `apps/electron` 的启动逻辑

### 阶段二：Packages 重组（2 周）

**Week 3**：

1. 创建 `packages/ui/`、`packages/editors/`、`packages/features/` 目录
2. 迁移现有 packages 到新结构
3. 拆分 `nebula-ui` 为细粒度组件包（可选，视复杂度决定）
4. 更新所有子应用的依赖引用

**Week 4**：

1. 创建 `packages/features/subscription-manager`
2. 创建 `packages/features/route-designer`
3. 创建 `packages/features/plugin-installer`
4. 创建 `packages/features/version-diff`
5. 更新 `integration` 子应用使用新的 features 包

### 阶段三：新增子应用开发（4 周）

**Week 5-6**：Tasks 子应用

- 任务列表、编辑器、执行日志
- 对接后端 `nebula-task` API

**Week 7-8**：Governance 子应用

- 资源申请、审批工作台、BPMN 设计器
- 对接后端 `nebula-governance` API

**Week 9-10**：Release 子应用

- 发布流水线、版本对比、回滚管理
- 对接后端 `nebula-release` API

**Week 11-12**：Plugins 子应用

- 插件市场、在线安装、生命周期管理
- 对接后端 `nebula-plugin` API

### 阶段四：测试与优化（2 周）

**Week 13**：

1. 端到端测试（Web + Electron 双模式）
2. 性能优化（代码分割、懒加载、Tree Shaking）
3. 修复 code-review-graph 检测到的 Hub Nodes 和 Bridge Nodes 问题

**Week 14**：

1. 文档更新（README、架构说明、子应用开发指南）
2. CI/CD 流程调整（适配新目录结构）
3. 灰度发布与监控

---

## 6. 风险评估与缓解

### 6.1 高风险项

| 风险                              | 影响                      | 缓解措施                                                                |
| --------------------------------- | ------------------------- | ----------------------------------------------------------------------- |
| 配置生成脚本 bug 导致构建失败     | 阻塞所有子应用开发        | 编写单元测试覆盖 JSON Schema 验证；提供手动回退机制                     |
| AuthProvider 迁移导致认证中断     | 用户无法登录              | 并行运行旧认证逻辑与新 AuthProvider，逐步切换                           |
| **Preload 统一后 IPC 通道不匹配** | **Electron 窗口通信失败** | **保留旧 Preload 包作为 fallback；编写集成测试覆盖所有窗口的 IPC 调用** |
| Packages 依赖调整引发循环依赖     | 构建失败或运行时错误      | 使用`madge` 工具检测循环依赖；分批次迁移                                |
| 新增子应用与后端 API 不匹配       | 功能不可用                | 前后端同步开发，每周对齐 API 契约                                       |

### 6.2 中风险项

| 风险                            | 影响             | 缓解措施                                        |
| ------------------------------- | ---------------- | ----------------------------------------------- |
| Electron 窗口管理与新配置不兼容 | 桌面端崩溃       | 保留旧`app.config.ts` 作为 fallback，逐步迁移   |
| Vite 别名映射错误导致模块找不到 | 开发环境无法启动 | 提供`pnpm run check:aliases` 脚本验证别名有效性 |
| 子应用间共享状态冲突            | 数据不一致       | 严格遵循 AuthProvider 单一事实来源原则          |

---

## 7. 成功指标

### 7.1 技术指标

- **新增子应用时间**：从 4 小时缩减至 30 分钟（仅需编辑 `windows.json` + 创建目录，**无需创建 Preload 包**）
- **构建速度**：全量构建时间减少 30%（通过依赖优化和代码分割）
- **Preload 包数量**：从 3 个独立包合并为 1 个统一 Preload，**代码重复率降低 70%**
- **Hub Nodes 数量**：Top 10 Hub Nodes 的平均度数降低 50%
- **Bridge Nodes 中的测试代码**：降至 0（生产代码与测试代码分离）

### 7.2 业务指标

- **后端模块覆盖率**：从 40% 提升至 90%（新增 Tasks、Governance、Release、Plugins）
- **用户任务完成时间**：资源发布流程从 5 步缩减至 3 步（可视化流水线）
- **插件安装成功率**：从手动上传 JAR 提升至在线一键安装（成功率 > 95%）

---

## 8. 附录

### 8.1 关键依赖清单

| 包名            | 版本   | 用途            |
| --------------- | ------ | --------------- |
| Vue             | 3.5.35 | 前端框架        |
| Vue Router      | 4.6.4  | 路由管理        |
| Vite            | 8.0.10 | 构建工具        |
| Electron        | 42.3.1 | 桌面容器        |
| @vue-flow/core  | 1.41.2 | DAG 流程图      |
| bpmn-js         | 18.0.0 | BPMN 流程编辑器 |
| Monaco Editor   | 0.55.1 | 代码编辑器      |
| VxeTable        | 4.19.6 | 数据表格        |
| CodeMirror 6    | 6.x    | 富文本编辑器    |
| WangEditor Next | 5.7.7  | Markdown 编辑器 |

### 8.2 参考资源

- [Nebula 后端模块规划](./模块规划.md)
- [Code Review Graph 工具文档](https://github.com/code-review-graph/docs)
- [Electron + Vite 最佳实践](https://electron-vite.org/)
- [Monorepo 管理指南](https://pnpm.io/workspaces)

---

**文档版本**：v1.0
**最后更新**：2026-06-25
**作者**：AI Assistant（基于 code-review-graph 分析与人工审查）
