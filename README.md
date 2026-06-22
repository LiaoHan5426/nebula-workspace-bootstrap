# Nebula 工作空间自动构建脚本

本目录包含一套用于从**空目录**自动搭建 Nebula 工作空间的脚本，目标是一次性完成：

- 克隆 / 更新任意 Git 仓库（支持指定任意仓库，不再依赖默认配置）
- 在工作空间根目录生成多根 `*.code-workspace` 文件
- 创建 Python 虚拟环境并安装 `code-review-graph`
- 为各仓构建 / 更新 CRG 图并完成注册
- 为 Windows 提供兼容 PowerShell 的 CRG hooks（可选 Git for Windows Bash 回退）
- **从 [RTK Releases](https://github.com/rtk-ai/rtk/releases) 下载 RTK 到 `.cursor/rtk/` 并完成 `rtk init`**
- 配置工作空间级 `.cursor` 目录与 hooks 资产（含 RTK `preToolUse` hook）
- **将各仓 `agent-skills/rules/*.mdc` 同步到 `<repo>/.cursor/rules/`**（指针规则，指向 `agent-skills/skills/.../SKILL.md`，不复制 SKILL 全文）
- 生成 `architecture/AGENTS.md` 作为跨仓工作空间级 agent 规则入口

> 说明：本目录只负责**脚本与模板**，不会自动修改用户级 `~/.cursor/hooks.json`。如需让 Cursor 在所有工作区都启用相同 hooks，可根据生成的模板手动合并。

## 目录结构

```
workspace-bootstrap/
├── .gitignore
├── README.md
├── bootstrap-onefile.ps1   # PowerShell 单文件版本（支持远程执行）
├── bootstrap-onefile.py    # Python 单文件版本（支持远程执行）
├── bootstrap-onefile.sh    # Bash 单文件版本（支持远程执行）
├── bootstrap.ps1           # PowerShell 模块化版本入口
├── bootstrap.py            # 模块化版本主入口
├── bootstrap.sh            # Bash 模块化版本入口
├── repos.manifest.json     # 配置文件（已移除默认仓库）
├── src/                    # 模块化子模块
│   ├── __init__.py
│   ├── config.py           # 配置解析
│   ├── crg.py              # Code Review Graph 管理
│   ├── editor.py           # 编辑器配置（Cursor/Trae）
│   ├── git.py              # Git 操作
│   ├── hooks.py            # Hooks 配置
│   ├── rtk.py              # RTK 安装与配置
│   ├── utils.py            # 工具函数
│   ├── venv.py             # 虚拟环境管理
│   └── workspace.py        # 工作空间构建
└── templates/              # 模板文件
    ├── architecture-AGENTS.md
    ├── rtk-hook-cursor.ps1
    ├── rtk-hook-cursor.sh
    └── workspace.code-workspace.json
```

### Multi-root 与 Python 解释器

多根工作区中 **`${workspaceFolder:workspace}` 在 Cursor 里对 workspace 级 settings 支持不稳定**（尤其是 `python.defaultInterpreterPath`）。bootstrap 因此：

- `workspace` 根 folder 使用 `"path": "."`（不要写成 `"./."`）
- `python.defaultInterpreterPath` 写入 **绝对路径**（指向工作空间 `.venv`）

`workspace` folder 仍用于在侧栏查看 `.venv`、根级 `.gitignore` 等；`backend` / `frontend` 等子 folder 继续提供分仓视图（会有一定目录重复，属预期）。

## 快速开始

### 方式一：交互式模式（推荐）

```powershell
# PowerShell
python bootstrap.py
# 或
.\bootstrap.ps1

# Bash
python bootstrap.py
# 或
./bootstrap.sh
```

### 方式二：命令行参数模式

```powershell
# PowerShell
python bootstrap.py --workspace-root "J:\Code\nebula-workspace" --repo https://github.com/user/repo.git

# Bash
python bootstrap.py --workspace-root "$HOME/Code/nebula-workspace" --repo https://github.com/user/repo.git
```

### 方式三：远程执行（无需克隆仓库）

```powershell
# PowerShell 远程执行（交互式模式）
irm https://raw.githubusercontent.com/LiaoHan5426/nebula-workspace-bootstrap/master/bootstrap-onefile.ps1 | iex

# PowerShell 远程执行（带参数）
irm https://raw.githubusercontent.com/LiaoHan5426/nebula-workspace-bootstrap/master/bootstrap-onefile.ps1 | iex -ArgumentList "-WorkspaceRoot 'J:\Code\nebula-workspace', -Repo 'https://github.com/LiaoHan5426/nebula.git'"

# Python 远程执行
python -c "$(curl -s https://raw.githubusercontent.com/LiaoHan5426/nebula-workspace-bootstrap/master/bootstrap-onefile.py)" --workspace-root /path/to/workspace --repo https://github.com/user/repo.git

# Bash 远程执行
curl -s https://raw.githubusercontent.com/LiaoHan5426/nebula-workspace-bootstrap/master/bootstrap-onefile.sh | bash -s -- --workspace-root /path/to/workspace --repo https://github.com/user/repo.git
```

## 参数约定

### 核心参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--workspace-root` | 必选，工作空间根目录 | 无 |
| `--repo` | 可选，Git 仓库 URL 或完整 spec（可多次指定） | 无 |
| `--repos` | 遗留模式：从 manifest 选择仓库（不推荐） | `all` |
| `--editor` | 编辑器类型：`all`、`cursor`、`trae` | `all` |
| `--interactive`, `-i` | 进入交互式配置模式 | 无参数时自动进入 |

### 仓库 Spec 格式

```bash
# 简单格式（直接 URL）
--repo https://github.com/user/repo.git

# 完整格式
--repo name=myrepo,url=https://github.com/user/repo.git,dir=local-dir,alias=crg-alias
```

### 高级参数

| 参数 | 说明 |
|------|------|
| `--skip-pull` | 已存在仓库时跳过 `git pull` |
| `--skip-graph-build` | 只完成 CRG 安装和注册，不执行首次 `build/postprocess` |
| `--skip-rtk` | 跳过 RTK 下载与初始化 |
| `--force-rtk` | 强制重新从 GitHub Releases 下载 RTK |
| `--install-user-hooks` | 将工作空间 PowerShell hooks 合并到 `~/.cursor/hooks.json` |
| `--force-agents` | 强制覆盖 `architecture/AGENTS.md` |
| `--force` | 强制重新初始化工作空间 |
| `--yes`, `-y` | 自动确认所有提示 |

## 使用示例

### 示例 1：初始化工作空间（指定单个仓库）

```powershell
python bootstrap.py --workspace-root "J:\Code\nebula-workspace" --repo https://github.com/LiaoHan5426/nebula.git
```

### 示例 2：初始化工作空间（多个仓库）

```powershell
python bootstrap.py --workspace-root "J:\Code\nebula-workspace" ^
    --repo https://github.com/LiaoHan5426/nebula.git ^
    --repo https://github.com/LiaoHan5426/nebula-studio.git
```

### 示例 3：指定仓库详细配置

```powershell
python bootstrap.py --workspace-root "J:\Code\nebula-workspace" ^
    --repo name=backend,url=https://github.com/LiaoHan5426/nebula.git,dir=nebula,alias=nebula ^
    --repo name=frontend,url=https://github.com/LiaoHan5426/nebula-studio.git,dir=nebula-studio,alias=studio
```

### 示例 4：仅为 Trae 编辑器初始化

```powershell
python bootstrap.py --workspace-root "J:\Code\nebula-workspace" ^
    --repo https://github.com/LiaoHan5426/nebula.git ^
    --editor trae
```

### 示例 5：跳过 RTK 安装

```powershell
python bootstrap.py --workspace-root "J:\Code\nebula-workspace" ^
    --repo https://github.com/LiaoHan5426/nebula.git ^
    --skip-rtk
```

### 示例 6：强制重新初始化

```powershell
python bootstrap.py --workspace-root "J:\Code\nebula-workspace" ^
    --repo https://github.com/LiaoHan5426/nebula.git ^
    --force --yes
```

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

## 从空目录验证步骤

1. 选择一个新的工作空间根目录，例如：`J:\Code\nebula-workspace-test`

2. 执行 bootstrap：

   ```powershell
   python bootstrap.py --workspace-root "J:\Code\nebula-workspace-test" --repo https://github.com/LiaoHan5426/nebula.git
   ```

3. 验证目录结构：
   - `nebula/` 已 clone 或更新
   - `.venv/` 已创建
   - 根目录存在 `*.code-workspace` 文件
   - 存在 `architecture/AGENTS.md`
   - 存在 `.cursor/hooks.json` 与 `crg-*.ps1` / `crg-*.sh`

4. 打开该工作区的 `.code-workspace`，在 Cursor/Trae 中确认：
   - 工作空间文件夹可见
   - Python 默认解释器指向工作空间 `.venv`

5. 在终端中到任一仓根目录执行：
   ```powershell
   J:\Code\nebula-workspace-test\.venv\Scripts\code-review-graph.exe status
   ```
   确认图已构建（或按需手动执行 `build` 与 `postprocess`）

6. 在编辑器中触发一次文件保存和 `git commit`，确认 hooks 生效。

## 编辑器支持

### Cursor 模式

- 配置 `.cursor` 目录和 hooks
- 同步 agent-skills 规则到 `.cursor/rules/`

### Trae 模式

- 安装 RTK 工具
- 配置 hooks
- 配置 MCP（模型上下文协议）

### All 模式（默认）

同时配置 Cursor 和 Trae 所需的所有组件。

## 容错机制

- **工作空间已初始化检测**：检测 `.venv`、`repos`、`.cursor` 目录，提示用户确认是否覆盖
- **`--force` 参数**：强制重新初始化，跳过确认提示
- **`--yes` 参数**：自动确认所有提示，适合脚本化执行
- **网络容错**：Git 克隆失败时重试，RTK 下载失败时提示手动安装

## 迁移说明

### 从旧版本迁移

1. 移除 `repos.manifest.json` 中的默认仓库配置（已完成）
2. 使用 `--repo` 参数替代 `--repos`
3. 建议使用交互式模式或远程执行方式

### 远程仓库支持

本脚本已发布到 GitHub：`https://github.com/LiaoHan5426/nebula-workspace-bootstrap`

支持通过 `curl` / `irm` 远程执行，无需提前克隆仓库。
