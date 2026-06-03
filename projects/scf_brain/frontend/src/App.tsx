import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HomePage } from '@/pages/home'
import { AssessmentPage } from '@/pages/assessment'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/assessment/:runId" element={<AssessmentPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
