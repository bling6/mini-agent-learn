import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import type { AgentEvent, ChatMessage } from "./types";
import {
  createSession,
  newSession,
  sendMessage,
  createEventSource,
  getHistory,
  listTranscripts,
  restoreTranscript,
  deleteTranscript,
  interruptRun,
} from "./api";
import type { TranscriptSession } from "./api";
import "./App.css";

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [transcripts, setTranscripts] = useState<TranscriptSession[]>([]);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize session
  useEffect(() => {
    createSession().then((id) => setSessionId(id));
  }, []);

  // Load history when session is ready
  useEffect(() => {
    if (sessionId) {
      getHistory(sessionId).then((msgs) =>
        setMessages(
          msgs.map((m, i) => ({
            id: `hist-${i}`,
            role: m.role as "user" | "assistant",
            content: m.content,
            events: [],
          }))
        )
      );
    }
  }, [sessionId]);

  // Load transcripts list
  useEffect(() => {
    listTranscripts().then(setTranscripts);
  }, []);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, events]);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleSend = async () => {
    if (!sessionId || !input.trim() || isRunning) return;

    const userMsg = input.trim();
    setInput("");

    setMessages((prev) => [
      ...prev,
      { id: `user-${Date.now()}`, role: "user", content: userMsg, events: [] },
    ]);

    setEvents([]);
    setIsRunning(true);

    const rid = await sendMessage(sessionId, userMsg);
    setCurrentRunId(rid);

    // Connect SSE
    const es = createEventSource(rid);
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      const parsed = JSON.parse(e.data);
      const eventType = parsed.type;
      const eventData = parsed.data;

      if (eventType === "done") {
        // Run completed
        setIsRunning(false);
        setCurrentRunId(null);
        es.close();
        eventSourceRef.current = null;
        // Reload history to get final assistant message
        if (sessionId) {
          getHistory(sessionId).then((msgs) =>
            setMessages(
              msgs.map((m, i) => ({
                id: `hist-${i}`,
                role: m.role as "user" | "assistant",
                content: m.content,
                events: [],
              }))
            )
          );
        }
        return;
      }

      setEvents((prev) => [...prev, { type: eventType, data: eventData }]);
    };

    es.onerror = () => {
      setIsRunning(false);
      setCurrentRunId(null);
      es.close();
      eventSourceRef.current = null;
      if (sessionId) {
        getHistory(sessionId).then((msgs) =>
          setMessages(
            msgs.map((m, i) => ({
              id: `hist-${i}`,
              role: m.role as "user" | "assistant",
              content: m.content,
              events: [],
            }))
          )
        );
      }
    };
  };

  const handleNewChat = async () => {
    if (isRunning) return;
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    const newId = await newSession();
    setSessionId(newId);
    setMessages([]);
    setEvents([]);
    setIsRunning(false);
    setCurrentRunId(null);
    listTranscripts().then(setTranscripts);
  };

  const handleRestore = async (transcriptId: string) => {
    if (!sessionId || isRunning) return;
    try {
      await restoreTranscript(sessionId, transcriptId);
      const msgs = await getHistory(sessionId);
      setMessages(
        msgs.map((m, i) => ({
          id: `hist-${i}`,
          role: m.role as "user" | "assistant",
          content: m.content,
          events: [],
        }))
      );
      // setSidebarOpen(false);
      listTranscripts().then(setTranscripts);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleDeleteTranscript = async (transcriptId: string) => {
    try {
      await deleteTranscript(transcriptId);
      setTranscripts((prev) => prev.filter((t) => t.session_id !== transcriptId));
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleInterrupt = async () => {
    if (!currentRunId) return;
    try {
      await interruptRun(currentRunId);
    } catch {
      // run may not exist anymore (server restart or already completed), treat as already stopped
      setIsRunning(false);
      setCurrentRunId(null);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const displayItems: Array<
    | { type: "user"; content: string }
    | { type: "assistant"; content: string }
    | { type: "events"; events: AgentEvent[] }
  > = [];

  for (const msg of messages) {
    displayItems.push({ type: msg.role, content: msg.content });
  }

  if (isRunning && events.length > 0) {
    displayItems.push({ type: "events", events });
  }

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? "" : "collapsed"}`}>
        <div className="sidebar-header">
          <span className="sidebar-title">历史对话</span>
          <button className="sidebar-close" onClick={() => setSidebarOpen(false)}>✕</button>
        </div>
        <button className="sidebar-new-btn" onClick={handleNewChat}>+ 新对话</button>
        <div className="sidebar-list">
          {transcripts.length === 0 && (
            <div className="sidebar-empty">暂无历史记录</div>
          )}
          {transcripts.map((t) => (
            <div key={t.session_id} className="sidebar-item">
              <div className="sidebar-item-main" onClick={() => handleRestore(t.session_id)}>
                <div className="sidebar-item-title">{t.title}</div>
                <div className="sidebar-item-meta">
                  {t.session_id} · {t.message_count} 条消息
                </div>
              </div>
              <button
                className="sidebar-item-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteTranscript(t.session_id);
                }}
                title="删除"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main chat area */}
      <div className="app">
        <div className="header">
          <button className="btn btn-icon" onClick={() => setSidebarOpen(!sidebarOpen)} title={sidebarOpen ? "收起侧栏" : "展开侧栏"}>
            ☰
          </button>
          <div className="header-title">AI 编程助手</div>
          <div className="header-actions" />
        </div>

        <div className="messages">
          {displayItems.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">🤖</div>
              <div className="empty-state-text">输入问题开始对话</div>
            </div>
          )}

          {displayItems.map((item, i) => {
            if (item.type === "user") {
              return (
                <div key={i} className="message message-user">
                  <div className="bubble">{item.content}</div>
                </div>
              );
            }

            if (item.type === "assistant") {
              return (
                <div key={i} className="message message-assistant">
                  <div className="bubble">
                    <div className="markdown-body">
                      <ReactMarkdown>{item.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              );
            }

            if (item.type === "events") {
              return (
                <div key={i} className="message message-assistant">
                  <div className="bubble">
                    <EventStream events={(item as { type: "events"; events: AgentEvent[] }).events} />
                  </div>
                </div>
              );
            }

            return null;
          })}

          {isRunning && events.length === 0 && (
            <div className="message message-assistant">
              <div className="bubble">
                <div className="event-thinking">
                  思考中<span className="dot">...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isRunning ? "等待回复中..." : "输入消息，Enter 发送"}
            disabled={isRunning}
            rows={1}
          />
          {isRunning ? (
            <button className="btn btn-stop" onClick={handleInterrupt}>
              停止
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={handleSend}
              disabled={!input.trim()}
            >
              发送
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function EventStream({ events }: { events: AgentEvent[] }) {
  const items: Array<
    | { kind: "thinking" }
    | { kind: "reasoning"; content: string }
    | { kind: "tool"; call: AgentEvent; result?: AgentEvent }
    | { kind: "permission_denied"; data: AgentEvent }
    | { kind: "interrupted" }
    | { kind: "error"; data: AgentEvent }
    | { kind: "response"; content: string }
  > = [];

  const toolCallMap = new Map<number, AgentEvent>();

  for (let i = 0; i < events.length; i++) {
    const ev = events[i];
    if (ev.type === "thinking") {
      items.push({ kind: "thinking" });
    } else if (ev.type === "reasoning") {
      items.push({ kind: "reasoning", content: ev.data.content || "" });
    } else if (ev.type === "tool_call") {
      toolCallMap.set(i, ev);
    } else if (ev.type === "tool_result") {
      const callIndex = [...toolCallMap.keys()].find(
        (j) => toolCallMap.get(j)?.data.tool_name === ev.data.tool_name
      );
      if (callIndex !== undefined) {
        const call = toolCallMap.get(callIndex)!;
        items.push({ kind: "tool", call, result: ev });
        toolCallMap.delete(callIndex);
      } else {
        items.push({ kind: "tool", call: ev, result: undefined });
      }
    } else if (ev.type === "interrupted") {
      items.push({ kind: "interrupted" });
    } else if (ev.type === "permission_denied") {
      items.push({ kind: "permission_denied", data: ev });
    } else if (ev.type === "error") {
      items.push({ kind: "error", data: ev });
    } else if (ev.type === "response") {
      items.push({ kind: "response", content: ev.data.content || "" });
    }
  }

  for (const [, call] of toolCallMap) {
    items.push({ kind: "tool", call, result: undefined });
  }

  return (
    <div>
      {items.map((item, i) => {
        if (item.kind === "thinking") {
          return (
            <div key={i} className="event-thinking">
              思考中<span className="dot">...</span>
            </div>
          );
        }

        if (item.kind === "reasoning") {
          return (
            <div key={i} className="event-reasoning">{item.content}</div>
          );
        }

        if (item.kind === "tool") {
          return <ToolCallCard key={i} call={item.call} result={item.result} />;
        }

        if (item.kind === "interrupted") {
          return (
            <div key={i} className="event-interrupted">
              对话已中断
            </div>
          );
        }

        if (item.kind === "permission_denied") {
          return (
            <div key={i} className="event-permission-denied">
              ⛔ 权限拒绝: {item.data.data.tool_name} — {item.data.data.reason}
            </div>
          );
        }

        if (item.kind === "error") {
          return (
            <div key={i} className="event-error">
              ❌ 错误: {item.data.data.message}
            </div>
          );
        }

        if (item.kind === "response") {
          return (
            <div key={i} className="markdown-body">
              <ReactMarkdown>{item.content}</ReactMarkdown>
            </div>
          );
        }

        return null;
      })}
    </div>
  );
}

function ToolCallCard({ call, result }: { call: AgentEvent; result?: AgentEvent }) {
  const [expanded, setExpanded] = useState(false);
  const toolName = call.data.tool_name || "unknown";
  const args = call.data.args || {};

  return (
    <div className={`event-tool-call tool-card ${expanded ? "expanded" : ""}`}>
      <div className="tool-header" onClick={() => setExpanded(!expanded)}>
        <span>
          <span className="tool-icon">🔧</span>
          <span className="tool-name">{toolName}</span>
        </span>
        <span className="tool-toggle">{expanded ? "收起" : "展开"}</span>
      </div>
      {expanded && (
        <div className="tool-body">
          <div className="tool-args">
            <pre>{JSON.stringify(args, null, 2)}</pre>
          </div>
          {result && (
            <div className={`tool-result ${result.data.truncated ? "" : "success"}`}>
              {result.data.result?.slice(0, 500)}
              {result.data.truncated && "..."}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;