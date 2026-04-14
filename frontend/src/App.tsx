import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './lib/auth'
import { ThemeProvider } from './lib/ThemeContext'
import { LoginPage } from './routes/login'
import { DashboardPage } from './routes/dashboard'
import { InvoicesPage } from './routes/invoices'
import { InvoiceDetailPage } from './routes/invoice-detail'
import { ClientsPage } from './routes/clients'
import { ClientDetailPage } from './routes/client-detail'
import { ClientStatusPage } from './routes/client-status'
import { ClientFormPage } from './routes/client-form'
import { OnboardingPage } from './routes/onboarding'
import { ConfigPage } from './routes/config'
import { ImportPage } from './routes/import'
import { Layout } from './components/layout/Layout'
import { ScadenziarioPage } from './routes/scadenziario'
import { ReportsPage } from './routes/reports'
import { AnalyticsPage } from './routes/analytics'
import { NotFoundPage } from './routes/not-found'
import { LandingPage } from './routes/landing'
import { BillingPage } from './routes/billing'
import { PaymentSuccessPage } from './routes/payment-success'
import { PaymentCancelPage } from './routes/payment-cancel'
import { AdminCollectionPage } from './routes/admin-collection'
import { AdminClientsPage } from './routes/admin-clients'
import { ClientPortalPage } from './routes/client-portal'
import { SdiFiscalPage } from './routes/sdi-fiscale'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  const { isAuthenticated } = useAuthStore()
  return (
    <ThemeProvider>
    <Routes>
      <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LandingPage />} />
      <Route path="/register" element={<LandingPage />} />
      <Route path="/landing" element={<LandingPage />} />
      <Route path="/billing" element={<BillingPage />} />
        <Route path="/payment-success" element={<PaymentSuccessPage />} />
        <Route path="/payment-cancel" element={<PaymentCancelPage />} />
      <Route path="/portal/:token" element={<ClientPortalPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={<DashboardPage />} />
        <Route index element={<DashboardPage />} />
        <Route path="invoices" element={<InvoicesPage />} />
        <Route path="invoices/:id" element={<InvoiceDetailPage />} />
        <Route path="clients" element={<ClientsPage />} />
        <Route path="clients/new" element={<ClientFormPage />} />
        <Route path="clients/:id" element={<ClientDetailPage />} />
        <Route path="clients/:id/status" element={<ClientStatusPage />} />
        <Route path="clients/:id/edit" element={<ClientFormPage />} />
        <Route path="config" element={<ConfigPage />} />
        <Route path="import" element={<ImportPage />} />
        <Route path="scadenziario" element={<ScadenziarioPage />} />
        <Route path="sdi-fiscale" element={<SdiFiscalPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="admin/collection" element={<AdminCollectionPage />} />
        <Route path="admin/clients" element={<AdminClientsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
    </ThemeProvider>
  )
}

export default App
