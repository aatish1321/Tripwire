import { useEffect, useState } from 'react'
import type { RunEvent } from './types'

/** Replays received events at a pace the audience can follow: one agent step at a time, then the next event.
 *  Scripted runs arrive in milliseconds, so without this the whole story would appear at once. */
export function usePlayback(received: RunEvent[], stepMs = 250, eventMs = 550) {
  const [cur, setCur] = useState({ i: 0, s: 0 }) // i events fully shown, s agent steps of event i shown
  const empty = received.length === 0

  useEffect(() => {
    if (empty) setCur({ i: 0, s: 0 })
  }, [empty])

  useEffect(() => {
    if (cur.i >= received.length) return
    const n = received[cur.i].data.agents?.length ?? 0
    const t = setTimeout(
      () => setCur((c) => (c.s < n ? { i: c.i, s: c.s + 1 } : { i: c.i + 1, s: 0 })),
      cur.s < n ? stepMs : eventMs,
    )
    return () => clearTimeout(t)
  }, [cur, received, stepMs, eventMs])

  const visible = received.slice(0, cur.i)
  const partial = received[cur.i]
  let active: string | null = null
  if (partial && cur.s > 0) {
    const agents = partial.data.agents ?? []
    visible.push({ ...partial, data: { ...partial.data, agents: agents.slice(0, cur.s) } })
    active = agents[cur.s - 1]?.agent ?? null
  }
  return { visible, active, done: cur.i >= received.length }
}
