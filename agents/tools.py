from pathlib import Path
import subprocess
import os
from .todo import todoList
from .utils.skill_loader import SKILL_LOADER


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
            "description": "更新任务列表。跟踪多步骤任务的进度。",
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
        "function": {
            "name": "compression",
            "description": "手动触发上下文消息压缩"
        },
    },
]
CHILD_TOOLS = BASE_TOOLS
PARENT_TOOLS = CHILD_TOOLS + [
    {
        "type": "function",
        "function": {
            "name": "task",
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
]

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


TOOL_MAPPER = {
    "bash": run_bash,
    "read_file": run_read_file,
    "write_file": run_write_file,
    "edit_file": run_edit_file,
    "todo": todoList.update,
    "load_skill": SKILL_LOADER.get_content,
}
