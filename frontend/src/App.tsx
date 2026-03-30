import { useEffect, useState } from 'react'

interface HealthResponse {
  status: string
  stack: string
}

/** Phase 0 smoke-test: renders a ping to /api/health and shows the result. */
export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<HealthResponse>
      })
      .then(setHealth)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Unknown error'),
      )
  }, [])

  return (
    <div style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
      <h1>🐐 GOAT AI — Phase 0</h1>
      <p>
        <strong>React build:</strong> ✅ working (Node {process.env.NODE_ENV})
      </p>
      <p>
        <strong>FastAPI /api/health:</strong>{' '}
        {health ? (
          <span style={{ color: 'green' }}>
            ✅ {JSON.stringify(health)}
          </span>
        ) : error ? (
          <span style={{ color: 'red' }}>❌ {error}</span>
        ) : (
          '⏳ checking…'
        )}
      </p>
    </div>
  )
}
