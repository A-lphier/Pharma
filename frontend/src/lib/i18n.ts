import it from './locales/it.json'
import en from './locales/en.json'

export type Locale = 'it' | 'en'

const translations: Record<Locale, typeof it> = { it, en }

export function getLocale(): Locale {
  return (localStorage.getItem('locale') as Locale) || 'it'
}

export function setLocale(locale: Locale) {
  localStorage.setItem('locale', locale)
  window.dispatchEvent(new CustomEvent('locale-changed', { detail: { locale } }))
}

export function t(key: string): string {
  const locale = getLocale()
  const keys = key.split('.')
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let value: any = translations[locale]
  for (const k of keys) {
    value = value?.[k]
  }
  return value ?? key
}

export const localeNames: Record<Locale, string> = {
  it: 'Italiano',
  en: 'English',
}
