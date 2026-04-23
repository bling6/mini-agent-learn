export interface AgentEvent {
  type: "thinking" | "reasoning" | "tool_call" | "tool_result" | "response" | "error" | "permission_denied" | "interrupted";
  data: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  events: AgentEvent[];
}

export interface RunState {
  run_id: string;
  status: "running" | "completed" | "error" | "idle";
}