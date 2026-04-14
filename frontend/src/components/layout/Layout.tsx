import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../lib/auth'
import { useTheme } from '../../lib/ThemeContext'
import { Button } from '../ui/button'
import { NotificationDropdown } from './NotificationDropdown'
import {
  LayoutDashboard,
  FileText,
  FileCheck,
  LogOut,
  Menu,
  X,
  Users,
  Upload,
  Settings2,
  Calendar,
  BarChart3,
  Plus,
  Moon,
  Sun,
  TrendingUp,
  ShieldAlert,
  AlertTriangle,
} from 'lucide-react'
import { useState } from 'react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Fatture', href: '/invoices', icon: FileText },
  { name: 'Scadenziario', href: '/scadenziario', icon: Calendar },
  { name: 'SDI Fiscale', href: '/sdi-fiscale', icon: FileCheck },
  { name: 'Clienti', href: '/clients', icon: Users },
  { name: 'Report', href: '/reports', icon: BarChart3 },
  { name: 'Analytics', href: '/analytics', icon: TrendingUp },
  { name: 'Importa', href: '/import', icon: Upload },
  { name: 'Configurazione', href: '/config', icon: Settings2 },
]

const adminNavigation = [
  { name: 'Gestione Recovery', href: '/admin/collection', icon: AlertTriangle },
  { name: 'Clienti & Rischio', href: '/admin/clients', icon: ShieldAlert },
]

export function Layout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { theme, toggleTheme } = useTheme()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Mobile header */}
      <header className="lg:hidden bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50 safe-area-inset-top">
        <div className="flex items-center justify-between h-14 px-4">
          <span className="text-lg font-semibold text-primary-600">FatturaMVP</span>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title={theme === 'dark' ? 'Modalità chiara' : 'Modalità scura'}
            >
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <NotificationDropdown />
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-gray-500 hover:text-gray-700"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <nav className="bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 animate-slide-in">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors touch-manipulation ${
                    isActive
                      ? 'text-primary-600 bg-primary-50'
                      : 'text-gray-700 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              )
            })}
            {/* Admin section */}
            <div className="px-4 py-2">
              <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Admin</p>
            </div>
            {adminNavigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors ${
                    isActive
                      ? 'text-orange-600 bg-orange-50'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        )}
      </header>

      {/* Desktop sidebar */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-1 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
          <div className="flex items-center h-16 px-6 border-b border-gray-200 dark:border-gray-700">
            <span className="text-xl font-bold text-primary-600 dark:text-primary-400">FatturaMVP</span>
          </div>

          <nav className="flex-1 px-4 py-4 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? 'text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/30'
                      : 'text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              )
            })}

            {/* Admin section divider */}
            <div className="pt-4 pb-1">
              <div className="border-t border-gray-200 dark:border-gray-700" />
              <p className="text-[10px] uppercase tracking-wider text-gray-600 dark:text-gray-400 font-semibold mt-3 mb-1 px-3">Admin</p>
            </div>

            {adminNavigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/30'
                      : 'text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={toggleTheme}
              className="flex items-center gap-2 w-full mb-3 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
              title={theme === 'dark' ? 'Modalità chiara' : 'Modalità scura'}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              {theme === 'dark' ? 'Modalità chiara' : 'Modalità scura'}
            </button>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                <span className="text-sm font-medium text-primary-600 dark:text-primary-300">
                  {user?.username?.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{user?.email}</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={logout}
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="lg:pl-64 pb-20 lg:pb-6">
        <div className="py-6 px-4 sm:px-6 lg:px-8 safe-area-inset-bottom">
          <Outlet />
        </div>
      </main>

      {/* Mobile FAB - quick create invoice */}
      <Link
        to="/invoices?upload=true"
        className="lg:hidden fixed bottom-6 right-6 z-50 w-14 h-14 bg-primary-600 hover:bg-primary-700 text-white rounded-full shadow-lg flex items-center justify-center transition-all active:scale-95"
        title="Nuova fattura"
      >
        <Plus className="w-6 h-6" />
      </Link>
    </div>
  )
}
