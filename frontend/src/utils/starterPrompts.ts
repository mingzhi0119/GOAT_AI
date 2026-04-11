export const STARTER_PROMPT_POOL = [
  'Summarize the biggest shifts in consumer behavior this year.',
  'What are the top strategic risks for 2026?',
  "Explain Porter's Five Forces in plain English.",
  'Draft a concise executive summary template.',
  'Compare premium vs value positioning for a consumer brand.',
  'What market signals suggest a category is saturating?',
  'Outline a simple competitor response framework.',
  'How should a company evaluate entering a new region?',
  'List likely drivers of margin pressure in retail.',
  'What questions should leadership ask before a pricing change?',
  'Turn this topic into a 5-slide briefing outline.',
  'What are three plausible growth scenarios for next year?',
  'Summarize likely customer segments for this offering.',
  'What are the best KPIs for tracking demand health?',
  'Draft a SWOT for a mid-market software company.',
  'How would you stress-test a go-to-market plan?',
  'What makes a strategy memo persuasive to executives?',
  'Identify likely operational bottlenecks from a scaling plan.',
  'How should we frame risks, assumptions, and unknowns?',
  'What are common failure modes in a product launch?',
  'Draft a board-style update in bullet points.',
  'What signals would indicate weakening pricing power?',
  'How would you analyze a new entrant in this market?',
  'Give me a quick framework for partnership evaluation.',
  'What are the strongest arguments for and against expansion?',
  'Summarize strategic tradeoffs between growth and profitability.',
  'How should a team prioritize opportunities under uncertainty?',
  'What are the likely second-order effects of a cost-cutting plan?',
  'Turn this into a clear recommendation with supporting rationale.',
  'What questions belong in a customer discovery interview?',
  'How would you structure a one-page strategic brief?',
  'What would an investor likely ask about this plan?',
  'Outline a market-entry checklist for a new category.',
  'What are credible hypotheses for declining conversion?',
  'How should we compare organic growth vs acquisition?',
  'Draft a risk register for a transformation initiative.',
  'What evidence would strengthen this recommendation?',
  'How would you separate signal from noise in this trend?',
  'Write a short problem statement and success criteria.',
  'What are the most important unknowns to validate first?',
] as const

export function pickRandomPromptTexts(
  pool: readonly string[],
  count: number,
  random: () => number = Math.random,
): string[] {
  const unique = Array.from(new Set(pool))
  const shuffled = [...unique]
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1))
    ;[shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex]!, shuffled[index]!]
  }
  return shuffled.slice(0, Math.max(0, Math.min(count, shuffled.length)))
}
