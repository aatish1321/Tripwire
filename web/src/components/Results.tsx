import { useState } from 'react'
import type { ScoreRow, Scoreboard } from '../types'
import { Icon, type IconName } from './Icon'

const OUTCOME: Record<ScoreRow['outcome'], { icon: IconName; word: string }> = {
  succeeded: { icon: 'alert', word: 'succeeded' },
  blocked: { icon: 'block', word: 'blocked' },
  failed: { icon: 'x', word: 'failed' },
  passed: { icon: 'check', word: 'passed' },
}
const Outcome = ({ kind }: { kind: ScoreRow['outcome'] }) => (
  <span className={`out ${kind}`}><Icon name={OUTCOME[kind].icon} /> {OUTCOME[kind].word}</span>
)

const AGENT_KEYS = ['scanner', 'sanitizer', 'guard', 'judge']
// which agents were off for the "on" runs, as the server reports it
const layerNote = (layers: Record<string, boolean>) => {
  const off = AGENT_KEYS.filter((k) => layers[k] === false)
  return off.length ? ` (${off.join(', ')} off)` : ''
}

/** A7/A9's scoreboard: every scripted attack and normal task, firewall off vs on. */
export function Results({ disabled, layers }: { disabled: boolean; layers: Record<string, boolean> }) {
  const [board, setBoard] = useState<Scoreboard | null>(null)
  const [error, setError] = useState('')
  const off = Object.keys(layers).filter((l) => !layers[l])

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
        <button className="primary" onClick={load} disabled={disabled}><Icon name="play" /> Run scoreboard</button>
        {/* the agent switches above apply to the "on" runs, e.g. untick Scanner to show what only it catches */}
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
                <h3>Firewall {m}{m === 'on' && board.layers ? layerNote(board.layers) : ''}</h3>
                <div className="big attacks">{board[m].attacks_succeeded} / {board[m].attacks_total}</div>
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
                  <td><Outcome kind={r.outcome} /></td>
                  <td>{on[r.name] ? <Outcome kind={on[r.name].outcome} /> : ''}</td>
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
