import json
import threading
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.agent import Agent
from agents.output_handler import AgentEvent
from agents.utils.Memory import memory_manager
from agents.utils.watch_skill import run_watch_skill, stop_watch_skill
from agents.utils.transcript import transcript_manager
from service.session import session_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    memory_manager.load_all()
    run_watch_skill()
    yield
    stop_watch_skill()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---


class CreateSessionResponse(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    run_id: str


class EventItem(BaseModel):
    type: str
    data: dict


class MessageItem(BaseModel):
    role: str
    content: str | None = None


class HistoryResponse(BaseModel):
    messages: list[MessageItem]


class TranscriptSession(BaseModel):
    session_id: str
    title: str
    message_count: int
    files: list[str]


class TranscriptListResponse(BaseModel):
    sessions: list[TranscriptSession]


# --- Endpoints ---


@app.post("/api/sessions", response_model=CreateSessionResponse)
def create_session():
    session = session_manager.create_session()
    return CreateSessionResponse(session_id=session.session_id)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session = session_manager.get_session(req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.active_run_id:
        active_run = session_manager.get_run(session.active_run_id)
        if active_run and active_run.status == "running":
            raise HTTPException(409, "Agent is already running")

    session.messages.append({"role": "user", "content": req.message})
    session.output_handler.clear()
    run = session_manager.create_run(session)

    def run_agent():
        try:
            agent = Agent(
                messages=session.messages,
                permission=session.permission,
                output_handler=session.output_handler,
                stop_event=run.stop_event,
            )
            agent.run()
            if run.stop_event.is_set():
                run.status = "interrupted"
            else:
                run.status = "completed"
        except Exception as e:
            run.status = "error"
            run.error = str(e)
            session.output_handler.error(str(e))
        finally:
            session.active_run_id = None

    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()
    return ChatResponse(run_id=run.run_id)


@app.get("/api/chat/stream/{run_id}")
async def stream_events(run_id: str):
    run = session_manager.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")

    handler = run.session.output_handler

    async def event_generator():
        sent_index = 0
        notify = handler.subscribe()
        try:
            while not handler.is_done():
                # Wait for new events using the threading.Event
                await asyncio.to_thread(handler.wait_for_event, notify, timeout=30.0)
                notify.clear()

                # Send all new events since last sent
                new_events = handler.events[sent_index:]
                for ev in new_events:
                    data = json.dumps({"type": ev.type, "data": ev.data}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    sent_index += 1

            # Send any remaining events after done
            new_events = handler.events[sent_index:]
            for ev in new_events:
                data = json.dumps({"type": ev.type, "data": ev.data}, ensure_ascii=False)
                yield f"data: {data}\n\n"
                sent_index += 1

            # Send final done signal
            yield f"data: {json.dumps({'type': 'done', 'data': {}}, ensure_ascii=False)}\n\n"
        finally:
            handler.unsubscribe(notify)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/runs/{run_id}/interrupt")
def interrupt_run(run_id: str):
    run = session_manager.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if run.status != "running":
        return {"status": run.status}
    run.stop_event.set()
    run.session.output_handler.emit(AgentEvent("interrupted", {}))
    return {"status": "interrupting"}


@app.get("/api/sessions/{session_id}/history", response_model=HistoryResponse)
def get_history(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    msgs = []
    for m in session.messages:
        if m["role"] in ("user", "assistant") and m.get("content"):
            msgs.append(MessageItem(role=m["role"], content=m["content"]))
    return HistoryResponse(messages=msgs)


@app.post("/api/sessions/{session_id}/clear")
def clear_session(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    session.messages = [{"role": "system", "content": ""}]
    session.output_handler.clear()
    # Start a fresh transcript session so future messages go to a new file
    transcript_manager.new_session()
    return {"status": "cleared"}


@app.get("/api/transcripts", response_model=TranscriptListResponse)
def list_transcripts():
    sessions = transcript_manager.list_sessions()
    result = []
    for s in sessions:
        # Find the lead file to get the first user message as title
        lead_file = None
        for f in s["files"]:
            if f.endswith("_lead") or "lead" in f:
                lead_file = f
                break
        lead_file = lead_file or s["files"][0]

        title = s["session_id"]
        file_path = transcript_manager.dir / f"{lead_file}.jsonl"
        if file_path.exists():
            for line in file_path.read_text(encoding="utf-8").strip().splitlines():
                record = json.loads(line)
                if record.get("role") == "user" and record.get("content"):
                    title = record["content"][:50]
                    break

        result.append(TranscriptSession(
            session_id=s["session_id"],
            title=title,
            message_count=s["message_count"],
            files=s["files"],
        ))
    return TranscriptListResponse(sessions=result)


@app.post("/api/sessions/{session_id}/restore/{transcript_id}")
def restore_transcript(session_id: str, transcript_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.active_run_id:
        raise HTTPException(409, "Agent is currently running")

    # Find lead file for this transcript
    sessions = transcript_manager.list_sessions()
    target = None
    for s in sessions:
        if s["session_id"] == transcript_id:
            target = s
            break
    if not target:
        raise HTTPException(404, "Transcript not found")

    lead_file = None
    for f in target["files"]:
        if f.endswith("_lead") or "lead" in f:
            lead_file = f
            break
    lead_file = lead_file or target["files"][0]

    restored = transcript_manager.load_messages_by_file(lead_file)
    if restored and restored[0]["role"] == "system":
        session.messages = restored
    else:
        session.messages = [{"role": "system", "content": ""}] + restored
    session.output_handler.clear()

    # Set transcript session_id to the restored one so future messages append to the same file
    transcript_manager.session_id = transcript_id

    return {"status": "restored", "message_count": len(session.messages)}


@app.delete("/api/transcripts/{transcript_id}")
def delete_transcript(transcript_id: str):
    sessions = transcript_manager.list_sessions()
    target = None
    for s in sessions:
        if s["session_id"] == transcript_id:
            target = s
            break
    if not target:
        raise HTTPException(404, "Transcript not found")

    for file_stem in target["files"]:
        file_path = transcript_manager.dir / f"{file_stem}.jsonl"
        if file_path.exists():
            file_path.unlink()
    return {"status": "deleted"}
