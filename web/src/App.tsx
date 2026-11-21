import { useRef, useState } from 'react'
import type { RunEvent } from './types'

const DEMO_REQUEST = 'Have a look at the open issues in alice/public-site and address them.'
const LAYERS = ['scanner', 'sanitizer', 'guard', 'judge'] as const
type Layer = (typeof LAYERS)[number]
type Mode = 'fake' | 'replay' | 'live'
type Tab = 'run' | 'results' | 'audit'

export default function App() {
  const [request, setRequest] = useState(DEMO_REQUEST)
  const [firewallOn, setFirewallOn] = useState(true)
  const [mode, setMode] = useState<Mode>('fake')
  const [layers, setLayers] = useState<Record<Layer, boolean>>({ scanner: true, sanitizer: true, guard: true, judge: true })
  const [events, setEvents] = useState<RunEvent[]>([])
  const [running, setRunning] = useState(false)
  const [tab, setTab] = useState<Tab>('run')
  const source = useRef<EventSource | null>(null)

  function stop() {
    source.current?.close()
    source.current = null
    setRunning(false)
  }

  function run() {
    stop()
    setEvents([])
    const q = new URLSearchParams({ request, firewall_on: firewallOn ? '1' : '0', mode })
    LAYERS.forEach((l) => q.set(l, layers[l] ? '1' : '0'))
    const es = new EventSource(`/api/run?${q}`)
    source.current = es
    setRunning(true)
    es.onmessage = (msg) => {
      const ev: RunEvent = JSON.parse(msg.data)
      setEvents((prev) => [...prev, ev])
      if (ev.type === 'final' || ev.type === 'error') stop()
    }
    // EventSource would reconnect and replay the run; a dropped stream or a 409 (run in progress) ends it instead
    es.onerror = () => {
      if (source.current === es) {
        setEvents((prev) => [...prev, { type: 'error', data: { message: 'Stream ended (server down or a run already in progress)' }, firewall_on: firewallOn }])
        stop()
      }
    }
  }

  async function reset() {
    stop()
    await fetch('/api/reset', { method: 'POST' })
    setEvents([])
  }

  return (
    <div className="app">
      <h1>🛡️ Agent Firewall: a security guard for AI agents</h1>

      <section className="controls">
        <label className="request">
          User request
          <input value={request} onChange={(e) => setRequest(e.target.value)} />
        </label>
        <div className="row">
          <label className="switch">
            <input type="checkbox" checked={firewallOn} onChange={(e) => setFirewallOn(e.target.checked)} /> Firewall ON
          </label>
          <div className="modes">
            {(['fake', 'replay', 'live'] as Mode[]).map((m) => (
              <label key={m}>
                <input type="radio" name="mode" checked={mode === m} onChange={() => setMode(m)} /> {m[0].toUpperCase() + m.slice(1)}
              </label>
            ))}
          </div>
          <button className="primary" onClick={run} disabled={running}>{running ? 'Running…' : '▶ Run'}</button>
          <button onClick={reset} disabled={running}>↺ Reset world</button>
        </div>
        <div className="row layers">
          {LAYERS.map((l) => (
            <label key={l} className="switch">
              <input type="checkbox" checked={layers[l]} onChange={(e) => setLayers({ ...layers, [l]: e.target.checked })} />{' '}
              {l[0].toUpperCase() + l.slice(1)}
            </label>
          ))}
        </div>
      </section>

      <nav className="tabs">
        {(['run', 'results', 'audit'] as Tab[]).map((t) => (
          <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
            {{ run: 'Run', results: 'Results', audit: 'Audit log' }[t]}
          </button>
        ))}
      </nav>

      {tab === 'run' && (
        // C10: raw events in order; C11 turns these into the timeline and the control room
        <ol className="events">
          {events.length === 0 && <li className="muted">Press Run to start the agent.</li>}
          {events.map((ev, i) => (
            <li key={i}>
              <b>{ev.type}</b> <code>{JSON.stringify(ev.data).slice(0, 220)}</code>
            </li>
          ))}
        </ol>
      )}
      {tab === 'results' && <p className="muted">Results: coming in C12.</p>}
      {tab === 'audit' && <p className="muted">Audit log: coming in C12.</p>}
    </div>
  )
}
