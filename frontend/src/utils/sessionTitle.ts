const CJK_CHAR_RE = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/

export function normalizeSessionTitle(text: string): string {
  return text.trim().replace(/\s+/g, ' ')
}

export function truncateSessionTitle(text: string): string {
  const normalized = normalizeSessionTitle(text)
  if (!normalized) return ''

  const limit = CJK_CHAR_RE.test(normalized) ? 15 : 26
  if (normalized.length <= limit) return normalized
  if (limit <= 3) return '.'.repeat(limit)
  return `${normalized.slice(0, limit - 3).trimEnd()}...`
}
