import type { XmlPackagePair } from '../offline/xmlPackage'

interface Props {
  packages: XmlPackagePair[]
  activeIndex: number
  onSelect: (index: number) => void
}

export default function OfflineScreenNav({ packages, activeIndex, onSelect }: Props) {
  if (packages.length <= 1) return null

  return (
    <nav className="offline-screen-nav" aria-label="Screens in folder">
      <div className="offline-screen-nav-title">Screens</div>
      <ul>
        {packages.map((pkg, idx) => (
          <li key={pkg.id}>
            <button
              type="button"
              className={idx === activeIndex ? 'active' : ''}
              onClick={() => onSelect(idx)}
              title={pkg.label}
            >
              {pkg.label}
              {!pkg.screenshot && !pkg.screenshotPath && (
                <span className="offline-screen-badge">XML</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
