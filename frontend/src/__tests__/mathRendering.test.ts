import { describe, expect, it } from 'vitest'
import { shouldRenderMathMarkdown } from '../utils/mathRendering'

describe('mathRendering', () => {
  it('enables math rendering for explicit block formulas', () => {
    expect(shouldRenderMathMarkdown('Here is $$E=mc^2$$', false)).toBe(true)
    expect(shouldRenderMathMarkdown('Here is \\[E=mc^2\\]', false)).toBe(true)
  })

  it('enables math rendering for clear inline formulas', () => {
    expect(shouldRenderMathMarkdown('The slope is $m$', false)).toBe(true)
    expect(shouldRenderMathMarkdown('Use $\\frac{1}{2}$ here', false)).toBe(true)
  })

  it('does not enable math rendering for plain dollars or incomplete streaming text', () => {
    expect(shouldRenderMathMarkdown('It costs $5 today', false)).toBe(false)
    expect(shouldRenderMathMarkdown('Math starts with $\\frac{1}{2', true)).toBe(false)
  })

  it('ignores code spans and fenced code blocks', () => {
    expect(shouldRenderMathMarkdown('`$x$`', false)).toBe(false)
    expect(shouldRenderMathMarkdown('```text\n$E=mc^2$\n```', false)).toBe(false)
  })
})
