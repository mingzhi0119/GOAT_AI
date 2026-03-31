import type { FC } from 'react'

interface Props {
  size?: number
  /** Rounded square (sidebar) vs circle (e.g. chat avatar). */
  variant?: 'rounded' | 'circle'
}

/** Golden goat PNG — rounded gold frame in sidebar; optional circular thin gold ring for chat. */
const GoatIcon: FC<Props> = ({ size = 38, variant = 'rounded' }) => {
  const isCircle = variant === 'circle'
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: isCircle ? '50%' : Math.round(size * 0.21),
        border: isCircle ? '1px solid #FFCD00' : '1.5px solid #FFCD00',
        overflow: 'hidden',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: isCircle ? '#1a1a1a' : 'rgba(0, 0, 0, 0.25)',
      }}
    >
      <img
        src="./golden_goat_icon.png"
        alt="GOAT AI logo"
        style={{
          width: isCircle ? '92%' : '88%',
          height: isCircle ? '92%' : '88%',
          objectFit: 'contain',
        }}
      />
    </div>
  )
}

export default GoatIcon
