import os
from agents.agent import Agent
from agents.tools import CHILD_TOOLS
from agents.utils.Permission import PermissionManager


SUB_SYSTEM = f"""你是 {os.getcwd()} 的coding subagent。完成指定任务，然后总结。

注意事项：
- 只能操作当前工作目录下的所有文件和目录，包括子级
- 执行危险命令会被拒绝
- 文件操作支持 UTF-8 编码
- 使用uv包管理工具，如果uv命令不存在，请先安装uv包，需要使用者确认安装
- 回复内容不用过于详细
"""


def run_subagent(prompt: str):
    """运行子agent"""
    message = [
        {"role": "system", "content": SUB_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    permission = PermissionManager()

    out = Agent(
        messages=message,
        tools=CHILD_TOOLS,
        isSubAgent=True,
        permission=permission,
    ).run()
    print(f"子agent回复: {out}")
    return out
