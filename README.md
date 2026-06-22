# Nebula 工作空间自动构建脚本

本目录包含一套用于从**空目录**自动搭建 Nebula 工作空间的脚本，目标是一次性完成：

- 克隆 / 更新后端 `nebula` 与前端 `nebula-studio` 仓库
- 在工作空间根目录生成多根 `*.code-workspace` 文件
- 创建 Python 虚拟环境并安装 `code-review-graph`
- 为各仓构建 / 更新 CRG 图并完成注册
- 为 Windows 提供兼容 PowerShell 的 CRG hooks（可选 Git for Windows Bash 回退）
- **从 [RTK Releases](https://github.com/rtk-ai/rtk/releases) 下载 RTK 到 `.cursor/rtk/` 并完成 `rtk init`**
- 配置工作空间级 `.cursor` 目录与 hooks 资产（含 RTK `preToolUse` hook）
- **将各仓 `agent-skills/rules/*.mdc` 同步到 `<repo>/.cursor/rules/`**（指针规则，指向 `agent-skills/skills/.../SKILL.md`，不复制 SKILL 全文）
- 生成 `architecture/AGENTS.md` 作为跨仓工作空间级 agent 规则入口

> 说明：本目录只负责**脚本与模板**，不会自动修改用户级 `~/.cursor/hooks.json`。如需让 Cursor 在所有工作区都启用相同 hooks，可根据生成的模板手动合并。

## 目录结构（目标）

- `bootstrap.ps1`：Windows 入口脚本（PowerShell）
- `bootstrap.sh`：Linux/macOS 入口脚本（bash）
- `bootstrap.py`：跨平台核心逻辑
- `repos.manifest.json`：仓库清单与工作区元数据
- `templates/`
  - `workspace.code-workspace.json`：多根工作区模板
  - `architecture-AGENTS.md`：工作空间级 `architecture/AGENTS.md` 模板
  - `rtk-hook-cursor.ps1`：Windows RTK `preToolUse` hook
  - `rtk-hook-cursor.sh`：Linux/macOS RTK `preToolUse` hook（需 jq）

### Multi-root 与 Python 解释器

多根工作区中 **`${workspaceFolder:workspace}` 在 Cursor 里对 workspace 级 settings 支持不稳定**（尤其是 `python.defaultInterpreterPath`）。bootstrap 因此：

- `workspace` 根 folder 使用 `"path": "."`（不要写成 `"./."`）
- `python.defaultInterpreterPath` 写入 **绝对路径**（指向工作空间 `.venv`）

`workspace` folder 仍用于在侧栏查看 `.venv`、根级 `.gitignore` 等；`backend` / `frontend` 等子 folder 继续提供分仓视图（会有一定目录重复，属预期）。

## 调用示例

### Windows（PowerShell）

```powershell
cd J:\Code\nebula-workspace\nebula
.\workspace-bootstrap\bootstrap.ps1 `
  -WorkspaceRoot "J:\Code\nebula-workspace" `
  -Repos "nebula,nebula-studio"
```

### Linux / macOS

```bash
cd /path/to/nebula
./workspace-bootstrap/bootstrap.sh \
  --workspace-root "$HOME/Code/nebula-workspace" \
  --repos "nebula,nebula-studio"
```

## 参数约定（由 `bootstrap.py` 实现）

- `--workspace-root`：必选，工作空间根目录，例如 `J:\Code\nebula-workspace`
- `--repos`：可选，逗号分隔的仓库 key，默认 `all`
- `--skip-pull`：已存在仓库时跳过 `git pull`
- `--skip-graph-build`：只完成 CRG 安装和注册，不执行首次 `build/postprocess`
- `--skip-rtk`：跳过 RTK 下载与初始化（Windows 上仍会尝试修正已有 `CLAUDE.md` 中与 PowerShell 冲突的 `&&` 链式示例）
- `--force-rtk`：强制重新从 GitHub Releases 下载 RTK（即使 `.cursor/rtk/` 已存在）
- `--install-user-hooks`：将工作空间 PowerShell hooks 合并到 `~/.cursor/hooks.json`（修复 Windows Git Bash 弹窗）

`rtk init` 写入的 `CLAUDE.md` 默认使用 bash 风格 `&&`；**仅在 Windows** 上 bootstrap 会在各仓 `rtk init` 后自动 patch 为 PowerShell 的 `;`，与 `powershell-shell-workflow` 规则一致。Linux/macOS 保留 `&&`。

## 平台识别与差异

`bootstrap.py` 通过 `os.name` / `sys.platform` / `platform.machine()` 区分平台：

| 能力 | Windows (`os.name == "nt"`) | Linux / macOS |
| --- | --- | --- |
| RTK 下载包 | `rtk-x86_64-pc-windows-msvc.zip` | `darwin` / `linux-gnu` / `linux-musl`（按 CPU 架构） |
| RTK 二进制名 | `.cursor/rtk/rtk.exe` | `.cursor/rtk/rtk` |
| RTK Cursor hook | `rtk-hook-cursor.ps1` + PowerShell | `rtk-hook-cursor.sh` + bash（需安装 **jq**） |
| CRG hooks | `crg-*.ps1`（PowerShell Hidden） | `crg-*.sh`（系统 bash 或 Git Bash） |
| venv / CRG 路径 | `.venv/Scripts/` | `.venv/bin/` |
| CLAUDE.md `&&` → `;` patch | 是 | 否（bash 链式仍用 `&&`） |
| `--install-user-hooks` | 合并 PowerShell 路径到 `~/.cursor/hooks.json` | 不适用（无 Git Bash 弹窗问题） |

> **说明**：`rtk-hook-cursor.ps1` 是 Windows 专用；Unix 使用上游同协议的 `rtk-hook-cursor.sh`，但指向工作空间内 `.cursor/rtk/rtk` 而非全局 PATH。

详细行为见 `bootstrap.py` 内联文档。

## 从空目录验证步骤

1. 选择一个新的工作空间根目录，例如：`J:\Code\nebula-workspace-test`
2. 在 PowerShell 中执行：

   ```powershell
   cd J:\Code\nebula-workspace\nebula
   .\workspace-bootstrap\bootstrap.ps1 `
     -WorkspaceRoot "J:\Code\nebula-workspace-test" `
     -Repos "nebula,nebula-studio"
   ```

3. 验证目录结构：
   - `nebula/` 与 `nebula-studio/` 已 clone 或更新
   - `.venv/` 已创建
   - 根目录存在 `*.code-workspace` 文件
   - 存在 `architecture/AGENTS.md`
   - 存在 `nebula/.cursor/rules/*.mdc` 与 `nebula-studio/.cursor/rules/*.mdc`（由 `agent-skills/rules` 同步）
   - 存在 `.cursor/hooks.json` 与 `crg-*.ps1` / `crg-*.sh`

4. 打开该工作区的 `.code-workspace`，在 Cursor 中确认：
   - 后端、前端、architecture、.cursor 四个文件夹可见
   - Python 默认解释器指向工作空间 `.venv`

5. 在 PowerShell 中到任一仓根目录执行：
   - `J:\Code\nebula-workspace-test\.venv\Scripts\code-review-graph.exe status`
   - 确认图已构建（或按需手动执行 `build` 与 `postprocess`）

6. 在 Cursor 中触发一次文件保存和 `git commit`，根据当前版本对工作空间 `.cursor/hooks.json` 的支持情况：
   - 如 hooks 生效，应能在 CRG 数据库中看到增量更新
   - 如只识别用户级 `~/.cursor/hooks.json`，可参考生成的工作空间 hooks 配置手动合并到用户级配置


