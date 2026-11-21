import { useEffect, useState } from 'react'
import type { AuditEntry } from '../types'
import { Icon } from './Icon'

/** Every firewall decision from logs/audit.jsonl, newest first; blocked rows in red. */
export function AuditLog() {
  const [log, setLog] = useState<AuditEntry[] | null>(null)

  function load() {
    fetch('/api/audit')
      .then((r) => r.json())
      .then((entries: AuditEntry[]) => setLog([...entries].reverse()))
      .catch(() => setLog(null))
  }
  useEffect(load, [])

  if (log === null) return <p className="muted">Can't reach the API server.</p>
  return (
    <div>
      <button onClick={load}><Icon name="reset" /> Refresh</button>
      {log.length === 0 ? (
        <p className="muted">No decisions yet.</p>
      ) : (
        <table className="table">
          <thead>
            <tr><th>Time</th><th>Tool</th><th>Verdict</th><th>Rule</th><th>Reason</th></tr>
          </thead>
          <tbody>
            {log.map((e, i) => (
              <tr key={i} className={e.decision.verdict === 'block' ? 'row-block' : ''}>
                <td>{new Date(e.ts).toLocaleTimeString()}</td>
                <td>{e.call.tool}</td>
                <td>{e.decision.verdict}</td>
                <td>{e.decision.rule ?? ''}</td>
                <td>{e.decision.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
