import {
  ArrowUp,
  Brain,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  FileText,
  Image,
  List,
  MoreHorizontal,
  Palette,
  PanelLeft,
  Plus,
  Route,
  Settings,
  Square,
  SquarePen,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import type { SVGProps } from 'react'

const DEFAULT_ICON_SIZE = 16
const DEFAULT_ICON_STROKE = 2

function iconProps(size = DEFAULT_ICON_SIZE, props: SVGProps<SVGSVGElement> = {}) {
  return {
    size,
    strokeWidth: DEFAULT_ICON_STROKE,
    focusable: 'false' as const,
    'aria-hidden': 'true' as const,
    ...props,
  }
}

export const PlusIcon = (props: SVGProps<SVGSVGElement>) => <Plus {...iconProps(16, props)} />
export const CloseIcon = (props: SVGProps<SVGSVGElement>) => <X {...iconProps(12, props)} />
export const SendArrowIcon = (props: SVGProps<SVGSVGElement>) => (
  <ArrowUp {...iconProps(20, props)} />
)
export const StopIcon = (props: SVGProps<SVGSVGElement>) => <Square {...iconProps(18, props)} />
export const UploadIcon = (props: SVGProps<SVGSVGElement>) => <Upload {...iconProps(16, props)} />
export const ManageIcon = (props: SVGProps<SVGSVGElement>) => <List {...iconProps(16, props)} />
export const PlanModeIcon = (props: SVGProps<SVGSVGElement>) => <Route {...iconProps(16, props)} />
export const ThinkingModeIcon = (props: SVGProps<SVGSVGElement>) => (
  <Brain {...iconProps(16, props)} />
)
export const ChevronRightIcon = (props: SVGProps<SVGSVGElement>) => (
  <ChevronRight {...iconProps(14, props)} />
)
export const ChevronDownIcon = (props: SVGProps<SVGSVGElement>) => (
  <ChevronDown {...iconProps(12, props)} />
)
export const CheckIcon = (props: SVGProps<SVGSVGElement>) => <Check {...iconProps(14, props)} />
export const DocumentIcon = (props: SVGProps<SVGSVGElement>) => (
  <FileText {...iconProps(14, props)} />
)
export const ImageIcon = (props: SVGProps<SVGSVGElement>) => <Image {...iconProps(14, props)} />
export const SidebarToggleIcon = (props: SVGProps<SVGSVGElement>) => (
  <PanelLeft {...iconProps(16, props)} />
)
export const SettingsIcon = (props: SVGProps<SVGSVGElement>) => (
  <Settings {...iconProps(16, props)} />
)
export const MoreIcon = (props: SVGProps<SVGSVGElement>) => (
  <MoreHorizontal {...iconProps(16, props)} />
)
export const AppearanceIcon = (props: SVGProps<SVGSVGElement>) => (
  <Palette {...iconProps(14, props)} />
)
export const CopyIcon = (props: SVGProps<SVGSVGElement>) => <Copy {...iconProps(12, props)} />
export const CopiedIcon = (props: SVGProps<SVGSVGElement>) => <Check {...iconProps(12, props)} />
export const NewChatIcon = (props: SVGProps<SVGSVGElement>) => (
  <SquarePen {...iconProps(15, props)} />
)
export const TrashIcon = (props: SVGProps<SVGSVGElement>) => <Trash2 {...iconProps(14, props)} />
