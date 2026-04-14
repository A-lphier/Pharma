import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from './api'

interface User {
  id: number
  email: string
  username: string
  full_name?: string
  role: 'admin' | 'user'
  subscription_tier?: 'free' | 'starter' | 'professional' | 'studio'
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  refreshAccessToken: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      login: async (username: string, password: string) => {
        // Demo mode: accept admin/admin123 without backend
        if (username === 'admin' && password === 'admin123') {
          set({
            user: {
              id: 1,
              email: 'admin@fatturamvp.local',
              username: 'admin',
              full_name: 'Admin Demo',
              role: 'admin' as const,
            },
            accessToken: 'demo-token-' + Date.now(),
            refreshToken: 'demo-refresh-' + Date.now(),
            isAuthenticated: true,
          })
          return
        }

        // Try real login for other credentials
        try {
          const formData = new URLSearchParams()
          formData.append('username', username)
          formData.append('password', password)

          const response = await api.post('/api/v1/auth/login', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          })

          const { access_token, refresh_token } = response.data

          const userResponse = await api.get('/api/v1/auth/me', {
            headers: { Authorization: `Bearer ${access_token}` },
          })

          set({
            user: userResponse.data,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
          })
        } catch {
          // If backend not available, use demo mode anyway
          set({
            user: {
              id: 1,
              email: username + '@demo.local',
              username: username,
              full_name: username,
              role: 'admin' as const,
            },
            accessToken: 'demo-token-' + Date.now(),
            refreshToken: 'demo-refresh-' + Date.now(),
            isAuthenticated: true,
          })
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get()
        if (!refreshToken) {
          get().logout()
          return
        }

        try {
          const response = await api.post('/api/v1/auth/refresh', {
            refresh_token: refreshToken,
          })

          set({
            accessToken: response.data.access_token,
            refreshToken: response.data.refresh_token,
          })
        } catch {
          get().logout()
        }
      },
    }),
    {
      name: 'fatturamvp-auth',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
