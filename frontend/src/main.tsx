import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/global.css'
import App from './App.tsx'

const rootEl = document.getElementById('root')
if (!rootEl) throw new Error('#root element missing from index.html')

createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
