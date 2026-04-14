// ─── Pricing Tiers ─────────────────────────────────────────────────────────

export const TIERS = {
  free: {
    id: "free",
    name: "Free",
    price: 0,
    description: "Per iniziare",
    highlighted: false,
    features: [
      "Fino a 5 fatture",
      "Scadenziario base",
      "Sollecito AI (10 msg/mese)",
      "1 utente",
    ],
    limits: {
      maxInvoices: 5,
      maxUsers: 1,
      aiReminders: 10,
      sdi: false,
    },
  },
  starter: {
    id: "starter",
    name: "Starter",
    price: 19,
    description: "Per freelance e piccoli studi",
    highlighted: false,
    features: [
      "Fino a 50 fatture",
      "Scadenziario intelligente",
      "Sollecito AI (100 msg/mese)",
      "Trust Score base",
      "1 utente",
    ],
    limits: {
      maxInvoices: 50,
      maxUsers: 1,
      aiReminders: 100,
      sdi: false,
    },
  },
  professional: {
    id: "professional",
    name: "Professional",
    price: 29,
    description: "Lo studio che cresce",
    highlighted: true,
    features: [
      "Fino a 500 fatture",
      "Scadenziario intelligente",
      "Sollecito AI illimitato",
      "Trust Score avanzato",
      "5 utenti",
      "Dashboard analytics",
      "Integrazione SDI",
      "Priorita supporto",
    ],
    limits: {
      maxInvoices: 500,
      maxUsers: 5,
      aiReminders: -1, // illimitato
      sdi: true,
    },
  },
  studio: {
    id: "studio",
    name: "Studio",
    price: 79,
    description: "Massima potenza e flessibilita",
    highlighted: false,
    features: [
      "Fatture illimitate",
      "Tutto di Professional",
      "Gestione multi-cliente",
      "Report avanzati",
      "20 utenti",
      "API access",
      "Dedicated account manager",
    ],
    limits: {
      maxInvoices: -1, // illimitato
      maxUsers: 20,
      aiReminders: -1,
      sdi: true,
    },
  },
} as const

export type TierId = keyof typeof TIERS
export type Tier = (typeof TIERS)[TierId]

// ─── Feature flags ─────────────────────────────────────────────────────────

/** Restituisce true se il tier ha accesso a SDI. */
export function hasSDI(tierId: TierId): boolean {
  return TIERS[tierId]?.limits.sdi === true
}

/** Restituisce true se il tier ha AI reminders illimitati. */
export function hasUnlimitedReminders(tierId: TierId): boolean {
  return TIERS[tierId]?.limits.aiReminders === -1
}

/** Restituisce true se il tier supporta il numero di fatture dato. */
export function canCreateInvoices(tierId: TierId, currentCount: number): boolean {
  const max = TIERS[tierId]?.limits.maxInvoices
  if (max === -1) return true
  return currentCount < max
}

/** Restituisce il prezzo mensile come stringa formattata. */
export function formatPrice(tierId: TierId): string {
  const price = TIERS[tierId]?.price ?? 0
  return price === 0 ? "Gratis" : `€${price}/mese`
}
