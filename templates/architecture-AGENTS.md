# 工作空间级 Agent 规则

> 由 `workspace-bootstrap` 生成，路径：`{{WORKSPACE_ROOT}}/architecture/AGENTS.md`

本工作空间描述多仓工作空间的跨仓约定。各仓专属规范见各自 `AGENTS.md`。

## 仓库与目录

| Alias | 路径 |
| --- | --- |
{{REPO_TABLE_ROWS}}

- 工作空间根：`{{WORKSPACE_ROOT}}`
- 编辑器配置：`{{WORKSPACE_ROOT}}/{{EDITOR_DIR}}/`
- Python venv：`{{WORKSPACE_ROOT}}/.venv/`

## code-review-graph (CRG)

本工作空间优先用 CRG 做影响面分析、变更评审与跨仓调用路径查询。

### 何时必须用 CRG

- 改动影响面（「改 X 会影响哪些调用路径？」）
- 未提交改动的风险评审
- 跨仓耦合（分别查各仓再综合）

### MCP（编辑器配置）

Server：`code-review-graph`（工作空间 `{{EDITOR_DIR}}/mcp.json` 已配置）

| 工具 | 用途 |
| --- | --- |
| `get_impact_radius_tool` | 影响半径 |
| `detect_changes_tool` | 变更风险评分 |
| `traverse_graph_tool` / `query_graph_tool` | 调用链追踪 |
| `get_affected_flows_tool` | 端到端 flow |
| `cross_repo_search_tool` | 跨仓搜索 |

### CLI（工作空间 venv）

```text
{{CRG_EXE}} status
{{CRG_EXE}} update --skip-flows
{{CRG_EXE}} detect-changes --brief
```

### Hooks

- CRG hooks 使用 **{{SHELL_TYPE}}**（`.hooks/crg-*.{{SHELL_EXT}}`）
- 合并示例见 `{{EDITOR_DIR}}/hooks.merge-user.md`

### Editor Rules（各仓）

bootstrap 会将 `{{SKILLS_DIR}}/rules/*.{{SOURCE_RULE_EXT}}` 同步到各仓 `{{EDITOR_DIR}}/rules/`，自动转换为 `*.{{EDITOR_RULE_EXT}}`。这些规则为**指针规则**（`alwaysApply: true`），正文指向同仓 `{{SKILLS_DIR}}/skills/.../SKILL.md`，不复制 SKILL 全文。在对应 folder 下编辑时由编辑器自动注入。{{SKILLS_PATH_NOTE}}

## RTK (Rust Token Killer)

工作空间内 RTK 安装在：

- 目录：`{{RTK_DIR}}`
- 二进制：`{{RTK_EXE}}`
- Hook 脚本：`{{RTK_DIR}}/{{RTK_HOOK_SCRIPT}}`

来源：[rtk-ai/rtk Releases](https://github.com/rtk-ai/rtk/releases)（bootstrap 自动下载最新稳定版）

### 使用约定

- 冗长输出命令优先加 `rtk` 前缀：
  - `rtk vp run dev:web`
  - `rtk mvn test`
  - `rtk git status`
- {{SHELL_CHAIN_TIP}}

### 用户级 hooks 合并

编辑器主要读取用户级 hooks 配置。将工作空间 `{{EDITOR_DIR}}/hooks.json` 中的 `preToolUse`（RTK）与 CRG 条目合并进去，**全部使用 {{SHELL_TYPE}} 绝对路径**。详见 `{{EDITOR_DIR}}/hooks.merge-user.md`。

## Shell 配置

- 默认 shell：**{{SHELL_TYPE}}**
- 长驻进程（dev server、Spring Boot）由 Agent 后台启动，勿在同一条 Shell 链里阻塞
{{SHELL_FALLBACK_NOTE}}