import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { SystemConfigProvider } from './auth/SystemConfigContext'
import { ToastProvider } from './components/ui/Toast'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ToastProvider>
      <SystemConfigProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </SystemConfigProvider>
    </ToastProvider>
  </React.StrictMode>,
)
