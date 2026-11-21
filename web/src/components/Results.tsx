import { useState } from 'react'
import type { ScoreRow, Scoreboard } from '../types'

const OUTCOME: Record<ScoreRow['outcome'], string> = {
  succeeded: '🚨 succeeded',
  blocked: '⛔ blocked',
  failed: '✗ failed',
  passed: '✅ passed',
}

const AGENT_KEYS = ['scanner', 'sanitizer', 'guard', 'judge']
// which agents were off for the "on" runs, as the server reports it
const layerNote = (layers: Record<string, boolean>) => {
  const off = AGENT_KEYS.filter((k) => layers[k] === false)
  return off.length ? ` (${off.join(', ')} off)` : ''
}

/** A7/A9's scoreboard: every scripted attack and normal task, firewall off vs on. */
export function Results({ disabled }: { disabled: boolean }) {
  const [board, setBoard] = useState<Scoreboard | null>(null)
  const [error, setError] = useState('')
  // only here, not on the main screen: untick an agent to show what only it catches (e.g. Scanner off: 1/9 gets through)
  const [layers, setLayers] = useState<Record<string, boolean>>(Object.fromEntries(AGENT_KEYS.map((k) => [k, true])))
  const off = AGENT_KEYS.filter((l) => !layers[l])

  async function load() {
    setError('')
    const q = new URLSearchParams(Object.entries(layers).map(([k, v]) => [k, v ? '1' : '0']))
    const r = await fetch(`/api/scoreboard?${q}`).catch(() => null)
    if (!r?.ok) return setError(r?.status === 409 ? 'A run is in progress, try again when it ends.' : "Can't reach the API server.")
    setBoard(await r.json())
  }

  const on = Object.fromEntries((board?.rows ?? []).filter((r) => r.firewall_on).map((r) => [r.name, r]))
  return (
    <div className="results">
      {/* the scoreboard rewrites the shared world file, so never while a demo run is going */}
      <div className="row">
        <button className="primary" onClick={load} disabled={disabled}>▶ Run scoreboard</button>
        {AGENT_KEYS.map((l) => (
          <label key={l} className="switch">
            <input type="checkbox" checked={layers[l]} onChange={(e) => setLayers({ ...layers, [l]: e.target.checked })} />{' '}
            {l[0].toUpperCase() + l.slice(1)}
          </label>
        ))}
        <span className={off.length ? 'warn' : 'muted'}>
          {off.length ? `With ${off.map((l) => l[0].toUpperCase() + l.slice(1)).join(', ')} switched off` : 'All agents on'}
        </span>
      </div>
      {error && <p className="error">{error}</p>}
      {!board && !error && <p className="muted">Replays every scripted attack and normal task with the firewall off and on.</p>}
      {board && (
        <>
          <div className="score-cols">
            {(['off', 'on'] as const).map((m) => (
              <div key={m} className={`score s-${m === 'off' ? 'block' : 'ok'}`}>
                <h3>Firewall {m.toUpperCase()}{m === 'on' && board.layers ? layerNote(board.layers) : ''}</h3>
                <div className="big">{board[m].attacks_succeeded} / {board[m].attacks_total}</div>
                <div className="muted">attacks that succeeded</div>
                <div className="big">{board[m].normal_passed} / {board[m].normal_total}</div>
                <div className="muted">normal tasks that passed</div>
              </div>
            ))}
          </div>
          <table className="table">
            <thead>
              <tr><th>Scenario</th><th>Kind</th><th>Firewall off</th><th>Firewall on</th><th>Blocked by</th></tr>
            </thead>
            <tbody>
              {board.rows.filter((r) => !r.firewall_on).map((r) => (
                <tr key={r.name}>
                  <td>{r.name}</td>
                  <td>{r.kind}</td>
                  <td>{OUTCOME[r.outcome]}</td>
                  <td>{on[r.name] ? OUTCOME[on[r.name].outcome] : ''}</td>
                  <td>{on[r.name]?.blocked_rule ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">Scripted tool calls; the tools and the firewall rules run for real (LLM policy agent off).</p>
        </>
      )}
    </div>
  )
}
