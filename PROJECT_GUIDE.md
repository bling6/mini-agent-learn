# Code Agent Learn - 项目指南

## 📋 项目简介

**Code Agent Learn** 是一个基于 DeepSeek API 的 AI 代码助手 CLI 工具，提供交互式编程辅助功能。它支持工具调用、技能扩展和子任务执行，可以帮助开发者完成代码编写、文件操作、浏览器自动化等任务。

### 核心特性

- 🤖 **智能对话**: 基于大语言模型的交互式编程助手
- 🔧 **工具调用**: 支持文件操作、命令执行、任务管理等工具
- 🔌 **技能系统**: 可扩展的技能架构，支持浏览器自动化等功能
- 🔄 **子任务机制**: 独立上下文的子 Agent 执行特定任务
- 📊 **任务追踪**: 内置任务列表管理，跟踪多步骤任务进度
- 🔍 **实时监视**: 自动监视技能文件变更并重载

## 🏗️ 项目结构

```
code-agent-learn/
├── main.py                    # 主程序入口（CLI 交互）
├── agents/                    # Agent 核心模块
│   ├── agent.py              # Agent 类实现，处理 API 调用和工具执行
│   ├── sub_agent.py          # 子 Agent 实现（独立上下文）
│   ├── tools.py              # 工具定义和实现
│   ├── todo.py               # 任务列表管理
│   ├── loop.py               # Agent 循环实现（已废弃）
│   └── utils/                # 工具模块
│       ├── skill_loader.py   # 技能加载器
│       ├── watch_skill.py    # 技能文件监视器
│       └── context_compression.py  # 上下文压缩
├── skills/                    # 技能目录
│   ├── agent-browser/        # 浏览器自动化技能
│   │   ├── SKILL.md          # 技能定义
│   │   └── references/       # 参考文档
│   └── find-skills/          # 技能发现技能
│       └── SKILL.md
├── pyproject.toml            # 项目配置
├── .env                      # 环境变量配置
├── CLAUDE.md                 # Claude Code 指引
└── README.md                 # 项目说明
```

## 🚀 快速开始

### 1. 环境准备

确保你的系统已安装：
- Python 3.12+
- uv 包管理工具

### 2. 安装依赖

```bash
# 安装依赖
uv sync
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
OPENAI_API_KEY="your-api-key-here"
BASE_URL="https://api.deepseek.com"
```

### 4. 运行程序

```bash
# 启动交互式 CLI
uv run main.py
```

### 5. 使用命令

在交互界面中：
- 输入自然语言问题或任务
- 输入 `clear` 清空对话历史
- 输入 `history` 查看对话历史
- 输入 `exit`、`quit`、`q` 或按 `Ctrl+D` 退出

## 💡 核心架构

### 1. Agent 循环机制

```
用户输入 → 发送 API (流式) → 收集响应 
    ↓
工具调用？ → 是 → 执行工具 → 添加结果到消息 → 再次调用 API
    ↓
    否 → 返回最终响应
```

### 2. 工具系统

Agent 可用的工具定义在 `agents/tools.py`：

| 工具名 | 功能描述 | 使用场景 |
|--------|---------|---------|
| `bash` | 执行 shell 命令 | 运行命令、安装包、文件操作 |
| `read_file` | 读取文件内容 | 查看代码、配置文件 |
| `write_file` | 写入文件 | 创建新文件、覆盖文件 |
| `edit_file` | 编辑文件 | 修改现有文件内容 |
| `todo` | 任务列表管理 | 跟踪多步骤任务 |
| `load_skill` | 加载技能内容 | 使用特定技能 |
| `task` | 创建子 Agent | 执行独立任务 |

### 3. 技能系统

技能存放在 `skills/` 目录，采用约定优于配置的设计：

**技能结构：**
```
skills/
└── skill-name/
    ├── SKILL.md          # 必需：技能定义文件
    └── references/       # 可选：参考文档
```

**SKILL.md 格式：**
```markdown
---
name: skill-name
description: 技能简短描述
---

# 技能详细内容
这里是技能的详细说明和使用指南...
```

**已安装技能：**
- **agent-browser**: 浏览器自动化工具，支持网页交互、表单填写、截图等
- **find-skills**: 技能发现工具，帮助查找和安装新技能

### 4. 子 Agent 机制

子 Agent 特点：
- 拥有独立的消息上下文
- 使用 `CHILD_TOOLS`（不包含 `task` 工具）
- 用于执行特定任务后返回结果
- 避免污染主对话历史

## 🛠️ 技术栈

- **语言**: Python 3.12+
- **包管理**: uv
- **AI 框架**: LangChain, OpenAI SDK
- **API**: DeepSeek API（兼容 OpenAI API）
- **测试**: Pytest

### 主要依赖

```toml
- dotenv>=0.9.9          # 环境变量管理
- langchain>=1.2.13      # AI 应用框架
- langchain-openai>=1.1.12  # OpenAI 集成
- openai>=2.30.0         # OpenAI SDK
- pytest>=9.0.2          # 测试框架
- pyyaml>=6.0.3          # YAML 解析
- watchdog>=6.0.0        # 文件监视
```

## 📖 开发指南

### 添加新技能

1. 在 `skills/` 下创建新目录
2. 创建 `SKILL.md` 文件，添加 YAML frontmatter
3. （可选）添加 `references/` 参考文档
4. 技能会自动被加载和识别

示例：
```markdown
---
name: my-skill
description: 我的自定义技能
---

# My Skill

这个技能用于...

## 使用方法
...
```

### 自定义工具

在 `agents/tools.py` 中添加新工具：

```python
def my_custom_tool(param: str) -> str:
    """工具描述"""
    # 实现逻辑
    return "结果"
```

然后在 `TOOLS` 或 `CHILD_TOOLS` 中注册。

### 安全限制

- **路径限制**: 只能操作当前工作目录及其子目录
- **命令过滤**: 危险命令会被拒绝（如 `rm -rf /`）
- **超时限制**: 工具执行超时 120 秒
- **输出限制**: 输出长度有限制，避免内存溢出
- **编码支持**: 文件操作支持 UTF-8 编码

## 🔍 常见问题

### 1. 如何清空对话历史？
输入 `clear` 命令

### 2. 如何查看完整的对话历史？
输入 `history` 命令

### 3. 技能文件修改后会自动生效吗？
是的，`watch_skill.py` 会监视技能文件变更并自动重载

### 4. 如何使用 uv 安装新包？
```bash
uv add package-name
```

### 5. 子 Agent 和主 Agent 有什么区别？
子 Agent 拥有独立上下文，无法创建子任务（没有 `task` 工具），适合执行独立任务。

## 📝 开发注意事项

1. **包管理**: 必须使用 uv，不要使用 pip
2. **文件操作**: 必须在当前工作目录内
3. **任务列表**: 最多 20 个任务，最多 1 个进行中任务
4. **技能加载**: 仅在需要时加载技能内容
5. **回复风格**: 简洁明了，不过于详细

## 🎯 使用场景

- 代码编写和重构
- 文件操作和管理
- 浏览器自动化测试
- 技能扩展和定制
- 多步骤任务自动化
- 项目文档生成

## 📄 License

MIT

---

**Happy Coding! 🎉**
