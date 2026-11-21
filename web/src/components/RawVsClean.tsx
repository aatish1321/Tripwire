import type { Evidence } from '../types'
import { highlight, toText } from '../text'

/** Raw tool output with the hidden instructions marked, next to what the AI actually saw after the Sanitizer. */
export function RawVsClean({ raw, clean, evidence }: { raw: unknown; clean: unknown; evidence: Evidence[] }) {
  const count = new Set(evidence.map((e) => e.text)).size
  const wrapper = clean && typeof clean === 'object' && 'untrusted_content' in clean ? (clean as Record<string, unknown>) : null
  return (
    <details className="rawclean">
      <summary>⚠️ {count} hidden instruction{count === 1 ? '' : 's'} found · raw vs what the AI saw</summary>
      <div className="cmp">
        <div>
          <h4>Raw (what the stranger wrote)</h4>
          <pre>{highlight(toText(raw), evidence)}</pre>
        </div>
        <div>
          <h4>What the AI saw</h4>
          {wrapper && <p className="note">{String(wrapper.note)}</p>}
          <pre>{toText(wrapper ? wrapper.content : clean)}</pre>
        </div>
      </div>
    </details>
  )
}
