# Nebula Module Federation B 轨执行计划

> 依据：`nebula-module-federation-frontend-refactoring-plan.md` v1.1  
> 范围：B 轨（§17 第 17–24 条；Phase 1–6 中 `[B]`）。不等待 C。  
> 仓库：`nebula-studio`（前端）；组织主题后端 API 本批不做。  
> 开工日：2026-08-23

## 当前进度（2026-08-23）

A 轨 1–16 已关门。B 轨执行切片已完成：第一至四批门户 Query/i18n、Query/Pinia 共享层、管理列表与服务治理/统计 Query（B5-1…B5-16）、AccessRequest Form pattern、Phase 6 样式收口与遗留 storage/locale adapter。C 轨见 `docs/nebula-mf-track-c-execution-plan.md`。

**历史保留项复评：** Playwright 全页视觉矩阵已经补齐。B-R1 已完成组织主题 JSONB、带 `sys:org:theme:manage` 的读写 REST、操作审计，以及 Host 的 user > organization > product 合并和切组织刷新。Vue Query persister 因完整响应持久化的隐私、租户隔离和 experimental API 风险继续不默认启用；产品帮助 Markdown 全量英译属于内容产品范围，而非架构阻塞。

## 复评实施结果

| ID   | 工作项 | 验收 |
| ---- | ------ | ---- |
| B-R1 | 组织主题 REST（已完成） | `GET/PUT /api/system/organizations/{id}/theme`；JSONB、权限与操作审计；Host capability 统一加载/合并并在切组织时刷新，Remote 不增加直连分支 |
| B-R2 | 遗留 UI 库存 | **已实现**：`check:b-inventory` 生成 `featureI18nCandidates` / `lowTrafficFormCandidates`；新建/修改页面强制迁移，未触达页面按 owner/批次追踪，不再笼统称“可选打磨” |

B-R1/B-R2 均已完成，B-R2 候选页面继续按触达范围迁移。

## 第一批（已完成）

Phase 1 tokens / inventory / factory + Phase 4 Settings 主题 UI。验收命令见历史切片 B1-1 … B1-17。

## Phase 2 B：Host locale + i18n factory

| ID   | 工作项                 | 验收                                                                                               |
| ---- | ---------------------- | -------------------------------------------------------------------------------------------------- |
| B2-1 | `HostLocaleCapability` | `locale` / `setLocale` / `subscribe`；Web storage `nebula.locale.v1`；Electron `settings:locale:*` |
| B2-2 | Remote mount           | Docs/Settings `createNebulaI18n` + subscribe 改 locale，不 remount                                 |
| B2-3 | i18n factory           | 懒加载 locale chunk、`fallbackLocale: zh-CN`、缺 key 收集与 zh/en 叶子 key 对比                    |

## Phase 2 B：Docs design catalog + 视觉基线

| ID   | 工作项             | 验收                                                                                |
| ---- | ------------------ | ----------------------------------------------------------------------------------- |
| B2-4 | Design 侧栏        | Tokens（status vs accent）、Theme matrix、Primitives 入口、Patterns 短名单          |
| B2-5 | Docs i18n 壳       | catalog/壳走 zh-CN/en-US chunk；产品帮助正文仍以中文为主                            |
| B2-6 | Host vs standalone | 同一套 `resolveTheme` token JSON；全页 PNG 矩阵已由 experience Playwright 项目覆盖 |

## Phase 4 B：Settings 界面 i18n

| ID   | 工作项           | 验收                                                                              |
| ---- | ---------------- | --------------------------------------------------------------------------------- |
| B4-1 | feature catalogs | appearance / personal / users / roles / permissions / orgs / apps / config / logs |
| B4-2 | Language 页      | 启用 en-US；调用 `capabilities.locale.setLocale`；去掉 `nebula.settings.language` |
| B4-3 | mount            | Settings federation/boot 切语言不 remount                                         |

## Phase 5 B 切片：catalog / detail / subscription

| ID   | 工作项       | 验收                                                                                                           |
| ---- | ------------ | -------------------------------------------------------------------------------------------------------------- |
| B5-1 | Query 底座   | Integration `createNebulaQueryClient` + `VueQueryPlugin`；`createTestQueryClient` retry 0                      |
| B5-2 | queryOptions | catalog / detail 共用 `resourceCatalogQueryOptions`；subscriptions + datasources；mutation invalidate          |
| B5-3 | Pinia portal | favorites/recents/drafts；迁移 `nebula.portal.*`；tenant/logout 清 drafts 与 Query cache，不 `location.reload` |
| B5-4 | i18n         | `bootNebulaI18n` + catalog/subscription catalogs；error code 映射；切语言不 remount                            |

```text
vp run --filter @nebula-studio/query test
vp run --filter @nebula-studio/state test
vp run --filter @nebula-studio-renderer/integration typecheck
vp run --filter @nebula-studio-renderer/integration test
vp run check:b-inventory
vp run check:boundaries
```

手工：Host 打开资源目录 → 详情命中同一 catalog query；创建订阅后列表刷新；Settings 切 English 后 catalog/subscription 壳切换且 iframe 不重载；切租户后 catalog 换数据且无整页 reload。

## Phase 5 B 切片：门户余页 + 数据源 + 插件目录

| ID   | 工作项                | 验收                                                                |
| ---- | --------------------- | ------------------------------------------------------------------- |
| B5-5 | My resources/requests | 共用 `access-requests` / `subscriptions` query；取消申请 invalidate |
| B5-6 | Data sources          | 复用 `dataSourcesQueryOptions` + connectors query；CRUD invalidate  |
| B5-7 | Plugin catalog        | `pluginCatalogQueryOptions`；客户端筛选保留                         |
| B5-8 | i18n                  | portal / datasources / plugins catalogs；zh/en 叶子 key 对比        |

```text
vp run --filter @nebula-studio-renderer/integration typecheck
vp run --filter @nebula-studio-renderer/integration test
vp run check:b-inventory
vp run check:boundaries
```

## Phase 6 B：styles 收口

| ID   | 工作项   | 验收                                                                                                           |
| ---- | -------- | -------------------------------------------------------------------------------------------------------------- |
| B6-1 | 生产入口 | 删除 `tools/tailwindcss` 的 `index.ts` / `electron.ts`；Host/Remote 只 import styles/document 或 styles/remote |
| B6-2 | 重复 CSS | 删除无引用的 `*-entry.css`；overlay portal 只留 assembly.css                                                   |
| B6-3 | 构建边界 | `theme.css` 仍给 Vite/Oxlint；apps 不得依赖 `@nebula-studio-internal/tailwind`                                 |

```text
vp run check:css-sources
vp run check:boundaries
vp run --filter @nebula-studio-internal/vite test
vp run check:b-inventory
```

## Phase 6 B：遗留 storage / locale adapter

| ID   | 工作项       | 验收                                                                                    |
| ---- | ------------ | --------------------------------------------------------------------------------------- |
| B6-4 | locale       | 只读写 `nebula.locale.v1`；删除 `LEGACY_LOCALE_KEYS` 与 `nebula-studio-web-locale` 双写 |
| B6-5 | theme        | 只读写 `nebula.theme.v1`；删除 `nebula-studio-web-theme` 双写与 storage 监听            |
| B6-6 | portal/shell | 删除 `nebula.portal.*` hydrate 与 shell 旧 integration localStorage 清理                |

```text
vp run --filter @nebula-studio/i18n test
vp run --filter @nebula-studio/host-capabilities test
vp run --filter @nebula-studio-renderer/integration test
vp run check:b-inventory
```

## Phase 5 B 余量：Query/Pinia 共享层

| ID    | 工作项        | 验收                                                                                                                        |
| ----- | ------------- | --------------------------------------------------------------------------------------------------------------------------- |
| B5-9  | Query 共享层  | `createQueryKey` / `query.install`；Integration keys 集中在 `shared/query/keys`；datasources options 不再挂在 subscriptions |
| B5-10 | Pinia persist | `createNebulaPersistPlugin`：pick / privacy / schemaVersion；门户 favorites 走 device、drafts 走 session；插件筛选持久化    |

```text
vp run --filter @nebula-studio/query test
vp run --filter @nebula-studio/state test
vp run --filter @nebula-studio-renderer/integration test
```

## Phase 5 B 余量：管理列表 Query + Detail/Editor 语义

| ID    | 工作项 | 验收                                                                                                                            |
| ----- | ------ | ------------------------------------------------------------------------------------------------------------------------------- |
| B5-11 | Query  | cluster / executor / plugins / tenant / interfaces / tasks / flows / management home 走 queryOptions；删除未使用 `useResources` |
| B5-12 | Detail | ResourceDetail 使用 `NebulaDetailSection`                                                                                       |
| B5-13 | Editor | `resolveEditorSyntaxTheme` → vs/vs-dark；BPMN/DAG 选区用 `--editor-select` 而非 `--primary`                                     |

```text
vp run --filter @nebula-studio-renderer/integration typecheck
vp run --filter @nebula-studio-renderer/integration test
vp run --filter @nebula-studio/nebula-assembly test
```

## Phase 5 B 余量：服务治理 / 统计 / 申请 Form / 插件 list 合一

| ID    | 工作项 | 验收 |
| ----- | ------ | ---- |
| B5-14 | Query  | 服务治理/授权/发布、审批/发布/版本、订阅申请、日志/统计/拓扑、任务实例、DAG、连接器走 queryOptions；网关 demo 用 `useMutation` |
| B5-15 | Plugins | `PluginsPage` 只通过 `usePluginsPage` + `pluginListQueryOptions` 拉列表 |
| B5-16 | Form | AccessRequest 使用 `NebulaForm` / `NebulaFormItem` / `NebulaStepFlow`，draft 仍走 Pinia |

```text
vp run --filter @nebula-studio-renderer/integration typecheck
vp run --filter @nebula-studio-renderer/integration test
```

## 复评后的边界

- 已补齐：Playwright 全页视觉矩阵。
- 已补齐：B-R1 组织主题 REST/Host 合并；B-R2 遗留 UI 库存并进入持续迁移。
- 条件性实验：Vue Query persister 仅允许对明确白名单、非敏感 query 做独立 PoC，必须带 cache buster、tenant/user scope 和登出清理；不作为默认平台能力。
- 内容范围：产品帮助 Markdown 全量英译需产品内容 owner，不计作架构代码项，但新增/修改内容必须同步 `zh-CN/en-US`。
