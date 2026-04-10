const FENCED_CODE_RE = /```[\s\S]*?```/g
const INLINE_CODE_RE = /`[^`\n]*`/g

const DISPLAY_MATH_RE = /(^|[^\\])\$\$([\s\S]+?)\$\$(?!\$)/g
const DISPLAY_BLOCK_RE = /(^|\n[ \t]*\n)([ \t]*)\$\$([\s\S]+?)\$\$([ \t]*)(?=\n[ \t]*\n|[ \t]*$)/g
const BRACKET_MATH_RE = /\\\[[\s\S]+?\\\]/g
const INLINE_MATH_RE = /(^|[^\\])\$(?!\s)([^$\n]{1,120}?)(?<!\s)\$(?!\d)/g

function stripCodeSegments(text: string): string {
  return text.replace(FENCED_CODE_RE, ' ').replace(INLINE_CODE_RE, ' ')
}

function isLikelyInlineMath(body: string): boolean {
  const trimmed = body.trim()
  if (trimmed.length === 0) return false
  if (/[\\^_=+\-*/<>]/.test(trimmed)) return true
  if (/\s/.test(trimmed)) return false
  return trimmed.length <= 12 && /^[A-Za-z0-9]+$/.test(trimmed)
}

function hasBalancedDisplayMath(text: string): boolean {
  DISPLAY_MATH_RE.lastIndex = 0
  BRACKET_MATH_RE.lastIndex = 0
  return DISPLAY_MATH_RE.test(text) || BRACKET_MATH_RE.test(text)
}

function hasBalancedInlineMath(text: string): boolean {
  INLINE_MATH_RE.lastIndex = 0
  for (;;) {
    const match = INLINE_MATH_RE.exec(text)
    if (!match) return false
    const body = (match[2] ?? '').trim()
    if (isLikelyInlineMath(body)) return true
  }
}

/**
 * Return true only when the message is complete and contains an explicit math
 * expression worth rendering with KaTeX.
 */
export function shouldRenderMathMarkdown(text: string, isStreaming: boolean): boolean {
  if (isStreaming) return false
  const sanitized = stripCodeSegments(text)
  return hasBalancedDisplayMath(sanitized) || hasBalancedInlineMath(sanitized)
}

export function normalizeDisplayMathMarkdown(text: string): string {
  return text.replace(DISPLAY_BLOCK_RE, (_match, prefix: string, _indent: string, body: string) => {
    const cleanedBody = body.trim()
    return `${prefix}$$\n${cleanedBody}\n$$`
  })
}
