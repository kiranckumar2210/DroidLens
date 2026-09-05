import { useEffect, useState } from 'react'
import type { XmlPackagePair } from '../offline/xmlPackage'
import { loadPackageNote, savePackageNote } from '../offline/packageNotes'

interface Props {
  packages: XmlPackagePair[]
  activeIndex: number
  onSelect: (index: number) => void
}

export default function OfflineScreenNav({ packages, activeIndex, onSelect }: Props) {
  const active = packages[activeIndex]
  const [note, setNote] = useState('')

  useEffect(() => {
    if (active) setNote(loadPackageNote(active))
  }, [active?.id, active?.xmlPath, active?.label])

  if (packages.length <= 1 && !active) return null

  const saveNote = (value: string) => {
    setNote(value)
    if (active) savePackageNote(active, value)
  }

  return (
    <nav className="offline-screen-nav" aria-label="Screens in folder">
      {packages.length > 1 && (
        <>
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
        </>
      )}
      {active && (
        <div className="offline-package-notes">
          <label htmlFor="package-notes">Notes</label>
          <textarea
            id="package-notes"
            rows={3}
            placeholder="Screen notes, bug context, test data…"
            value={note}
            onChange={(e) => saveNote(e.target.value)}
          />
        </div>
      )}
    </nav>
  )
}
