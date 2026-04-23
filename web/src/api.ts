const BASE = "/api";

export async function createSession(): Promise<string> {
  const res = await fetch(`${BASE}/sessions`, { method: "POST" });
  const data = await res.json();
  return data.session_id;
}

export async function sendMessage(sessionId: string, message: string): Promise<string> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "发送消息失败");
  }
  const data = await res.json();
  return data.run_id;
}

export function createEventSource(runId: string): EventSource {
  return new EventSource(`${BASE}/chat/stream/${runId}`);
}

export async function getHistory(sessionId: string): Promise<{ role: string; content: string }[]> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/history`);
  return res.json().then((d) => d.messages);
}

export async function clearSession(sessionId: string): Promise<void> {
  await fetch(`${BASE}/sessions/${sessionId}/clear`, { method: "POST" });
}

export interface TranscriptSession {
  session_id: string;
  title: string;
  message_count: number;
  files: string[];
}

export async function listTranscripts(): Promise<TranscriptSession[]> {
  const res = await fetch(`${BASE}/transcripts`);
  const data = await res.json();
  return data.sessions;
}

export async function restoreTranscript(sessionId: string, transcriptId: string): Promise<void> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/restore/${transcriptId}`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "恢复失败");
  }
}

export async function deleteTranscript(transcriptId: string): Promise<void> {
  const res = await fetch(`${BASE}/transcripts/${transcriptId}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "删除失败");
  }
}

export async function newSession(): Promise<string> {
  const res = await fetch(`${BASE}/sessions`, { method: "POST" });
  const data = await res.json();
  return data.session_id;
}

export async function interruptRun(runId: string): Promise<void> {
  const res = await fetch(`${BASE}/runs/${runId}/interrupt`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "中断失败");
  }
}