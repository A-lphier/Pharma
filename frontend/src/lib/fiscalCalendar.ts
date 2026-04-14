/**
 * Fiscal Calendar — Italian tax deadlines 2026
 * Source: Agenzia delle Entrate official calendar
 */

export interface FiscalEvent {
  id: string
  date: string              // ISO date YYYY-MM-DD
  label: string
  description: string
  tipo: 'IVA' | 'IRPEF' | 'IRAP' | 'INPS' | 'COMUNICAZIONE' | 'SCADENZA' | 'ACCONTO'
  impattoCashflow?: number  // stima impatto in euro (indicativo)
  color: string
  actionable: boolean
}

const DEADLINES_2026: FiscalEvent[] = [
  // ── Gennaio ──
  { id: 'genn-1', date: '2026-01-16', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a dicembre 2025', tipo: 'IVA', impattoCashflow: 0, color: 'border-red-400', actionable: true },
  { id: 'genn-2', date: '2026-01-20', label: 'Intrastat mensile', description: 'Elenco Intrastat operazioni imponibili — mensile dicembre', tipo: 'IVA', color: 'border-red-300', actionable: false },
  { id: 'genn-3', date: '2026-01-31', label: 'Esterometro', description: 'Comunicazione operazioni con l\'estero — dati 2025', tipo: 'COMUNICAZIONE', color: 'border-purple-400', actionable: true },

  // ── Febbraio ──
  { id: 'feb-1', date: '2026-02-16', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a gennaio 2026', tipo: 'IVA', impattoCashflow: 0, color: 'border-red-400', actionable: true },
  { id: 'feb-2', date: '2026-02-20', label: 'Intrastat mensile', description: 'Elenco Intrastat — mensile gennaio', tipo: 'IVA', color: 'border-red-300', actionable: false },
  { id: 'feb-3', date: '2026-02-28', label: 'Certificazione Unica', description: 'CU 2025 — invio telematico (sostituti d\'imposta)', tipo: 'COMUNICAZIONE', color: 'border-purple-400', actionable: true },

  // ── Marzo ──
  { id: 'mar-1', date: '2026-03-01', label: 'Comunicazione Liquidazioni IVA', description: 'Comunicazione liquidazioni IVA periodica — 4° trim. 2025', tipo: 'IVA', color: 'border-red-400', actionable: true },
  { id: 'mar-2', date: '2026-03-16', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a febbraio 2026', tipo: 'IVA', impattoCashflow: 0, color: 'border-red-400', actionable: true },
  { id: 'mar-3', date: '2026-03-16', label: 'CU — termine ultratardivo', description: 'Certificazione Unica — invio con ravvedimento', tipo: 'COMUNICAZIONE', color: 'border-purple-400', actionable: true },
  { id: 'mar-4', date: '2026-03-20', label: 'Intrastat mensile', description: 'Elenco Intrastat — mensile febbraio', tipo: 'IVA', color: 'border-red-300', actionable: false },

  // ── Aprile ──
  { id: 'apr-1', date: '2026-04-01', label: 'Modello 770', description: 'Comunicazione dati fiscali precisone — 770/2026', tipo: 'COMUNICAZIONE', color: 'border-purple-400', actionable: true },
  { id: 'apr-2', date: '2026-04-16', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a marzo 2026', tipo: 'IVA', color: 'border-red-400', actionable: true },
  { id: 'apr-3', date: '2026-04-20', label: 'Intrastat mensile', description: 'Elenco Intrastat — mensile marzo', tipo: 'IVA', color: 'border-red-300', actionable: false },
  { id: 'apr-4', date: '2026-04-30', label: 'Esterometro', description: 'Comunicazione operazioni con l\'estero — dati trim. 1', tipo: 'COMUNICAZIONE', color: 'border-purple-400', actionable: true },

  // ── Maggio ──
  { id: 'mag-1', date: '2026-05-16', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a aprile 2026', tipo: 'IVA', color: 'border-red-400', actionable: true },
  { id: 'mag-2', date: '2026-05-20', label: 'Intrastat mensile', description: 'Elenco Intrastat — mensile aprile', tipo: 'IVA', color: 'border-red-300', actionable: false },
  { id: 'mag-3', date: '2026-05-31', label: 'Comunicazione Liquidazioni IVA', description: 'Comunicazione liquidazioni IVA — 1° trim. 2026', tipo: 'IVA', color: 'border-red-400', actionable: true },

  // ── Giugno — ACQUISTI IRPEF ──
  { id: 'giu-1', date: '2026-06-16', label: '1° Acconto IRPEF/IRES/IRAP', description: 'Primo acconto — rateizzazione possibile (40% + 20% + 20%)', tipo: 'ACCONTO', impattoCashflow: 0, color: 'border-blue-400', actionable: true },
  { id: 'giu-2', date: '2026-06-30', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a maggio 2026', tipo: 'IVA', color: 'border-red-400', actionable: true },

  // ── Luglio ──
  { id: 'lug-1', date: '2026-07-01', label: 'Esterometro', description: 'Comunicazione operazioni con l\'estero — dati trim. 2', tipo: 'COMUNICAZIONE', color: 'border-purple-400', actionable: true },
  { id: 'lug-2', date: '2026-07-16', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a giugno 2026', tipo: 'IVA', color: 'border-red-400', actionable: true },
  { id: 'lug-3', date: '2026-07-20', label: 'Intrastat mensile', description: 'Elenco Intrastat — mensile giugno + trimestrale', tipo: 'IVA', color: 'border-red-300', actionable: false },
  { id: 'lug-4', date: '2026-07-31', label: 'Comunicazione Liquidazioni IVA', description: 'Comunicazione liquidazioni IVA — 2° trim. 2026', tipo: 'IVA', color: 'border-red-400', actionable: true },

  // ── Settembre ──
  { id: 'set-1', date: '2026-09-01', label: 'Esterometro', description: 'Comunicazione operazioni con l\'estero — dati trim. 2 (posticipo)', tipo: 'COMUNICAZIONE', color: 'border-purple-400', actionable: true },
  { id: 'set-2', date: '2026-09-16', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a agosto 2026', tipo: 'IVA', color: 'border-red-400', actionable: true },
  { id: 'set-3', date: '2026-09-20', label: 'Intrastat mensile', description: 'Elenco Intrastat — mensile agosto', tipo: 'IVA', color: 'border-red-300', actionable: false },
  { id: 'set-4', date: '2026-09-30', label: 'Esterometro', description: 'Ultimo termine utile — comunicazione operazioni UE/extraUE 2° trim.', tipo: 'COMUNICAZIONE', color: 'border-purple-400', actionable: true },

  // ── Ottobre ──
  { id: 'ott-1', date: '2026-10-16', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a settembre 2026', tipo: 'IVA', color: 'border-red-400', actionable: true },
  { id: 'ott-2', date: '2026-10-20', label: 'Intrastat mensile', description: 'Elenco Intrastat — mensile settembre', tipo: 'IVA', color: 'border-red-300', actionable: false },
  { id: 'ott-3', date: '2026-10-31', label: 'Esterometro', description: 'Comunicazione liquidazioni IVA — 3° trim. 2026', tipo: 'COMUNICAZIONE', color: 'border-red-400', actionable: true },

  // ── Novembre — 2° ACCONTO ──
  { id: 'nov-1', date: '2026-11-01', label: 'Esterometro', description: 'Comunicazione operazioni con l\'estero — dati trim. 3', tipo: 'COMUNICAZIONE', color: 'border-purple-400', actionable: true },
  { id: 'nov-2', date: '2026-11-16', label: '2° Acconto IRPEF/IRES/IRAP', description: 'Secondo acconto — saldo + acconto (versamento in unica soluzione)', tipo: 'ACCONTO', impattoCashflow: 0, color: 'border-blue-400', actionable: true },
  { id: 'nov-3', date: '2026-11-30', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a ottobre 2026', tipo: 'IVA', color: 'border-red-400', actionable: true },

  // ── Dicembre ──
  { id: 'dic-1', date: '2026-12-16', label: 'IVA Mensile — versamento', description: 'Versamento IVA relativa a novembre 2026', tipo: 'IVA', color: 'border-red-400', actionable: true },
  { id: 'dic-2', date: '2026-12-20', label: 'Intrastat mensile', description: 'Elenco Intrastat — mensile novembre', tipo: 'IVA', color: 'border-red-300', actionable: false },
  { id: 'dic-3', date: '2026-12-27', label: ' IVA Annuale / Split payment', description: 'Versamento IVA.Split payment — liquidazione anno', tipo: 'IVA', impattoCashflow: 0, color: 'border-red-400', actionable: true },
]

export function getFiscalEvents(from?: string, to?: string): FiscalEvent[] {
  const now = from ? new Date(from) : new Date()
  const end = to ? new Date(to) : new Date(now.getFullYear(), 11, 31)
  return DEADLINES_2026.filter(e => {
    const d = new Date(e.date)
    return d >= now && d <= end
  })
}

export function getUpcomingEvents(days = 14): FiscalEvent[] {
  const now = new Date()
  const inDays = new Date(now); inDays.setDate(now.getDate() + days)
  return DEADLINES_2026.filter(e => {
    const d = new Date(e.date)
    return d >= now && d <= inDays
  }).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
}

export function getTipoColor(tipo: FiscalEvent['tipo']): string {
  const map: Record<FiscalEvent['tipo'], string> = {
    IVA: 'bg-red-50 text-red-700 border-red-200',
    IRPEF: 'bg-blue-50 text-blue-700 border-blue-200',
    IRAP: 'bg-purple-50 text-purple-700 border-purple-200',
    INPS: 'bg-orange-50 text-orange-700 border-orange-200',
    COMUNICAZIONE: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    SCADENZA: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    ACCONTO: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  }
  return map[tipo] || 'bg-gray-50 text-gray-700 border-gray-200'
}
