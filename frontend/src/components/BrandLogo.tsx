interface Props {
  size?: number
  showWordmark?: boolean
  className?: string
}

/** DroidLens brand mark — Android head + inspection lens + UI nodes. */
export default function BrandLogo({ size = 32, showWordmark = false, className = '' }: Props) {
  if (showWordmark) {
    return (
      <img
        src="/branding/logo.svg"
        alt="DroidLens — See. Inspect. Automate."
        className={`brand-logo-wordmark ${className}`}
        height={size}
        draggable={false}
      />
    )
  }

  const s = size
  return (
    <svg
      className={`brand-logo ${className}`}
      width={s}
      height={s}
      viewBox="0 0 512 512"
      role="img"
      aria-label="DroidLens"
    >
      <defs>
        <linearGradient id="dl-bg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#2f3b42" />
          <stop offset="100%" stopColor="#263238" />
        </linearGradient>
        <linearGradient id="dl-lens" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#42A5F5" />
          <stop offset="100%" stopColor="#1E88E5" />
        </linearGradient>
      </defs>
      <rect width="512" height="512" rx="108" fill="url(#dl-bg)" />
      <g stroke="#78909C" strokeWidth="6" strokeLinecap="round" opacity="0.55">
        <line x1="118" y1="372" x2="178" y2="332" />
        <line x1="178" y1="332" x2="238" y2="352" />
        <circle cx="118" cy="372" r="10" fill="#B0BEC5" />
        <circle cx="178" cy="332" r="10" fill="#B0BEC5" />
        <circle cx="238" cy="352" r="10" fill="#B0BEC5" />
      </g>
      <g fill="#34A853">
        <rect x="156" y="118" width="18" height="44" rx="9" />
        <rect x="338" y="118" width="18" height="44" rx="9" />
        <path d="M256 156 C176 156 132 214 132 286 C132 358 176 396 256 396 C336 396 380 358 380 286 C380 214 336 156 256 156 Z" />
      </g>
      <ellipse cx="256" cy="292" rx="92" ry="72" fill="#263238" />
      <circle cx="220" cy="276" r="16" fill="#ECEFF1" />
      <circle cx="292" cy="276" r="16" fill="#ECEFF1" />
      <circle cx="332" cy="332" r="78" fill="none" stroke="url(#dl-lens)" strokeWidth="22" />
      <circle cx="332" cy="332" r="52" fill="rgba(255,255,255,0.12)" />
      <g stroke="#FFFFFF" strokeWidth="5" strokeLinecap="round" opacity="0.95">
        <line x1="332" y1="296" x2="332" y2="318" />
        <line x1="332" y1="346" x2="332" y2="368" />
        <line x1="296" y1="332" x2="318" y2="332" />
        <line x1="346" y1="332" x2="368" y2="332" />
        <circle cx="332" cy="332" r="14" fill="none" stroke="#FFFFFF" strokeWidth="4" />
      </g>
      <line x1="388" y1="388" x2="438" y2="438" stroke="url(#dl-lens)" strokeWidth="22" strokeLinecap="round" />
    </svg>
  )
}
