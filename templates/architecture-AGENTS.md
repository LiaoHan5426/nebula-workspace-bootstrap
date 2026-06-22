# 工作空间级 Agent 规则

> 由 `workspace-bootstrap` 生成，路径：`{{WORKSPACE_ROOT}}/architecture/AGENTS.md`

本文件描述 **Nebula 多仓工作空间**（`nebula` 后端 + `nebula-studio` 前端）的跨仓约定。各仓专属规范见各自 `AGENTS.md`。

## 仓库与目录

| Alias | 路径 |
| --- | --- |
{{REPO_TABLE_ROWS}}

- 工作空间根：`{{WORKSPACE_ROOT}}`
- Cursor 配置：`{{WORKSPACE_ROOT}}/.cursor/`
- Python venv：`{{WORKSPACE_ROOT}}/.venv/`

## code-review-graph (CRG)

本工作空间前后端配对开发，优先用 CRG 做影响面分析、变更评审与跨仓调用路径查询。

### 已注册仓库

见上表。注册表：`~/.code-review-graph/registry.json`。

### 何时必须用 CRG

- 改动影响面（「改 X 会影响哪些调用路径？」）
- 未提交改动的风险评审
- 前后端耦合（分别查两边再综合）

### MCP（Cursor 优先）

Server：`code-review-graph`（工作空间 `.cursor/mcp.json` 已配置）

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

### Hooks（Windows）

- CRG hooks 使用 **PowerShell**（`.cursor/hooks/crg-*.ps1`）
- **禁止**在用户级 `~/.cursor/hooks.json` 中直接指向 `.sh`（会弹出 Git Bash 窗口）
- 合并示例见 `.cursor/hooks.merge-user.md`

### Cursor Rules（各仓）

bootstrap 会将 `agent-skills/rules/*.mdc` 同步到各仓 `.cursor/rules/`。这些 `.mdc` 为**指针规则**（`alwaysApply: true`），正文指向同仓 `agent-skills/skills/.../SKILL.md`，不复制 SKILL 全文。在对应 folder（`backend` / `frontend`）下编辑时由 Cursor 自动注入。

## RTK (Rust Token Killer)

工作空间内 RTK 安装在：

- 目录：`{{RTK_DIR}}`
- 二进制：`{{RTK_EXE}}`
- Cursor hook：`{{RTK_DIR}}/{{RTK_HOOK_SCRIPT}}`

来源：[rtk-ai/rtk Releases](https://github.com/rtk-ai/rtk/releases)（bootstrap 自动下载最新稳定版）

### 使用约定

- 冗长输出命令优先加 `rtk` 前缀：
  - `rtk vp run dev:web`
  - `rtk mvn test`
  - `rtk git status`
- PowerShell 链式命令用 `;`，不用 `&&`：
  - `rtk git add . ; rtk git commit -m "msg" ; rtk git push`

### 用户级 hooks 合并

Cursor 主要读取 `~/.cursor/hooks.json`。将工作空间 `.cursor/hooks.json` 中的 `preToolUse`（RTK）与 CRG 条目合并进去，**全部使用 PowerShell 绝对路径**。详见 `.cursor/hooks.merge-user.md`。

## Windows Shell

- 默认 shell：**PowerShell**
- 长驻进程（dev server、Spring Boot）由 Agent 后台启动，勿在同一条 Shell 链里阻塞
- Git for Windows Bash 仅作 CRG 备用（`.cursor/hooks/bash-fallback/`），默认不启用

## 双仓联动

- 前端 API 调用 ↔ 后端接口：两边分别跑 CRG，再人工核对契约（`/api/*` 路径）
- 后端改动：关注 gateway、console、executor demo 模块
- 前端改动：关注 integration 包与 `vp` 脚本
