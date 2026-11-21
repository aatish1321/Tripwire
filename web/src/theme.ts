export type Theme = 'dark' | 'light'
const KEY = 'tripwire-theme'

/** A saved choice wins; otherwise follow the system. */
export function pickTheme(saved: string | null, prefersLight: boolean): Theme {
  return saved === 'light' || saved === 'dark' ? saved : prefersLight ? 'light' : 'dark'
}

/** The theme index.html already applied before the first paint (see the inline script there). */
export function currentTheme(): Theme {
  return typeof document !== 'undefined' && document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'
}

/** Applies a theme and remembers it. Storage can be blocked (private windows), so a failed save is not an error. */
export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    /* applied for this visit, just not remembered */
  }
}
