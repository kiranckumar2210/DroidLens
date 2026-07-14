import { ShieldOff } from 'lucide-react'
import './admin.css'

export default function AccessDenied() {
  return (
    <div className="admin-denied">
      <div>
        <ShieldOff size={48} style={{ marginBottom: '1rem', opacity: 0.6 }} />
        <h1>403</h1>
        <p>You don&apos;t have permission to access the admin dashboard.</p>
        <a href="/" className="admin-btn primary">Back to DroidLens</a>
      </div>
    </div>
  )
}
