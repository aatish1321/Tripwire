import type { AgentStep, RunEvent } from '../types'
import type { IconName } from './Icon'

export const AGENTS = ['manager', 'scanner', 'sanitizer', 'guard', 'judge'] as const
export const ICON: Record<string, IconName> = { manager: 'route', scanner: 'search', sanitizer: 'filter', guard: 'shield', judge: 'scale' }
/** The word shown for a status, in plain lowercase. */
export const STATUS_WORD: Record<string, string> = { ok: 'ok', flag: 'flagged', block: 'blocked', skip: 'off', idle: 'idle', none: 'idle' }
const RANK: Record<string, number> = { skip: 1, ok: 2, flag: 3, block: 4 }

export const cap = (s: string) => s[0].toUpperCase() + s.slice(1)

/** The most serious status in a list of steps (block > flag > ok > skip), or undefined if there are none. */
export function worst(steps: AgentStep[]): AgentStep['status'] | undefined {
  return steps.reduce<AgentStep['status'] | undefined>((w, s) => ((RANK[s.status] ?? 0) > (w ? RANK[w] : 0) ? s.status : w), undefined)
}

export type TaggedStep = AgentStep & { call: string }

/** Every agent's steps in this run, each tagged with the tool call it belongs to. */
export function stepsByAgent(events: RunEvent[]): Record<string, TaggedStep[]> {
  const out: Record<string, TaggedStep[]> = Object.fromEntries(AGENTS.map((a) => [a, []]))
  const calls: Record<string, { step: number; tool: string }> = {}
  for (const ev of events) {
    if (ev.type === 'tool_call') calls[ev.data.id] = ev.data as { step: number; tool: string }
    const call = calls[ev.data.call_id]
    for (const s of (ev.data.agents ?? []) as AgentStep[]) {
      ;(out[s.agent] ??= []).push({ ...s, call: call ? `Step ${call.step} · ${call.tool}` : '' })
    }
  }
  return out
}

export function sortBySeverity<T extends AgentStep>(steps: T[]): T[] {
  return [...steps].sort((a, b) => (RANK[b.status] ?? 0) - (RANK[a.status] ?? 0))
}
