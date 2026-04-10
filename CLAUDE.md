# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Code Agent Learn 是一个基于 DeepSeek API 的 AI 代码助手 CLI 工具。它通过工具调用架构提供交互式编程辅助功能，支持技能扩展和子代理执行。

## 开发命令

```bash
# 安装依赖
uv sync

# 运行交互式 CLI
uv run main.py

# 添加新依赖
uv add <package-name>

# 运行特定 Python 模块
uv run python -m <module>
```

## 核心架构

### Agent 循环机制

核心执行模型遵循以下模式：
1. 用户输入 → 流式 API 响应
2. 收集响应块（内容 + 工具调用）
3. 如果存在工具调用 → 执行工具 → 添加结果到消息 → 从步骤 1 重复
4. 如果没有工具调用 → 返回最终响应

关键实现：`agents/agent.py` - `agent_loop()` 方法处理流式响应和工具执行协调。

### 工具系统

工具分为两组：
- **PARENT_TOOLS**：完整工具集，包含 `task`（创建子代理）和 `save_memory`（持久化用户偏好）
- **CHILD_TOOLS**：子代理的受限集合（没有 `task` 工具以防止嵌套子代理）

工具在 `agents/tools.py` 中定义，使用 JSON 模式并通过 `TOOL_MAPPER` 映射到 Python 函数。

### 技能系统

技能从 `skills/` 目录自动发现。每个技能需要：
- `SKILL.md` 文件，包含 YAML frontmatter（name, description）
- 可选的 `references/` 文件夹用于文档

技能通过 `load_skill` 工具按需加载。技能加载器（`agents/utils/skill_loader.py`）扫描技能目录并向系统提示词提供描述。

已安装的技能：
- **agent-browser**：使用 CDP 协议的浏览器自动化
- **find-skills**：发现和安装新技能
- **frontend-design**：创建生产级前端界面

### 子代理机制

子代理在隔离上下文中执行任务：
- 独立的消息历史（从新开始）
- 仅使用 `CHILD_TOOLS`
- 返回结果给父代理
- 防止污染主对话历史

实现：`agents/sub_agent.py` - `run_subagent()` 函数

### 记忆系统

跨会话的持久记忆：
- **user**：用户偏好（例如"始终使用中文"，"偏好使用 tabs"）
- **feedback**：用户纠正
- **project**：从代码难以推断的项目特定约定
- **reference**：外部资源指针

记忆以 markdown 文件形式存储在 `.memory/` 目录，启动时加载到系统提示词中。

### 上下文压缩

当消息超过阈值（5000 条消息）时自动压缩：
- 工具调用结果压缩为摘要
- 旧消息替换为生成的摘要
- 可通过 `compression` 工具手动触发

实现：`agents/utils/context_compression.py`

### 权限系统

检查工具执行的安全层：
- 阻止危险命令（例如 `rm -rf /`, `sudo`）
- 可以请求用户确认敏感操作
- 验证文件路径在工作目录内

实现：`agents/utils/Permission.py`

## 关键实现细节

### 流式响应处理

Agent 以块的形式处理流式响应：
- 内容块：直接打印到控制台
- 工具调用块：通过 `deal_tool_chunk()` 方法增量组装
- 最终工具调用从块字典重建

### 文件操作

所有文件操作强制路径安全：
- `path_check()` 验证路径相对于工作目录
- 防止目录遍历攻击
- 仅支持 UTF-8 编码

### 任务追踪

`todo` 工具维护全局 `todoList` 对象：
- 最多 20 个任务
- 最多 1 个任务处于 "in_progress" 状态
- 如果空闲 3+ 轮，Agent 会被提醒更新列表

### 技能监视模式

后台守护进程监视技能文件变更：
- 修改时自动重载技能定义
- 在单独线程运行
- 实现：`agents/utils/watch_skill.py`

## 配置

`.env` 中必需的环境变量：
```
OPENAI_API_KEY=<your-api-key>
BASE_URL=https://api.deepseek.com
```

API 兼容 OpenAI SDK。模型名称在 `agents/agent.py` 中硬编码为 "glm-5"。
