import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { App } from './app/App'
import { AtlasProvider } from './app/AtlasContext'
import { queryClient } from './app/queryClient'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AtlasProvider><App /></AtlasProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
