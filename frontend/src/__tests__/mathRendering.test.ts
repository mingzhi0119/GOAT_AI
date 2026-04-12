import { describe, expect, it } from 'vitest'
import { buildMathRenderPlan } from '../utils/mathRendering'

describe('mathRendering', () => {
  it('renders complete block formulas immediately while streaming', () => {
    const plan = buildMathRenderPlan('Here is $$E=mc^2$$ and more text', true)

    expect(plan.renderedMarkdownPrefix).toBe('Here is $$E=mc^2$$ and more text')
    expect(plan.trailingPlainText).toBe('')
    expect(plan.enableMath).toBe(true)
  })

  it('renders complete inline formulas immediately while streaming', () => {
    const plan = buildMathRenderPlan('The slope is $m$ today.', true)

    expect(plan.renderedMarkdownPrefix).toBe('The slope is $m$ today.')
    expect(plan.trailingPlainText).toBe('')
    expect(plan.enableMath).toBe(true)
  })

  it('keeps only the incomplete trailing formula as plain text while streaming', () => {
    const plan = buildMathRenderPlan('Closed $x$ before open $$y^2', true)

    expect(plan.renderedMarkdownPrefix).toBe('Closed $x$ before open ')
    expect(plan.trailingPlainText).toBe('$$y^2')
    expect(plan.enableMath).toBe(true)
  })

  it('ignores code spans and fenced code blocks when slicing math', () => {
    const inlineCodePlan = buildMathRenderPlan('Use `$x$` and then $$E=mc^2$$', true)
    const fencedCodePlan = buildMathRenderPlan('```text\n$E=mc^2$\n```\n\n$x$', true)

    expect(inlineCodePlan.trailingPlainText).toBe('')
    expect(inlineCodePlan.enableMath).toBe(true)
    expect(fencedCodePlan.trailingPlainText).toBe('')
    expect(fencedCodePlan.enableMath).toBe(true)
  })

  it('does not treat prices or plain dollars as math', () => {
    const pricePlan = buildMathRenderPlan('It costs $5 today and $12 tomorrow.', true)

    expect(pricePlan.renderedMarkdownPrefix).toBe('It costs $5 today and $12 tomorrow.')
    expect(pricePlan.trailingPlainText).toBe('')
    expect(pricePlan.enableMath).toBe(false)
  })
})
