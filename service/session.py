import threading
import uuid

from agents.utils.Permission import PermissionManager
from agents.output_handler import ServiceOutputHandler


class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = [{"role": "system", "content": ""}]
        self.permission = PermissionManager(
            ask_user_callback=lambda *_: True,
        )
        self.output_handler = ServiceOutputHandler()
        self.active_run_id: str | None = None
        self.lock = threading.Lock()


class RunState:
    def __init__(self, run_id: str, session: Session):
        self.run_id = run_id
        self.status = "running"  # running | completed | error | interrupted
        self.event_index = len(session.output_handler.events)
        self.session = session
        self.result: str | None = None
        self.error: str | None = None
        self.stop_event = threading.Event()


class SessionManager:
    def __init__(self):
        self.sessions: dict[str, Session] = {}
        self.runs: dict[str, RunState] = {}
        self._lock = threading.Lock()

    def create_session(self) -> Session:
        session_id = uuid.uuid4().hex[:8]
        session = Session(session_id)
        with self._lock:
            self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    def create_run(self, session: Session) -> RunState:
        run_id = uuid.uuid4().hex[:8]
        run = RunState(run_id, session)
        with self._lock:
            self.runs[run_id] = run
        session.active_run_id = run_id
        return run

    def get_run(self, run_id: str) -> RunState | None:
        return self.runs.get(run_id)


session_manager = SessionManager()
