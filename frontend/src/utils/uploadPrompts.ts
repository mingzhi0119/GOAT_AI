const SUFFIX_PROMPTS: Record<string, string> = {
  csv: 'Inspect this CSV for trends, anomalies, and key comparisons.',
  xlsx: 'Inspect this spreadsheet for trends, anomalies, and key comparisons.',
  txt: 'Summarize this text file and highlight the most important details.',
  md: 'Summarize this document and extract the main takeaways.',
  pdf: 'Summarize this PDF and cite the key evidence behind each point.',
  docx: 'Summarize this document and extract the main takeaways.',
}

const TEMPLATE_FALLBACKS: Record<string, string> = {
  csv: 'Analyze this CSV and tell me the main trends, outliers, and comparisons worth noting.',
  xlsx: 'Analyze this spreadsheet and tell me the main trends, outliers, and comparisons worth noting.',
  txt: 'Summarize this text file, identify the key themes, and recommend what to do next.',
  md: 'Summarize this document, identify the key themes, and recommend what to do next.',
  pdf: 'Summarize this PDF, identify the key arguments, and recommend what to do next.',
  docx: 'Summarize this document, identify the key arguments, and recommend what to do next.',
}

export function getFileExtension(filename: string): string {
  const idx = filename.lastIndexOf('.')
  return idx >= 0 ? filename.slice(idx + 1).toLowerCase() : ''
}

export function getSuffixPrompt(filename: string): string {
  const ext = getFileExtension(filename)
  return SUFFIX_PROMPTS[ext] ?? 'Tell me what this file contains and how I should analyze it.'
}

export function getTemplateFallbackPrompt(filename: string): string {
  const ext = getFileExtension(filename)
  return TEMPLATE_FALLBACKS[ext] ?? 'Analyze this file and suggest the best follow-up prompt for exploring its contents.'
}
