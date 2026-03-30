import type { FC } from 'react'

interface Props {
  size?: number
  color?: string
}

/** Stylised geometric goat head — used in the sidebar logo. */
const GoatIcon: FC<Props> = ({ size = 38, color = '#FFCD00' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 36 36"
    fill={color}
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    {/* Left horn — sweeps up and slightly outward */}
    <path d="M11.5 12 C9.5 6 6 3 4 5.5 C5.5 8.5 8.5 11 11.5 12Z" />
    {/* Right horn */}
    <path d="M24.5 12 C26.5 6 30 3 32 5.5 C30.5 8.5 27.5 11 24.5 12Z" />
    {/* Left ear */}
    <path d="M9 19 C5 16 3.5 21.5 8 22.5Z" />
    {/* Right ear */}
    <path d="M27 19 C31 16 32.5 21.5 28 22.5Z" />
    {/* Head (main circle) */}
    <circle cx="18" cy="20" r="10" />
    {/* Muzzle */}
    <ellipse cx="18" cy="27" rx="5.5" ry="3.5" />
    {/* Beard */}
    <ellipse cx="18" cy="31.5" rx="2.8" ry="2.2" />
  </svg>
)

export default GoatIcon
