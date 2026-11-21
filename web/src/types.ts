// Copied from shared/contracts.py plus the phase 2 agent step shape. If a contract changes, change this file in the same commit.

export type Provenance = {
  source: 'user' | 'repo_file' | 'issue' | 'tool_meta'
  author: string | null
  trusted: boolean
  repo: string | null
  visibility: 'public' | 'private' | null
}

export type ToolCall = { id: string; tool: string; args: Record<string, unknown>; step: number }

export type Evidence = { field: string; text: string; technique: string; decoded?: string }

export type AgentStep = {
  agent: 'manager' | 'scanner' | 'sanitizer' | 'guard' | 'judge'
  status: 'ok' | 'flag' | 'block' | 'skip'
  summary: string
  evidence: Evidence[]
  ms: number
}

export type ToolResult = {
  call_id: string
  output: unknown
  provenance: Provenance
  clean_output?: unknown // phase 2: what the model saw
  agents?: AgentStep[] // phase 2: manager, scanner, sanitizer
}

export type Decision = {
  call_id: string
  verdict: 'allow' | 'block'
  rule: string | null
  reason: string
  checked_by: string[]
  agents?: AgentStep[] // phase 2: manager, guard, judge
}

export type RunEvent = {
  type: 'user' | 'agent_text' | 'tool_call' | 'decision' | 'tool_result' | 'leak' | 'final' | 'error'
  data: Record<string, any> // the ToolCall / Decision / ToolResult / text
  firewall_on: boolean
}

export type AuditEntry = { ts: string; session_id: string; user_request: string; call: ToolCall; decision: Decision }

export type ScoreSummary = { attacks_succeeded: number; attacks_total: number; normal_passed: number; normal_total: number }

export type ScoreRow = {
  name: string
  kind: 'attack' | 'normal'
  firewall_on: boolean
  outcome: 'succeeded' | 'blocked' | 'failed' | 'passed'
  ok: boolean
  blocked_rule: string | null
  blocked_tool: string | null
  reason: string | null
}

export type Scoreboard = { off: ScoreSummary; on: ScoreSummary; rows: ScoreRow[]; layers?: Record<string, boolean> }
