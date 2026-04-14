/**
 * Motore Deductibility Advisor — Regole fiscali italiane 2026
 *
 * Combina: IRPEF/IRES deducibilità + IVA detraibilità + Split payment + Reverse charge
 * Basato su: DPR 633/72, TUIR artt. 54-109, Legge 190/2014 (forfettario)
 */

// ── Tipi ──────────────────────────────────────────────────────────────────

export type DeductStatus = 'full' | 'partial' | 'none' | 'unknown'

export interface DeductResult {
  status: DeductStatus
  ivaDetraibile: boolean
  ivaDetraibilePct: number        // 0 | 40 | 50 | 80 | 100
  irpefDeduzionePct: number       // 0-100
  categoria: string               // es. "Autovettura", "Hotel", "Strumenti"
  warning?: string                // es. "Reverse charge edilizia"
  norma?: string                  // es. "Art. 164 TUIR c.1"
  message: string                 // breve spiegazione human-readable
}

// ── Keyword mapping → categorie fiscali ────────────────────────────────────

const CATEGORY_RULES: Array<{
  keywords: string[]
  deductResult: Omit<DeductResult, 'message'>
}> = [
  // ── Autovetture (Art. 164 TUIR) ──
  {
    keywords: ['autovettura', 'automobile', 'veicolo', 'car', 'auto', 'furgone', 'monovolume', 'suv', 'SUV'],
    deductResult: {
      status: 'partial',
      ivaDetraibile: true,
      ivaDetraibilePct: 40,
      irpefDeduzionePct: 20,
      categoria: 'Autovettura',
      warning: 'Deduzione limitata al 20% — verifica uso strutturato',
      norma: 'Art. 164 c.1 TUIR + Art. 19-bis DPR 633/72',
    },
  },
  // ── Immobili / Edilizia ──
  {
    keywords: ['materiale edile', 'cemento', 'laterizio', 'mattoni', 'pavimentazione', 'infissi', 'tetto', 'cantieri', 'restauro', 'ristrutturazione'],
    deductResult: {
      status: 'full',
      ivaDetraibile: true,
      ivaDetraibilePct: 100,
      irpefDeduzionePct: 100,
      categoria: 'Immobili/Cantieri',
      warning: 'Reverse charge — obbligo di inversione contabile',
      norma: 'Art. 17 c.6 lett. a-ter DPR 633/72',
    },
  },
  // ── Smartphone / Tablet ──
  {
    keywords: ['smartphone', 'cellulare', 'telefono', 'tablet', 'iPhone', 'Samsung', 'iPad'],
    deductResult: {
      status: 'partial',
      ivaDetraibile: true,
      ivaDetraibilePct: 50,
      irpefDeduzionePct: 50,
      categoria: 'Telefonia',
      warning: 'Smartphone: deduzione 50% se strumentale',
      norma: 'Art. 54-bis TUIR + Art. 19 DPR 633/72',
    },
  },
  // ── Alberghi / Ristoranti ──
  {
    keywords: ['hotel', 'albergo', 'ristorante', 'bar', 'pensione', 'b&b', 'B&B', 'vitto', 'pernottamento', 'pranzo', 'cena'],
    deductResult: {
      status: 'partial',
      ivaDetraibile: true,
      ivaDetraibilePct: 100,
      irpefDeduzionePct: 75,
      categoria: 'Vitto/Alloggio',
      warning: 'Deduzione vitto 75% — massimale €180/giorno (dipendenti)',
      norma: 'Art. 95 c.3 TUIR',
    },
  },
  // ── Cessione oro / Rottami ──
  {
    keywords: ['oro', 'rottami', 'metalli', 'rame', 'alluminio', 'ferro', 'acciaio'],
    deductResult: {
      status: 'full',
      ivaDetraibile: false,
      ivaDetraibilePct: 0,
      irpefDeduzionePct: 100,
      categoria: 'Cessione beni usati',
      warning: 'Reverse charge — IVA non applicabile',
      norma: 'Art. 17 c.6 lett. c-quinquies DPR 633/72',
    },
  },
  // ── Energia / Elettricità ──
  {
    keywords: ['energia elettrica', 'elettricità', 'luce', 'kWh', 'corrente', 'gas', 'metano', 'energia'],
    deductResult: {
      status: 'full',
      ivaDetraibile: true,
      ivaDetraibilePct: 100,
      irpefDeduzionePct: 100,
      categoria: 'Utenze',
      norma: 'Art. 19 DPR 633/72',
    },
  },
  // ── Consulenze / Professionisti ──
  {
    keywords: ['consulenza', 'parere', 'avvocato', 'notaio', 'commercialista', 'professionista', 'incarico professionale'],
    deductResult: {
      status: 'full',
      ivaDetraibile: true,
      ivaDetraibilePct: 100,
      irpefDeduzionePct: 100,
      categoria: 'Consulenza professionale',
      norma: 'Art. 54 TUIR',
    },
  },
  // ── Software / SaaS ──
  {
    keywords: ['software', 'licenza', 'saas', 'cloud', 'abbonamento', 'subscription', 'app', 'applicativo'],
    deductResult: {
      status: 'full',
      ivaDetraibile: true,
      ivaDetraibilePct: 100,
      irpefDeduzionePct: 100,
      categoria: 'Digitale/Software',
      norma: 'Art. 54 TUIR — spese strumentali',
    },
  },
  // ── Generic deductible (catch-all for common Italian business expenses) ──
  {
    keywords: ['servizio', 'servizi', 'assistenza', 'manutenzione', 'setup', 'implementazione', 'installazione', 'configurazione', 'progettazione', 'consulenza', 'parere', 'prestazione', 'lavoro', 'bonifico', 'commissione', 'fee', 'onorario', 'compenso'],
    deductResult: {
      status: 'full',
      ivaDetraibile: true,
      ivaDetraibilePct: 100,
      irpefDeduzionePct: 100,
      categoria: 'Servizio professionale',
      norma: 'Art. 54 TUIR',
    },
  },
  // ── Omaggi ──
  {
    keywords: ['omaggio', 'regalo', 'Samples', 'campione', 'gratis', ' omaggio'],
    deductResult: {
      status: 'none',
      ivaDetraibile: false,
      ivaDetraibilePct: 0,
      irpefDeduzionePct: 0,
      categoria: 'Omaggi',
      warning: 'Nessuna deduzione su omaggi — neanche IVA',
      norma: 'Art. 108 c.2 TUIR + Art. 19 c.2 DPR 633/72',
    },
  },
  // ── Auto a noleggio ──
  {
    keywords: ['noleggio', 'leasing', 'rent', 'noleggio auto', 'leasing auto'],
    deductResult: {
      status: 'partial',
      ivaDetraibile: true,
      ivaDetraibilePct: 40,
      irpefDeduzionePct: 80,
      categoria: 'Noleggio/Leasing',
      warning: 'Noleggio lungo: stessi limiti autovettura',
      norma: 'Art. 164 c.1 TUIR',
    },
  },
  // ── Cancelleria / Ufficio ──
  {
    keywords: ['cancelleria', 'carta', 'penne', 'ufficio', 'stampante', 'toner', 'cartucce', 'ufficio'],
    deductResult: {
      status: 'full',
      ivaDetraibile: true,
      ivaDetraibilePct: 100,
      irpefDeduzionePct: 100,
      categoria: 'Cancelleria/Ufficio',
      norma: 'Art. 54 TUIR',
    },
  },
  // ── Pubblicità ──
  {
    keywords: ['pubblicità', 'advertising', 'campagna', 'marketing', 'promozione', ' spot', 'inserzione'],
    deductResult: {
      status: 'full',
      ivaDetraibile: true,
      ivaDetraibilePct: 100,
      irpefDeduzionePct: 100,
      categoria: 'Pubblicità',
      norma: 'Art. 54 c.2 TUIR',
    },
  },
  // ── Formazione / Corsi ──
  {
    keywords: ['corso', 'formazione', 'aggiornamento', 'scuola', 'università', 'master', 'certificazione', 'training'],
    deductResult: {
      status: 'full',
      ivaDetraibile: true,
      ivaDetraibilePct: 100,
      irpefDeduzionePct: 100,
      categoria: 'Formazione',
      warning: 'Verifica che il corso sia deducibile (materia attinente)',
      norma: 'Art. 54 c.5 TUIR + L. 4.0',
    },
  },
]

// ── Funzione principale ────────────────────────────────────────────────────

/**
 * Analizza una descrizione fattura e ritorna il risultato di deducibilità.
 */
export function analyzeDeductibility(description: string): DeductResult {
  const lower = description.toLowerCase()

  for (const rule of CATEGORY_RULES) {
    const matched = rule.keywords.some(kw => lower.includes(kw.toLowerCase()))
    if (matched) {
      const result: DeductResult = {
        ...rule.deductResult,
        message: buildMessage(rule.deductResult),
      }
      return result
    }
  }

  // Default: sconosciuto — potrebbe essere deducibile
  return {
    status: 'full',
    ivaDetraibile: true,
    ivaDetraibilePct: 100,
    irpefDeduzionePct: 100,
    categoria: 'Generico',
    message: 'Completamente deducibile — categoria non specifica',
  }
}

function buildMessage(r: Omit<DeductResult, 'message'>): string {
  if (r.status === 'full') {
    return `Completamente deducibile — ${r.categoria}`
  }
  if (r.status === 'partial') {
    return `Parzialmente deducibile: IRPEF ${r.irpefDeduzionePct}% · IVA ${r.ivaDetraibilePct}% — ${r.categoria}`
  }
  if (r.status === 'none') {
    return `Indeducibile — ${r.categoria}`
  }
  return `Deducibilità da verificare`
}

// ── Badge helpers ────────────────────────────────────────────────────────────

export const DEDUCT_ICONS: Record<DeductStatus, string> = {
  full: '✅',
  partial: '⚠️',
  none: '❌',
  unknown: '❓',
}

export const DEDUCT_COLORS: Record<DeductStatus, string> = {
  full: 'bg-green-100 text-green-800 border-green-200',
  partial: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  none: 'bg-red-100 text-red-800 border-red-200',
  unknown: 'bg-gray-100 text-gray-700 border-gray-200',
}
