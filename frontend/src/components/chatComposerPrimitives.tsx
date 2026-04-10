import type { FileBindingMode } from '../hooks/useFileContext'

export type ReasoningLevel = 'low' | 'medium' | 'high'

export const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M8 3.25v9.5M3.25 8h9.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
)

export const CloseIcon = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
    <path
      d="M3 3l6 6M9 3 3 9"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
    />
  </svg>
)

export const SendArrowIcon = () => (
  <svg width="24" height="24" viewBox="0 0 20 20" fill="none" aria-hidden="true">
    <path
      d="M10 15.25V4.75M10 4.75 5.9 8.85M10 4.75l4.1 4.1"
      stroke="currentColor"
      strokeWidth="2.15"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export const StopIcon = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
    <rect x="4" y="4" width="10" height="10" rx="2" fill="currentColor" />
  </svg>
)

export const UploadIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M8 10.75V3.75M8 3.75 5.5 6.25M8 3.75l2.5 2.5M3.75 10.5v1.25c0 .28.22.5.5.5h7.5c.28 0 .5-.22.5-.5V10.5"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export const ManageIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M3 4.25h10M3 8h10M3 11.75h6"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
    />
  </svg>
)

export const PlanModeIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M4 3.75h8M4 8h5.5M4 12.25h6.5"
      stroke="currentColor"
      strokeWidth="1.45"
      strokeLinecap="round"
    />
    <circle cx="11.75" cy="8" r="1.25" fill="currentColor" />
  </svg>
)

export const ThinkingModeIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M8 2.75a3.25 3.25 0 0 0-3.25 3.25c0 1.28.74 2.39 1.82 2.92.22.11.36.33.36.57v.96h2.14v-.96c0-.24.14-.46.36-.57A3.245 3.245 0 0 0 11.25 6 3.25 3.25 0 0 0 8 2.75Z"
      stroke="currentColor"
      strokeWidth="1.25"
      strokeLinejoin="round"
    />
    <path d="M6.25 12.25h3.5" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
    <path
      d="M8 13.25v.75M5.9 4.9l-.9-.9M10.1 4.9l.9-.9"
      stroke="currentColor"
      strokeWidth="1.1"
      strokeLinecap="round"
    />
  </svg>
)

export const ChevronRightIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
    <path
      d="M5.25 3.5 8.75 7l-3.5 3.5"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export const ChevronDownIcon = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
    <path
      d="M3 4.5 6 7.5l3-3"
      stroke="currentColor"
      strokeWidth="1.35"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
    <path
      d="M3.5 7.3 5.8 9.6l4.7-4.9"
      stroke="currentColor"
      strokeWidth="1.45"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export const DocumentIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M5 2.75h4.5L12.25 5.5V12.25a1 1 0 0 1-1 1h-6.5a1 1 0 0 1-1-1v-8.5a1 1 0 0 1 1-1Z"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinejoin="round"
    />
    <path d="M9.5 2.75V5.5h2.75" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
  </svg>
)

export const ImageIcon = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <rect x="2.5" y="3" width="11" height="10" rx="2" stroke="currentColor" strokeWidth="1.3" />
    <circle cx="6" cy="6.5" r="1" fill="currentColor" />
    <path
      d="M4 11l2.5-2.5 1.75 1.75L10.5 8 12 9.5"
      stroke="currentColor"
      strokeWidth="1.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export const ProcessingDot = () => (
  <span className="inline-flex h-2 w-2 rounded-full bg-amber-400/80" aria-hidden="true" />
)

export const ReadyDot = () => (
  <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400/80" aria-hidden="true" />
)

export function modeLabel(mode: FileBindingMode): string {
  if (mode === 'single') return 'Next'
  if (mode === 'persistent') return 'Sticky'
  return 'Off'
}

export function reasoningLabel(level: ReasoningLevel): string {
  if (level === 'low') return 'Low'
  if (level === 'high') return 'High'
  return 'Medium'
}
