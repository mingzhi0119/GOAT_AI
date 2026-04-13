export interface MathRenderPlan {
  renderedMarkdownPrefix: string
  trailingPlainText: string
  enableMath: boolean
}

type OpenMathKind = 'inline-dollar' | 'display-dollar' | 'bracket'

const FENCE = '```'

function isEscaped(text: string, index: number): boolean {
  let slashCount = 0
  for (let cursor = index - 1; cursor >= 0 && text[cursor] === '\\'; cursor -= 1) {
    slashCount += 1
  }
  return slashCount % 2 === 1
}

function canStartInlineDollar(text: string, index: number): boolean {
  const next = text[index + 1] ?? ''
  if (!next || /\s/.test(next) || /\d/.test(next)) return false
  return true
}

function canEndInlineDollar(text: string, index: number): boolean {
  const previous = text[index - 1] ?? ''
  if (!previous || /\s/.test(previous)) return false
  return true
}

function findOpenMathStart(text: string): number | null {
  let inFencedCode = false
  let inInlineCode = false
  let openMathKind: OpenMathKind | null = null
  let openMathStart: number | null = null

  for (let index = 0; index < text.length; index += 1) {
    if (!inInlineCode && text.startsWith(FENCE, index)) {
      inFencedCode = !inFencedCode
      index += FENCE.length - 1
      continue
    }

    if (inFencedCode) continue

    if (text[index] === '`') {
      inInlineCode = !inInlineCode
      continue
    }

    if (inInlineCode) continue

    if (openMathKind === null) {
      if (text.startsWith('\\[', index) && !isEscaped(text, index)) {
        openMathKind = 'bracket'
        openMathStart = index
        index += 1
        continue
      }
      if (text[index] !== '$' || isEscaped(text, index)) continue
      if (text[index + 1] === '$') {
        openMathKind = 'display-dollar'
        openMathStart = index
        index += 1
        continue
      }
      if (canStartInlineDollar(text, index)) {
        openMathKind = 'inline-dollar'
        openMathStart = index
      }
      continue
    }

    if (openMathKind === 'bracket') {
      if (text.startsWith('\\]', index) && !isEscaped(text, index)) {
        openMathKind = null
        openMathStart = null
        index += 1
      }
      continue
    }

    if (text[index] !== '$' || isEscaped(text, index)) continue

    if (openMathKind === 'display-dollar') {
      if (text[index + 1] === '$') {
        openMathKind = null
        openMathStart = null
        index += 1
      }
      continue
    }

    if (canEndInlineDollar(text, index)) {
      openMathKind = null
      openMathStart = null
    }
  }

  return openMathStart
}

function stripCodeSegments(text: string): string {
  let stripped = ''
  let inFencedCode = false
  let inInlineCode = false

  for (let index = 0; index < text.length; index += 1) {
    if (!inInlineCode && text.startsWith(FENCE, index)) {
      inFencedCode = !inFencedCode
      stripped += ' '
      index += FENCE.length - 1
      continue
    }

    if (!inFencedCode && text[index] === '`') {
      inInlineCode = !inInlineCode
      stripped += ' '
      continue
    }

    stripped += inFencedCode || inInlineCode ? ' ' : text[index]
  }

  return stripped
}

function containsBalancedMath(text: string): boolean {
  const openMathStart = findOpenMathStart(text)
  if (openMathStart !== null) {
    return openMathStart > 0 && containsBalancedMath(text.slice(0, openMathStart))
  }
  const sanitized = stripCodeSegments(text)
  return /(^|[^\\])\$\$[\s\S]+?\$\$(?!\$)/.test(sanitized)
    || /\\\[[\s\S]+?\\\]/.test(sanitized)
    || /(^|[^\\])\$(?!\s|\d)[\s\S]*?[^\s\\]\$(?!\d)/.test(sanitized)
}

const DISPLAY_BLOCK_RE = /(^|\n[ \t]*\n)([ \t]*)\$\$([\s\S]+?)\$\$([ \t]*)(?=\n[ \t]*\n|[ \t]*$)/g

export function normalizeDisplayMathMarkdown(text: string): string {
  return text.replace(DISPLAY_BLOCK_RE, (_match, prefix: string, _indent: string, body: string) => {
    const cleanedBody = body.trim()
    return `${prefix}$$\n${cleanedBody}\n$$`
  })
}

export function buildMathRenderPlan(text: string, isStreaming: boolean): MathRenderPlan {
  if (!isStreaming) {
    return {
      renderedMarkdownPrefix: text,
      trailingPlainText: '',
      enableMath: containsBalancedMath(text),
    }
  }

  const openMathStart = findOpenMathStart(text)
  const renderedMarkdownPrefix = openMathStart === null ? text : text.slice(0, openMathStart)
  const trailingPlainText = openMathStart === null ? '' : text.slice(openMathStart)

  return {
    renderedMarkdownPrefix,
    trailingPlainText,
    enableMath: containsBalancedMath(renderedMarkdownPrefix),
  }
}
