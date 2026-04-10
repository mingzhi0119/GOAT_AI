export const brandingConfig = {
  internalId: 'GOAT_AI',
  displayName: 'GOAT',
  appTitle: 'GOAT - Simon Business School',
  appDescription: 'GOAT - Strategic Intelligence by Simon Business School',
} as const

export function useBranding() {
  return brandingConfig
}
