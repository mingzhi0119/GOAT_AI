import type { FC } from 'react'
import { ZodiacCapricorn } from 'lucide-react'

interface Props {
  size?: number
  /** Rounded square (sidebar) vs circle (e.g. chat avatar). */
  variant?: 'rounded' | 'circle'
}

/** Brand icon frame for GOAT; optional circular variant for chat surfaces. */
const GoatIcon: FC<Props> = ({ size = 38, variant = 'rounded' }) => {
  const isCircle = variant === 'circle'
  return (
    <div
      className="goat-icon-frame"
      style={{
        width: size,
        height: size,
        borderRadius: isCircle ? '50%' : Math.round(size * 0.21),
        overflow: 'hidden',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <ZodiacCapricorn
        size={Math.round(size * 0.62)}
        strokeWidth={2}
        aria-hidden="true"
        focusable="false"
        color="var(--gold)"
      />
    </div>
  )
}

export default GoatIcon
