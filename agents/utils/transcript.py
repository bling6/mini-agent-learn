import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any


class TranscriptManager:
    """管理 agent 对话历史的持久化"""

    def __init__(self, transcript_dir: Path = None):
        self.dir = transcript_dir or (Path.cwd() / ".transcripts")
        self.dir.mkdir(parents=True, exist_ok=True)
        # 每次启动生成一个 session id，同一会话的所有 agent 共享
        self.session_id = time.strftime("%Y%m%d_%H%M%S")

    def _get_file_path(self, agent_name: str) -> Path:
        """获取指定 agent 本次会话的 transcript 文件路径"""
        filename = f"{self.session_id}_{agent_name}.jsonl"
        return self.dir / filename

    def _already_saved(self, agent_name: str) -> bool:
        """检查当前会话文件是否已有内容"""
        return self._get_file_path(agent_name).exists()

    def new_session(self):
        """开启新的会话，生成新的 session_id"""
        self.session_id = time.strftime("%Y%m%d_%H%M%S")
    
    def save_message(
        self, 
        agent_name: str, 
        message: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        保存单条消息到 transcript 文件
        
        Args:
            agent_name: agent 名称（lead 或 teammate 名称）
            message: 消息字典，包含 role, content 等
            metadata: 可选的额外元数据
        """
        record = {
            "timestamp": time.time(),
            "role": message.get("role"),
            "content": message.get("content"),
        }
        
        # 保存 tool_calls（如果有）
        if "tool_calls" in message:
            record["tool_calls"] = message["tool_calls"]
        
        # 保存 tool_call_id（如果有）
        if "tool_call_id" in message:
            record["tool_call_id"] = message["tool_call_id"]
        
        # 合并额外元数据
        if metadata:
            record["metadata"] = metadata
        
        file_path = self._get_file_path(agent_name)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def save_messages(
        self, 
        agent_name: str, 
        messages: List[Dict[str, Any]]
    ) -> None:
        """批量保存消息列表"""
        for msg in messages:
            self.save_message(agent_name, msg)
    
    def _load_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """从指定文件加载消息列表"""
        if not file_path.exists():
            return []

        messages = []
        for line in file_path.read_text(encoding="utf-8").strip().splitlines():
            if line:
                record = json.loads(line)
                msg = {"role": record["role"]}

                if "content" in record:
                    msg["content"] = record["content"]
                if "tool_calls" in record:
                    msg["tool_calls"] = record["tool_calls"]
                if "tool_call_id" in record:
                    msg["tool_call_id"] = record["tool_call_id"]

                messages.append(msg)

        return messages

    def load_messages(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        加载指定 agent 本次会话的历史消息
        """
        return self._load_from_file(self._get_file_path(agent_name))

    def load_messages_by_file(self, file_stem: str) -> List[Dict[str, Any]]:
        """
        根据文件名（不含扩展名）加载历史消息，用于恢复对话
        """
        return self._load_from_file(self.dir / f"{file_stem}.jsonl")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有可用的会话，按时间倒序"""
        # 文件名格式: 20260411_143052_lead.jsonl 或旧格式 lead.jsonl
        sessions = {}
        for file in self.dir.glob("*.jsonl"):
            stem = file.stem
            # 尝试解析新格式: sessionid_agentname
            parts = stem.split("_", 2)
            if len(parts) >= 3 and parts[0].isdigit() and len(parts[0]) == 8:
                session_id = f"{parts[0]}_{parts[1]}"
                agent_name = "_".join(parts[2:])
            else:
                # 旧格式: agentname
                session_id = "legacy"
                agent_name = stem

            if session_id not in sessions:
                sessions[session_id] = {"files": [], "agents": []}
            sessions[session_id]["files"].append(stem)
            sessions[session_id]["agents"].append(agent_name)

        # 排序：按 session_id 倒序
        result = []
        for sid in sorted(sessions.keys(), reverse=True):
            info = sessions[sid]
            # 统计总消息数
            total_msgs = 0
            for file_stem in info["files"]:
                file_path = self.dir / f"{file_stem}.jsonl"
                lines = file_path.read_text(encoding="utf-8").strip().splitlines()
                total_msgs += len(lines)
            result.append({
                "session_id": sid,
                "files": info["files"],
                "agents": info["agents"],
                "message_count": total_msgs,
            })

        return result
    
    def clear_transcript(self, agent_name: str) -> bool:
        """清空指定 agent 的历史记录"""
        file_path = self._get_file_path(agent_name)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def get_transcript_info(self, agent_name: str) -> Dict[str, Any]:
        """获取 transcript 文件的基本信息"""
        file_path = self._get_file_path(agent_name)
        if not file_path.exists():
            return {"exists": False}
        
        lines = file_path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return {"exists": False}
        
        first_record = json.loads(lines[0])
        last_record = json.loads(lines[-1])
        
        return {
            "exists": True,
            "message_count": len(lines),
            "first_timestamp": first_record.get("timestamp"),
            "last_timestamp": last_record.get("timestamp"),
            "file_size": file_path.stat().st_size,
        }


# 全局单例
transcript_manager = TranscriptManager()