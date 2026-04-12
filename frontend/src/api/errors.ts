interface ApiErrorEnvelope {
  detail?: unknown
  code?: unknown
  request_id?: unknown
}

function formatApiErrorMetadata(payload: ApiErrorEnvelope): string {
  const fragments: string[] = []
  if (typeof payload.code === 'string' && payload.code.trim()) {
    fragments.push(payload.code.trim())
  }
  if (typeof payload.request_id === 'string' && payload.request_id.trim()) {
    fragments.push(`request ${payload.request_id.trim()}`)
  }
  return fragments.length > 0 ? ` [${fragments.join('; ')}]` : ''
}

export function extractApiErrorDetail(payload: unknown): string | null {
  if (typeof payload !== 'object' || payload === null) return null
  const detail = (payload as ApiErrorEnvelope).detail
  if (typeof detail === 'string' && detail.trim()) return detail.trim()
  if (Array.isArray(detail)) return 'Request validation failed.'
  return null
}

export async function buildApiErrorMessage(
  resp: Response,
  fallbackPrefix: string,
): Promise<string> {
  try {
    const payload = (await resp.json()) as ApiErrorEnvelope
    const detail = extractApiErrorDetail(payload) ?? `${fallbackPrefix}: HTTP ${resp.status}`
    return `${detail}${formatApiErrorMetadata(payload)}`
  } catch {
    return `${fallbackPrefix}: HTTP ${resp.status}`
  }
}
