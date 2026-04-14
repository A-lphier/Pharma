import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import it from './locales/it.json'
import en from './locales/en.json'

export type Locale = 'it' | 'en'

const translations: Record<Locale, typeof it> = { it, en }

interface I18nContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: string) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

function getInitialLocale(): Locale {
  if (typeof window === 'undefined') return 'it'
  return (localStorage.getItem('locale') as Locale) || 'it'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getInitialLocale)

  const setLocale = useCallback((newLocale: Locale) => {
    localStorage.setItem('locale', newLocale)
    setLocaleState(newLocale)
  }, [])

  const t = useCallback(
    (key: string): string => {
      const keys = key.split('.')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let value: any = translations[locale]
      for (const k of keys) {
        value = value?.[k]
      }
      return value ?? key
    },
    [locale]
  )

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}

export const localeNames: Record<Locale, string> = {
  it: 'Italiano',
  en: 'English',
}
