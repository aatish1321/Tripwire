import type { ReactNode } from 'react'
import type { Evidence } from './types'

/** Readable text for a tool output, without JSON escaping, so evidence strings still match exactly. */
export function toText(value: unknown, indent = ''): string {
  if (Array.isArray(value)) return value.map((v) => toText(v, indent)).join('\n')
  if (value && typeof value === 'object') {
    return Object.entries(value)
      .map(([k, v]) => (v && typeof v === 'object' ? `${indent}${k}:\n${toText(v, indent + '  ')}` : `${indent}${k}: ${v}`))
      .join('\n')
  }
  return `${indent}${value}`
}

export function short(value: unknown, limit: number): string {
  const t = (typeof value === 'string' ? value : JSON.stringify(value)).replace(/\s+/g, ' ')
  return t.length <= limit ? t : t.slice(0, limit - 1) + '…'
}

/** Text with every evidence string marked in red; invisible text shows its decoded version instead of nothing. */
export function highlight(text: string, evidence: Evidence[]): ReactNode[] {
  const out: ReactNode[] = []
  let rest = text
  let key = 0
  while (rest) {
    // the earliest evidence match in what's left (longest first on a tie)
    let best: { at: number; ev: Evidence } | null = null
    for (const ev of evidence) {
      const at = ev.text ? rest.indexOf(ev.text) : -1
      if (at >= 0 && (!best || at < best.at || (at === best.at && ev.text.length > best.ev.text.length))) best = { at, ev }
    }
    if (!best) {
      out.push(rest)
      break
    }
    if (best.at) out.push(rest.slice(0, best.at))
    out.push(
      <mark key={key++} title={best.ev.technique.replace(/_/g, ' ')}>
        {best.ev.decoded ? `⟦hidden: ${best.ev.decoded}⟧` : best.ev.text}
      </mark>,
    )
    rest = rest.slice(best.at + best.ev.text.length)
  }
  return out
}
