import subprocess
import os

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

TOOLS = [
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
                "required": ["command"]
            },
        }
    },
]

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

TOOL_MAPPER = {
    "bash": run_bash,
}
