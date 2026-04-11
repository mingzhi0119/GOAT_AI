import { describe, expect, it, vi } from 'vitest'
import { pickRandomPromptTexts, STARTER_PROMPT_POOL } from '../utils/starterPrompts'

describe('starter prompt pool', () => {
  it('contains a broad prompt pool', () => {
    expect(STARTER_PROMPT_POOL.length).toBeGreaterThanOrEqual(40)
  })

  it('returns a unique random subset capped by the requested count', () => {
    const random = vi
      .fn<() => number>()
      .mockReturnValueOnce(0.2)
      .mockReturnValueOnce(0.7)
      .mockReturnValueOnce(0.1)
      .mockReturnValueOnce(0.9)
      .mockReturnValue(0.4)

    const prompts = pickRandomPromptTexts(
      ['a', 'b', 'c', 'd', 'e', 'e'],
      4,
      random,
    )

    expect(prompts).toHaveLength(4)
    expect(new Set(prompts).size).toBe(4)
  })
})
