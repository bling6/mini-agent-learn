from pathlib import Path
import json

TASKS_DIR = Path.cwd() / ".tasks"


class TaskManager:
    def __init__(self, tasks_dir: Path):
        self.dir = tasks_dir
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1

    def _max_id(self) -> int:
        ids = [int(f.stem.split("_")[1]) for f in self.dir.glob("task_*.json")]
        return max(ids) if ids else 0

    def _load(self, task_id: int) -> dict:
        task_path = self.dir / f"task_{task_id}.json"
        if not task_path.exists() or not task_path.is_file():
            return None
        with task_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, task: dict):
        task_path = self.dir / f"task_{task['id']}.json"
        with task_path.open("w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)

    def get(self, task_id: int) -> str:
        return json.dumps(self._load(task_id), ensure_ascii=False, indent=2)

    def create(self, subject: str, description: str = "") -> str:
        task = {
            "id": self._next_id,  # 任务ID
            "subject": subject,  # 任务内容
            "description": description,  # 任务补充说明
            "status": "pending",  # 任务状态
            "blockedBy": [],  # 前置任务ID
            "blocks": [],  # 后续任务ID
            "owner": "",  # 任务负责人
        }
        self._save(task)
        self._next_id += 1
        return json.dumps(task, ensure_ascii=False, indent=2)

    def update(
        self,
        task_id: int,
        status: str = None,
        owner: str = None,
        add_blocked_by: list = None,
        add_blocks: list = None,
    ) -> str:
        task = self._load(task_id)
        if task is None:
            return f"任务ID {task_id} 不存在"
        # 更新任务负责人
        if owner is not None:
            task["owner"] = owner
        if status is not None:
            if status not in ("pending", "in_progress", "completed", "deleted"):
                raise ValueError(f"无效的任务状态: {status}")
            task["status"] = status
        if status == "completed":
            self._clear_dependency(task_id)
        if add_blocked_by:
            task["blockedBy"] = list(set(task["blockedBy"] + add_blocked_by))
        if add_blocks:
            task["blocks"] = list(set(task["blocks"] + add_blocks))
            for blocked_id in add_blocks:
                try:
                    blocked_task = self._load(blocked_id)
                    if task_id not in blocked_task["blockedBy"]:
                        blocked_task["blockedBy"].append(task_id)
                        self._save(blocked_task)
                except Exception:
                    pass
        self._save(task)
        return json.dumps(task, ensure_ascii=False, indent=2)

    def _clear_dependency(self, task_id: int):
        for f in self.dir.glob("task_*.json"):
            task = json.loads(f.read_text(encoding="utf-8"))
            if task_id in task.get("blockedBy", []):
                task["blockedBy"].remove(task_id)
            self._save(task)

    def list_all(self) -> str:
        tasks = []
        for f in sorted(self.dir.glob("task_*.json")):
            tasks.append(json.loads(f.read_text(encoding="utf-8")))
        if not tasks:
            return "暂无任务"

        lines = []
        for task in tasks:
            marker = {
                "pending": "[ ]",
                "in_progress": "[>]",
                "completed": "[✅]",
                "deleted": "[-]",
            }.get(task["status"], "[?]")
            blocked = (
                f" (blocked by: {task['blockedBy']})" if task.get("blockedBy") else ""
            )
            owner = f" owner={task['owner']}" if task.get("owner") else ""
            lines.append(f"{marker} #{task['id']}: {task['subject']}{owner}{blocked}")

        return "\n".join(lines)

    def del_file(self, task_ids: list) -> str:
        for task_id in task_ids:
            task_path = self.dir / f"task_{task_id}.json"
            if task_path.exists() and task_path.is_file():
                task_path.unlink()
        return f"任务ID {','.join(map(str, task_ids))} 已删除"


task_manager = TaskManager(TASKS_DIR)
