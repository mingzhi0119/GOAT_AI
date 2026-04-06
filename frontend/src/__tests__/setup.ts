import '@testing-library/jest-dom'

/** In-memory localStorage for hooks that read session/messages on mount. */
const storage: Record<string, string> = {}
const ls: Storage = {
  get length() {
    return Object.keys(storage).length
  },
  clear: () => {
    for (const k of Object.keys(storage)) delete storage[k]
  },
  getItem: (key: string): string | null => {
    const v = storage[key]
    return v === undefined ? null : v
  },
  key: (i: number) => Object.keys(storage)[i] ?? null,
  removeItem: (key: string) => {
    delete storage[key]
  },
  setItem: (key: string, value: string) => {
    storage[key] = value
  },
}
Object.defineProperty(globalThis, 'localStorage', { value: ls, writable: true })
