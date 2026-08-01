# Nebula 多仓库工作空间

本仓库既是 Nebula 工作空间的控制仓库，也是可重复执行的构建工具。

它负责版本管理跨仓库内容，并根据 `repos.manifest.json` 克隆或更新后端与前端仓库。前后端仍保留各自独立的 Git 历史。

安装器使用 Git sparse-checkout，只把工作空间需要的文档、架构、manifest
和命令入口放到目标根目录。bootstrap 实现保存在用户级缓存目录中
（Windows 为 `%LOCALAPPDATA%\nebula-workspace-bootstrap`），不会进入工作空间。

## 工作空间结构

```text
nebula-workspace/
├── .git/                         # 本控制仓库
├── docs/                         # 跨仓库规划与设计
├── architecture/                 # 系统级架构
├── repos.manifest.json           # 子仓库声明
├── .knowledge/agent-memory/      # 私有中央知识库（父仓库忽略）
├── bootstrap.py                  # Python 构建入口
├── workspace.ps1                 # Windows 统一命令
├── workspace.sh                  # Linux/macOS 统一命令
├── nebula/                       # 后端独立 Git 仓库（父仓库忽略）
└── nebula-studio/                # 前端独立 Git 仓库（父仓库忽略）
```

工作空间控制仓库保存：

- 跨前后端的开发规划、架构决策和联调说明；
- 仓库 URL、默认分支和本地目录约定；
- VS Code/Cursor 多根工作区生成逻辑；
- CRG、RTK、编辑器规则和 hooks 的初始化逻辑。
- 中央知识库克隆、项目模块清单刷新、新鲜度检查和 Hermes CRG MCP 注册。

## 在新机器上构建

前置依赖：Git、Python 3，以及能读取私有仓库 `LiaoHan5426/agent-memory` 的 GitHub 凭据。

### Windows

一条命令完成克隆和构建：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod https://raw.githubusercontent.com/LiaoHan5426/nebula-workspace-bootstrap/master/install.ps1))) -WorkspaceRoot J:\Code\nebula-workspace
```

或者分步执行：

```powershell
git clone https://github.com/LiaoHan5426/nebula-workspace-bootstrap.git J:\Code\nebula-workspace
J:\Code\nebula-workspace\workspace.ps1 init
```

### Linux/macOS

一条命令：

```bash
curl -fsSL https://raw.githubusercontent.com/LiaoHan5426/nebula-workspace-bootstrap/master/install.sh | bash -s -- ~/Code/nebula-workspace
```

或者分步执行：

```bash
git clone https://github.com/LiaoHan5426/nebula-workspace-bootstrap.git ~/Code/nebula-workspace
~/Code/nebula-workspace/workspace.sh init
```

`init` 默认读取 `repos.manifest.json` 中的全部仓库，不需要重复填写前后端 URL。

它还会把中央知识库克隆到工作区相对路径 `.knowledge/agent-memory`，自动刷新
后端 Maven 模块地图和前端 workspace 地图，并在检测到 Hermes CLI 时用
`hermes mcp add` 注册工作区虚拟环境中的 code-review-graph MCP。共享配置不写
盘符、用户名或其他机器绝对路径。

初始化后，两个源码仓库的 `.hermes.md` 会从 `WIKI_PATH` 或相对路径
`../.knowledge/agent-memory` 激活项目知识。可手工检查项目知识新鲜度：

```powershell
python .knowledge\agent-memory\scripts\project_navigation.py check --workspace-root .
```

如果只需要基础工作空间、暂时不安装 RTK 或不构建代码图：

```powershell
.\workspace.ps1 init -SkipRtk -SkipGraphBuild
```

## 日常更新

Windows：

```powershell
.\workspace.ps1 update
```

Linux/macOS：

```bash
./workspace.sh update
```

更新命令先以 `git pull --ff-only` 更新工作空间控制仓库，再更新 manifest 中的子仓库并重新生成本机配置。

## 诊断

```powershell
.\workspace.ps1 doctor
```

诊断命令会确认根目录是否为有效的工作空间 Git 仓库，并检查前后端仓库、中央知识库和 code-review-graph 可执行文件是否存在。

工具不会把“仅存在一个空 `.git` 目录”的旧工作空间视为有效仓库，也不会自动覆盖非空的无版本工作空间。

## 直接使用 Python

默认构建 manifest 中的全部仓库：

```powershell
python bootstrap.py --workspace-root . --yes
```

只构建指定仓库：

```powershell
python bootstrap.py --workspace-root . --repos nebula --yes
```

临时追加任意仓库：

```powershell
python bootstrap.py --workspace-root . `
  --repo name=example,url=https://github.com/example/example.git,dir=example,branch=main `
  --yes
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--repos all` | 使用 manifest 中的全部仓库 |
| `--repo SPEC` | 使用临时仓库声明，可重复传入 |
| `--skip-pull` | 已存在的子仓库不执行 pull |
| `--skip-graph-build` | 跳过首次 CRG 图构建 |
| `--skip-rtk` | 跳过 RTK 下载和初始化 |
| `--force-rtk` | 强制重新下载 RTK |
| `--editor cursor\|trae\|all` | 选择编辑器配置 |
| `--yes`, `-y` | 非交互执行 |

## 文档归属

- 跨仓库规划放在根目录 `docs/`。
- 跨仓库架构放在根目录 `architecture/`。
- 仅与后端相关的文档放入 `nebula` 仓库。
- 仅与前端相关的文档放入 `nebula-studio` 仓库。

## 从旧工作空间迁移

旧的 `J:\Code\nebula-workspace` 根目录不是有效 Git 仓库时，先备份其中的 `docs/`、`architecture/`、`docker-compose.yml` 等根级文件。然后：

1. 将本控制仓库克隆为新的工作空间根目录；
2. 把旧前后端仓库移动回对应目录，或让初始化命令重新克隆；
3. 将备份的跨仓库文档复制到新根目录；
4. 检查并提交这些文档到控制仓库。

不要直接对含空 `.git` 目录的旧工作空间执行 `git add .`。两个子仓库必须由根 `.gitignore` 排除，不能误添加成 embedded repository。
