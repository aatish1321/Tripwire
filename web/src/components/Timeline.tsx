import { useEffect, useRef } from 'react'
import type { AgentStep, Decision, Evidence, RunEvent, ToolCall, ToolResult } from '../types'
import { short } from '../text'
import { AGENTS, cap, STATUS_WORD, worst } from './agents'
import { Icon } from './Icon'
import { RawVsClean } from './RawVsClean'

type Card = { call: ToolCall; decision?: Decision; result?: ToolResult; firewallOn: boolean }
type Item = { kind: 'call'; card: Card } | { kind: RunEvent['type']; data: Record<string, any> }

/** Flat event stream -> timeline items; decisions and results attach to their tool call. */
function group(events: RunEvent[]): Item[] {
  const items: Item[] = []
  const cards: Record<string, Card> = {}
  for (const ev of events) {
    if (ev.type === 'tool_call') {
      const card = { call: ev.data as ToolCall, firewallOn: ev.firewall_on }
      cards[ev.data.id] = card
      items.push({ kind: 'call', card })
    } else if (ev.type === 'decision' && cards[ev.data.call_id]) cards[ev.data.call_id].decision = ev.data as Decision
    else if (ev.type === 'tool_result' && cards[ev.data.call_id]) cards[ev.data.call_id].result = ev.data as ToolResult
    else items.push({ kind: ev.type, data: ev.data })
  }
  return items
}

/** The wire: the five agents on one line. After the agent that blocked, it turns dashed red and the rest are dimmed. */
function Chain({ steps }: { steps: AgentStep[] }) {
  const statuses: string[] = AGENTS.map((a) => worst(steps.filter((s) => s.agent === a)) ?? 'none')
  const trip = statuses.indexOf('block')
  return (
    <ol className="wire" aria-label="Agents that checked this step">
      {AGENTS.map((a, i) => (
        <li key={a} className={`s-${statuses[i]}${i === trip ? ' trip' : ''}${trip >= 0 && i > trip ? ' past' : ''}${trip >= 0 && i > trip && statuses[i] !== 'block' ? ' dead' : ''}`}>
          <span className="dot" />
          <span className="name">{cap(a)}</span>
          <span className="state">{STATUS_WORD[statuses[i]]}</span>
        </li>
      ))}
    </ol>
  )
}

function CallCard({ card }: { card: Card }) {
  const { call, decision, result } = card
  const steps = [...(decision?.agents ?? []), ...(result?.agents ?? [])]
  const evidence: Evidence[] = (result?.agents ?? []).flatMap((s) => s.evidence)
  const blockEvidence = (decision?.agents ?? []).filter((s) => s.status === 'block').flatMap((s) => s.evidence)
  const techniques = [...new Set(blockEvidence.map((e) => e.technique.replace(/_/g, ' ')))]
  return (
    <div className="card">
      <div className="tool">Step {call.step} · {call.tool}</div>
      <div className="args">{Object.entries(call.args).map(([k, v]) => `${k}=${short(v, 60)}`).join(', ')}</div>
      {steps.length > 0 && <Chain steps={steps} />}
      {decision?.verdict === 'block' ? (
        <div className="blocked">
          <div className="blocked-title"><Icon name="block" /> Blocked{decision.rule ? ` · ${decision.rule}` : ''}</div>
          <div className="reason">{decision.reason}</div>
          {techniques.length > 0 && <div className="techniques">Evidence found: {techniques.join(' · ')}</div>}
        </div>
      ) : decision ? (
        <span className="verdict allow"><Icon name="check" /> Allowed</span>
      ) : !card.firewallOn ? (
        <span className="verdict none"><Icon name="off" /> No firewall: ran unchecked</span>
      ) : null}
      {result && <div className="result">→ {short(result.output, 170)}</div>}
      {result && evidence.length > 0 && <RawVsClean raw={result.output} clean={result.clean_output} evidence={evidence} />}
    </div>
  )
}

export function Timeline({ events, follow }: { events: RunEvent[]; follow: boolean }) {
  const end = useRef<HTMLDivElement>(null)
  // the activity column scrolls on its own: keep the newest step in view while the run plays
  useEffect(() => {
    if (follow) end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [events.length, follow])

  if (events.length === 0) return <p className="muted">Press Run to start the agent.</p>
  return (
    <div className="timeline">
      {group(events).map((item, i) => {
        if (item.kind === 'call') return <CallCard key={i} card={item.card} />
        const d = item.data
        switch (item.kind) {
          case 'user':
            return (
              <div key={i} className="user">
                <Icon name="user" />
                <div>{d.text} {d.scripted && <span className="muted">(scripted replay)</span>}</div>
              </div>
            )
          case 'agent_text':
            return <div key={i} className="final"><Icon name="bot" /><div>{d.text}</div></div>
          case 'leak':
            return (
              <div key={i} className="leak">
                <Icon name="alert" />
                {d.kind === 'private_read' ? `Agent read private repo ${d.repo} after a stranger's instructions` : `Private data leaked into public repo ${d.repo}`}
              </div>
            )
          case 'final':
            return <div key={i} className="final"><Icon name="bot" /><div>{d.text}</div></div>
          case 'error':
            return <div key={i} className="error"><Icon name="alert" /><div>Error: {d.message ?? JSON.stringify(d)}</div></div>
          default:
            return null
        }
      })}
      <div ref={end} />
    </div>
  )
}
