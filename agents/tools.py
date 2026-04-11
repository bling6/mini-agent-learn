from pathlib import Path
import subprocess
import os
import json
from .todo import todoList
from .utils.skill_loader import SKILL_LOADER
from .utils.Memory import memory_manager
from .task import taskManager
from .background_task import bgManager
from .teams import messageBus, teamManager, VALID_MSG_TYPES


# TOOLS = [
#     {
#         "name": "bash",
#         "description": "运行shell命令",
#         "parameters": {
#             "type": "object",
#             "properties": {"command": {"type": "string"}},
#             "required": ["command"],
#         },
#     }
# ]

BASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "运行shell命令",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要运行的shell命令",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入文件内容,用于创建新文件或完全覆盖已存在文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要写入的文件路径",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的内容",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "编辑现有文件内容,通过查找和替换特定文本来修改文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要编辑的文件路径",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "要替换的原始文本(必须精确匹配)",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "要替换为的文本",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo",
            "description": "创建和更新简单的待办任务事项列表。跟踪多步骤任务的进度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "要更新的任务列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "任务ID",
                                },
                                "text": {
                                    "type": "string",
                                    "description": "任务文本",
                                },
                                "status": {
                                    "type": "string",
                                    "description": "任务状态",
                                    "enum": ["pending", "in_progress", "completed"],
                                },
                            },
                            "required": ["id", "text", "status"],
                        },
                    },
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": "加载技能的具体内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "要加载的技能名称",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {"name": "compression", "description": "手动触发上下文消息压缩"},
    },
]

BUS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "发送任务消息给队友",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                    },
                    "content": {
                        "type": "string",
                    },
                    "msg_type": {
                        "type": "string",
                        "enum": list(VALID_MSG_TYPES),
                    },
                },
                "required": ["to", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_inbox",
            "description": "仔细阅读并清空lead的收件箱。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]
CHILD_TOOLS = BASE_TOOLS
PARENT_TOOLS = (
    CHILD_TOOLS
    + BUS_TOOLS
    + [
        {
            "type": "function",
            "function": {
                "name": "spawn_agent",
                "description": "生成一个具有全新上下文的子代理,用于执行指定任务",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "要运行的任务描述",
                        }
                    },
                    "required": ["prompt"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "save_memory",
                "description": "保存跨会话保留的持久记忆。如果保存的内容与之前有相似，考虑合并。如果内容意思相反，考虑覆盖。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "简短标识符（例如 prefer_tabs、db_schema）",
                        },
                        "description": {
                            "type": "string",
                            "description": "用一句话概括这段记忆的内容",
                        },
                        "type": {
                            "type": "string",
                            "description": "user=偏好设置, feedback=用户明确纠正过你的地方。, project=不容易从代码直接重新看出来的项目约定或背景, reference=外部资源指针",
                            "enum": ["user", "feedback", "project", "reference"],
                        },
                        "content": {
                            "type": "string",
                            "description": "完整的记忆内容，可多行显示",
                        },
                    },
                    "required": ["name", "description", "type", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "task_create",
                "description": "创建一个持久化任务(utf-8编码)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "任务内容",
                        },
                        "description": {
                            "type": "string",
                            "description": "任务补充说明",
                        },
                    },
                    "required": ["subject"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "task_update",
                "description": "更新一个任务的状态",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "任务ID",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "deleted"],
                            "description": "任务状态",
                        },
                        "owner": {
                            "type": "string",
                            "description": "当队友认领任务时设置",
                        },
                        "addBlockedBy": {
                            "type": "array",
                            "items": {
                                "description": "前置任务ID",
                                "type": "integer",
                            },
                            "description": "要添加的前置任务ID列表,只有前置任务完成才能执行当前任务",
                        },
                        "addBlocks": {
                            "type": "array",
                            "items": {
                                "description": "后续任务ID",
                                "type": "integer",
                            },
                            "description": "要添加的后续任务ID列表,只有当前任务完成才能执行后续任务",
                        },
                    },
                    "required": ["task_id", "status"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "task_list",
                "description": "列出所有任务及其状态摘要",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "task_get",
                "description": "获取一个任务详情",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "任务ID",
                        },
                    },
                    "required": ["task_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "task_del",
                "description": "删除多个任务文件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_ids": {
                            "type": "array",
                            "items": {
                                "type": "integer",
                                "description": "任务ID",
                            },
                            "description": "任务ID列表",
                        },
                    },
                    "required": ["task_ids"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "background_run",
                "description": "在后台线程中运行command。立即返回 task_id。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "要运行的命令",
                        },
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_background",
                "description": "检查后台线程任务的状态。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "任务ID",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "spawn_teammate",
                "description": "生成或者唤醒一个在独立线程中运行的持久队友，然后要用send_message工具发送任务消息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"},
                        "prompt": {"type": "string"},
                    },
                    "required": ["name", "role", "prompt"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_teammates",
                "description": "列出所有队友的名称、角色和状态",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "broadcast",
                "description": "广播消息给所有队友",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                        },
                    },
                    "required": ["content"],
                },
            },
        },
    ]
)
WORKDIR = Path.cwd()


def path_check(p: str):
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError("路径必须是相对于当前工作目录的路径")
    return path


# bash 命令工具
def run_bash(command: str):
    print(f"\033[33m运行命令: {command}\033[0m")
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "命令包含危险字符，拒绝执行"
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:8000] if out else "(无输出)"
    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"命令执行失败: {e}"


# 读取文件工具
def run_read_file(path: str):
    try:
        file_path = path_check(path).expanduser()
        if not file_path.exists() or not file_path.is_file():
            return f"文件 {file_path} 不存在"
        content = file_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return f"文件 {file_path} 读取失败: {e}"


# 写入文件工具
def run_write_file(path: str, content: str):
    try:
        file_path = path_check(path).expanduser()
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"文件 {file_path} 写入成功"
    except Exception as e:
        return f"文件 {file_path} 写入失败: {e}"


# 编辑文件工具
def run_edit_file(path: str, old_text: str, new_text: str):
    try:
        file_path = path_check(path).expanduser()
        # 确保目录存在
        old_content = file_path.read_text(encoding="utf-8")
        if old_text not in old_content:
            return f"文件 {file_path} 中不存在 {old_text}"
        content = old_content.replace(old_text, new_text, 1)
        file_path.write_text(content, encoding="utf-8")
        return f"文件 {file_path} 编辑成功"
    except Exception as e:
        return f"文件 {file_path} 编辑失败: {e}"


# 保存记忆工具
def run_save_memory(name: str, description: str, type: str, content: str) -> str:
    return memory_manager.save_memory(name, description, type, content)


TOOL_MAPPER = {
    "bash": run_bash,
    "read_file": lambda **kw: run_read_file(kw["path"]),
    "write_file": lambda **kw: run_write_file(kw["path"], kw["content"]),
    "edit_file": lambda **kw: run_edit_file(kw["path"], kw["old_text"], kw["new_text"]),
    "todo": lambda **kw: todoList.update(kw["items"]),
    "load_skill": lambda **kw: SKILL_LOADER.get_content(kw["name"]),
    "save_memory": lambda **kw: run_save_memory(
        kw["name"], kw["description"], kw["type"], kw["content"]
    ),
    "task_create": lambda **kw: taskManager.create(
        kw["subject"], kw.get("description", "")
    ),
    "task_update": lambda **kw: taskManager.update(
        kw["task_id"],
        kw.get("status"),
        kw.get("owner"),
        kw.get("addBlockedBy"),
        kw.get("addBlocks"),
    ),
    "task_list": taskManager.list_all,
    "task_get": lambda **kw: taskManager.get(kw["task_id"]),
    "task_del": lambda **kw: taskManager.del_file(kw["task_ids"]),
    "background_run": lambda **kw: bgManager.run(kw["command"]),
    "check_background": lambda **kw: bgManager.check(kw.get("task_id")),
    "spawn_teammate": lambda **kw: teamManager.spawn(
        kw["name"], kw["role"], kw["prompt"]
    ),
    "list_teammates": lambda **kw: teamManager.list_all(),
    "send_message": lambda **kw: messageBus.send(
        "lead", kw["to"], kw["content"], kw.get("msg_type", "message")
    ),
    "read_inbox": lambda **kw: json.dumps(messageBus.read_inbox("lead"), indent=2),
    "broadcast": lambda **kw: messageBus.broadcast(
        "lead", kw["content"], teamManager.member_names()
    ),
}
