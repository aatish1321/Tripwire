import { useState } from 'react'
import type { RunEvent } from '../types'
import { AGENTS, cap, ICON, sortBySeverity, STATUS_WORD, stepsByAgent, worst } from './agents'
import { Icon } from './Icon'

// The map, sized for the right-hand column. Positions are percentages of the map box. Two lanes leave the Manager:
// results coming back are scanned, then cleaned; actions going out are checked, then judged.
const POS: Record<string, { x: number; y: number }> = {
  manager: { x: 13, y: 50 },
  scanner: { x: 50, y: 25 },
  sanitizer: { x: 87, y: 25 },
  guard: { x: 50, y: 75 },
  judge: { x: 87, y: 75 },
}
// The wires: a trunk out of the Manager, a branch into each lane, then the lane's second stage. A wire takes the colour of
// the stage it leads into; after a stage that blocked, it is dashed red (the wire is cut).
const SEGMENTS: { from: string; to: string; d: string }[] = [
  { from: 'manager', to: 'manager', d: 'M 13 50 H 31.5' },
  { from: 'manager', to: 'scanner', d: 'M 31.5 50 V 25 H 50' },
  { from: 'scanner', to: 'sanitizer', d: 'M 50 25 H 87' },
  { from: 'manager', to: 'guard', d: 'M 31.5 50 V 75 H 50' },
  { from: 'guard', to: 'judge', d: 'M 50 75 H 87' },
]
const WIRE_CLASS: Record<string, string> = { ok: 'ok', flag: 'flag', block: 'block' }

/** The five agents as a map. When a step is blocked, the action lane's wire turns dashed red and the lane says "stopped". */
export function ControlRoom({ events, active }: { events: RunEvent[]; active: string | null }) {
  const [selected, setSelected] = useState<string | null>(null)
  const by = stepsByAgent(events)
  const status: Record<string, string> = Object.fromEntries(AGENTS.map((a) => [a, worst(by[a]) ?? 'idle']))
  const stopped = status.guard === 'block' || status.judge === 'block'
  const ran = status.guard === 'ok' && status.judge === 'ok'

  return (
    <div className="room">
      <div className="map-scroll">
        <div className="map">
          <svg className="map-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            {SEGMENTS.map(({ from, to, d }) => (
              <path key={from + to} d={d} className={from !== to && status[from] === 'block' ? 'trip' : (WIRE_CLASS[status[to]] ?? '')} />
            ))}
          </svg>
          <span className="lane" style={{ left: 'calc(50% - 60px)', top: 4 }}>Results: scanned, then cleaned</span>
          <span className="lane" style={{ left: 'calc(50% - 60px)', top: 108 }}>Actions: checked, then judged</span>
          {(stopped || ran) && <span className={`lane-out ${stopped ? 's-block' : 's-ok'}`} style={{ top: 108 }}>{stopped ? 'stopped' : 'runs'}</span>}

          {AGENTS.map((agent) => (
            <button
              key={agent}
              className={`node s-${status[agent]}${agent === active ? ' active' : ''}${agent === selected ? ' selected' : ''}`}
              style={{ left: `${POS[agent].x}%`, top: `${POS[agent].y}%` }}
              onClick={() => setSelected(agent === selected ? null : agent)}
            >
              <Icon name={ICON[agent]} />
              <span className="meta">
                <span className="agent-name">{cap(agent)}</span>
                <span className="agent-status">{STATUS_WORD[status[agent]]}</span>
              </span>
            </button>
          ))}
        </div>
      </div>

      {selected ? (
        <div className="agent-details">
          <h3><Icon name={ICON[selected]} /> {cap(selected)}</h3>
          {by[selected].length === 0 && <p className="muted">No steps in this run.</p>}
          {sortBySeverity(by[selected]).map((s, i) => (
            <div key={i} className={`detail s-${s.status}`}>
              <div><b className="status-text">{STATUS_WORD[s.status]}</b> · {s.call} · {s.ms} ms</div>
              <div>{s.summary}</div>
              {s.evidence.length > 0 && (
                <ul>
                  {s.evidence.map((e, j) => (
                    <li key={j}>
                      “{e.decoded ? `hidden: ${e.decoded}` : e.text}” <span className="muted">({e.technique.replace(/_/g, ' ')})</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">Click an agent to see what it found.</p>
      )}
    </div>
  )
}
