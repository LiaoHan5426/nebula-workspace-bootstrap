# ADR: 状态所有权

- 状态：已接受
- 日期：2026-08-23
- 轨道：B（前端体验底座）

## 决策

Pinia 是 **客户端领域状态** 的默认方案，不替代：

- URL / Vue Router
- 服务端缓存（Vue Query）
- 表单与校验草稿
- 组件局部 `ref` / `reactive`

Settings 外观偏好属于客户端领域状态：经 `@nebula-studio/state` + `@nebula-studio/storage` 持久化。禁止把 access token、权限结果或服务端实体写入 persist。

Host 通过 `HostThemeCapability` 发布 `ResolvedTheme`；Remote 只消费 capability 与 CSS 变量，不另存一份主题真相。

登出与切租户必须调用 storage `clear`（privacy 允许的键），不得留下跨用户偏好以外的会话缓存。
