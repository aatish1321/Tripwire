import { useEffect, useState } from 'react'
import { highlight } from '../text'
import { Icon } from './Icon'

type PR = { number: number; title: string; body: string }

/** "What the public can see": open PRs on alice/public-site, with leaked private text in red. */
export function PublicView({ refresh, leaked, waiting }: { refresh: number; leaked: string[]; waiting: boolean }) {
  const [prs, setPrs] = useState<PR[] | null>(null)

  useEffect(() => {
    fetch('/api/public-view')
      .then((r) => r.json())
      .then((v) => setPrs(v.pull_requests ?? []))
      .catch(() => setPrs(null))
  }, [refresh])

  if (waiting) return <p className="muted">Waiting for the run to finish…</p>
  if (prs === null) return <p className="muted">Can't reach the API server.</p>
  const marks = leaked.map((text) => ({ field: 'body', text, technique: 'leaked private text' }))
  return (
    <div className="public">
      {leaked.length > 0 && <div className="leak"><Icon name="alert" /> Private data is now public</div>}
      {prs.length === 0 && <p className="muted">No pull requests on alice/public-site.</p>}
      {prs.map((pr) => (
        <div key={pr.number} className="card">
          <div className="tool">PR #{pr.number}: {pr.title}</div>
          <pre className="pr-body">{highlight(pr.body, marks)}</pre>
        </div>
      ))}
    </div>
  )
}
