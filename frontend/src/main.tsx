import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import 'bootstrap/dist/css/bootstrap.min.css'
import './index.css'
import App from './App.tsx'
import ApplicationRuntime from './components/ApplicationRuntime.tsx'
import { SessionProvider } from './session/SessionContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <SessionProvider>
        <ApplicationRuntime>
          <App />
        </ApplicationRuntime>
      </SessionProvider>
    </BrowserRouter>
  </StrictMode>,
)
