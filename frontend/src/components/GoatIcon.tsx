import type { FC } from 'react'

interface Props {
  size?: number
}

/** Golden goat PNG with a thin gold rounded-corner frame — used in the sidebar logo. */
const GoatIcon: FC<Props> = ({ size = 38 }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: Math.round(size * 0.21),
      border: '1.5px solid #FFCD00',
      overflow: 'hidden',
      flexShrink: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'rgba(0, 0, 0, 0.25)',
    }}
  >
    <img
      src="./golden_goat_icon.png"
      alt="GOAT AI logo"
      style={{ width: '88%', height: '88%', objectFit: 'contain' }}
    />
  </div>
)

export default GoatIcon
