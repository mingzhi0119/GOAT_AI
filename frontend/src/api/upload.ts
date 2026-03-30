/** Stream CSV/XLSX upload analysis as tokens via Server-Sent Events. */
export async function* streamUpload(
  file: File,
  model: string,
): AsyncGenerator<string> {
  const form = new FormData()
  form.append('file', file)
  form.append('model', model)

  const resp = await fetch('/api/upload', { method: 'POST', body: form })
  if (!resp.ok) throw new Error(`Upload API: HTTP ${resp.status}`)
  if (!resp.body) throw new Error('Upload API: no response body')

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n')
    buffer = parts[parts.length - 1] ?? ''
    for (const line of parts.slice(0, -1)) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      try {
        const token = JSON.parse(raw) as string
        if (token === '[DONE]') return
        yield token
      } catch {
        // skip malformed frames
      }
    }
  }
}
