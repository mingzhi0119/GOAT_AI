import type { FileBindingMode } from '../hooks/useFileContext'
import type { ReasoningLevel } from '../api/types'

export type { ReasoningLevel } from '../api/types'
export {
  AppearanceIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CloseIcon,
  CopiedIcon,
  CopyIcon,
  DocumentIcon,
  ImageIcon,
  ManageIcon,
  MoreIcon,
  NewChatIcon,
  PlanModeIcon,
  PlusIcon,
  SendArrowIcon,
  SettingsIcon,
  SidebarToggleIcon,
  StopIcon,
  ThinkingModeIcon,
  TrashIcon,
  UploadIcon,
} from './uiIcons'

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
