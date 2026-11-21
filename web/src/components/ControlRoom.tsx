import { useState } from 'react'
import type { RunEvent } from '../types'
import { cap, ICON, sortBySeverity, stepsByAgent, worst } from './agents'

// Manager in the middle, the four specialists in the corners
const GRID = ['scanner', null, 'sanitizer', null, 'manager', null, 'guard', null, 'judge']

export function ControlRoom({ events, active }: { events: RunEvent[]; active: string | null }) {
  const [selected, setSelected] = useState<string | null>(null)
  const by = stepsByAgent(events)

  return (
    <div className="room">
      <div className="room-grid">
        {GRID.map((agent, i) => {
          if (!agent) return <div key={i} />
          const status = worst(by[agent]) ?? 'idle'
          return (
            <button
              key={agent}
              className={`agent-card s-${status}${agent === active ? ' active' : ''}${agent === selected ? ' selected' : ''}`}
              onClick={() => setSelected(agent === selected ? null : agent)}
            >
              <span className="agent-name">{ICON[agent]} {cap(agent)}</span>
              <span className="agent-status">{status.toUpperCase()}</span>
            </button>
          )
        })}
      </div>

      {selected ? (
        <div className="agent-details">
          <h3>{ICON[selected]} {cap(selected)}</h3>
          {by[selected].length === 0 && <p className="muted">No steps in this run.</p>}
          {sortBySeverity(by[selected]).map((s, i) => (
            <div key={i} className={`detail s-${s.status}`}>
              <div><b className="status-text">{s.status.toUpperCase()}</b> · {s.call} · {s.ms} ms</div>
              <div>{s.summary}</div>
              {s.evidence.length > 0 && (
                <ul>
                  {s.evidence.map((e, j) => (
                    <li key={j}>
                      “{e.decoded ? `hidden: ${e.decoded}` : e.text}” <i className="muted">({e.technique.replace(/_/g, ' ')})</i>
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
