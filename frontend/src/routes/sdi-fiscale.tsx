import { useState } from 'react'
import { Card, CardContent } from '../components/ui'
import {
  ShieldCheck, Mail, Key, Send, Download,
  CheckCircle2, XCircle, Clock, AlertTriangle,
  Info, Database
} from 'lucide-react'
import { formatCurrency } from '../lib/utils'

const STEPS_SDI = [
  {
    num: 1,
    title: 'Firma Digitale',
    desc: 'La fattura XML viene firmata digitalmente con il tuo certificato. Garantisce autenticità e integrità.',
    icon: Key,
    color: 'violet',
    detail: 'Obbligatoria per legge. Firma con smartcard, token USB o firma remota.',
  },
  {
    num: 2,
    title: 'Invio al SDI',
    desc: 'La fattura firmata viene inviata al Sistema Di Interscambio dell\'Agenzia delle Entrate.',
    icon: Send,
    color: 'blue',
    detail: 'Via PEC, web service SOAP, o attraverso un intermediario accreditato.',
  },
  {
    num: 3,
    title: 'Validazione',
    desc: 'Il SDI verifica che la fattura sia nel formato corretto, che le Partite IVA siano valide, ecc.',
    icon: ShieldCheck,
    color: 'emerald',
    detail: 'Se la validazione fallisce, ricevi una Notifica di Scarto. La fattura NON viene inoltrata.',
  },
  {
    num: 4,
    title: 'Consegna al Destinatario',
    desc: 'Se valida, il SDI inoltra la fattura al destinatario (cliente) tramite PEC o codice SDI.',
    icon: Mail,
    color: 'amber',
    detail: 'Il destinatario può accettare (scadenza 15 giorni) o rifiutare (con motivazione).',
  },
  {
    num: 5,
    title: 'Notifica di Esito',
    desc: 'Ricevi comunicazione dell\'esito: EC01 (accettata), EC02 (rifiutata), EC06 (decorrenza termini).',
    icon: CheckCircle2,
    color: 'green',
    detail: 'EC01 = fattura valida e compta. EC02 = rifiutata dal cliente o dal SDI.',
  },
]

const SDI_STATI = [
  { code: 'NS1', label: 'Notifica di Scarto', desc: 'Fattura rifiutata dal SDI per errori di formato o validazione.', severity: 'error', icon: XCircle },
  { code: 'NS2', label: 'Notifica di Esito C', desc: 'Notifica di esito per mancata trasmissione via PEC.', severity: 'warning', icon: AlertTriangle },
  { code: 'EC01', label: 'Esito C — Accettata', desc: 'Fattura accettata dal destinatario. È compta.', severity: 'success', icon: CheckCircle2 },
  { code: 'EC02', label: 'Esito C — Rifiutata', desc: 'Fattura rifiutata dal destinatario (entro 15 giorni).', severity: 'error', icon: XCircle },
  { code: 'EC03', label: 'Decorrenza Termini', desc: 'Il destinatario non ha risposto entro 15 giorni. Fattura compta.', severity: 'success', icon: Clock },
  { code: 'AT', label: 'Attesa Ricezione', desc: 'La fattura è stata trasmessa al SDI ma non ancora consegnata.', severity: 'neutral', icon: Clock },
]

const MOCK_SDI_INVOICES = [
  { id: 'FT2026-0012', cliente: 'Tech Solutions S.r.l.', amount: 5200, status: 'EC01', date: '2026-03-15', direction: 'outgoing' },
  { id: 'FT2026-0011', cliente: 'GlobalTrade S.p.A.', amount: 8900, status: 'EC01', date: '2026-03-12', direction: 'outgoing' },
  { id: 'FE2026-0003', cliente: 'Fornitore XYZ S.r.l.', amount: 1850, status: 'EC01', date: '2026-03-10', direction: 'incoming' },
  { id: 'FT2026-0010', cliente: 'Campagne Web S.r.l.', amount: 3400, status: 'EC03', date: '2026-03-08', direction: 'outgoing' },
  { id: 'FT2026-0009', cliente: 'MarketingPro S.r.l.', amount: 2100, status: 'NS1', date: '2026-03-05', direction: 'outgoing' },
  { id: 'FE2026-0002', cliente: 'EnergiaPlus S.p.A.', amount: 450, status: 'EC01', date: '2026-03-02', direction: 'incoming' },
]

export function SdiFiscalPage() {
  const [activeStep, setActiveStep] = useState<number | null>(null)

  const STATO_CONFIG: Record<string, { label: string; color: string; bg: string; text: string }> = {
    EC01: { label: 'Accettata', color: 'text-emerald-700', bg: 'bg-emerald-50', text: 'bg-emerald-500' },
    EC02: { label: 'Rifiutata', color: 'text-red-700', bg: 'bg-red-50', text: 'bg-red-500' },
    EC03: { label: 'Decorrenza', color: 'text-blue-700', bg: 'bg-blue-50', text: 'bg-blue-500' },
    NS1: { label: 'Scartata', color: 'text-red-700', bg: 'bg-red-50', text: 'bg-red-500' },
    NS2: { label: 'Esito C', color: 'text-amber-700', bg: 'bg-amber-50', text: 'bg-amber-500' },
    AT: { label: 'Attesa', color: 'text-gray-700', bg: 'bg-gray-50', text: 'bg-gray-400' },
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SDI & Fiscalità</h1>
          <p className="text-gray-500 text-sm mt-1">Come funziona la fatturazione elettronica in Italia</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-full">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-semibold text-emerald-700">SDI Connesso</span>
        </div>
      </div>

      {/* Info box */}
      <div className="bg-blue-50 border border-blue-100 rounded-2xl p-5 flex gap-4">
        <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center shrink-0">
          <Info className="w-5 h-5 text-blue-600" />
        </div>
        <div>
          <h3 className="font-semibold text-blue-900 mb-1">Fattura Elettronica Obbligatoria</h3>
          <p className="text-sm text-blue-700 leading-relaxed">
            Dal 2019 tutte le fatture tra soggetti IVA in Italia devono essere trasmesse elettronicamente
            tramite il <strong>Sistema Di Interscambio (SDI)</strong>. Non basta più inviarla per email —
            il formato obbligatorio è XML (FatturaPA), firmato digitalmente.
          </p>
        </div>
      </div>

      {/* Flusso visuale */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-4">Flusso di una fattura</h2>
        <div className="relative">
          {/* Connecting line */}
          <div className="hidden lg:block absolute top-10 left-[10%] right-[10%] h-0.5 bg-gradient-to-r from-violet-200 via-blue-200 via-emerald-200 via-amber-200 to-green-200" />

          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {STEPS_SDI.map((step) => {
              const Icon = step.icon
              const colors: Record<string, { icon: string; ring: string; border: string }> = {
                violet: { icon: 'text-violet-600 bg-violet50', ring: 'ring-violet-100', border: 'border-violet-200' },
                blue: { icon: 'text-blue-600 bg-blue-50', ring: 'ring-blue-100', border: 'border-blue-200' },
                emerald: { icon: 'text-emerald-600 bg-emerald-50', ring: 'ring-emerald-100', border: 'border-emerald-200' },
                amber: { icon: 'text-amber-600 bg-amber-50', ring: 'ring-amber-100', border: 'border-amber-200' },
                green: { icon: 'text-emerald-600 bg-emerald-50', ring: 'ring-emerald-100', border: 'border-emerald-200' },
              }
              const c = colors[step.color]
              const isActive = activeStep === step.num

              return (
                <button
                  key={step.num}
                  onClick={() => setActiveStep(isActive ? null : step.num)}
                  className="relative text-left focus:outline-none"
                >
                  <div className={`bg-white rounded-2xl border transition-all duration-200 hover:shadow-md ${isActive ? `ring-2 ring-offset-2 ${c.ring} shadow-md` : 'border-gray-200 shadow-sm'}`}>
                    <div className="p-4">
                      <div className="flex items-center gap-3 mb-3">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${c.icon}`}>
                          <Icon className="w-5 h-5" />
                        </div>
                        <div className="w-7 h-7 rounded-full bg-gray-900 flex items-center justify-center shrink-0">
                          <span className="text-white text-xs font-bold">{step.num}</span>
                        </div>
                      </div>
                      <h3 className="font-semibold text-gray-900 text-sm">{step.title}</h3>
                      <p className="text-xs text-gray-500 mt-1 leading-relaxed">{step.desc}</p>

                      {isActive && (
                        <div className="mt-3 pt-3 border-t border-gray-100">
                          <p className="text-xs text-gray-600 bg-gray-50 rounded-lg p-2.5 leading-relaxed">
                            💡 {step.detail}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Requisiti + Notifiche side by side */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Requisiti SDI */}
        <Card className="border border-gray-200 shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">Cosa ti serve per il SDI</h3>
            <p className="text-xs text-gray-400 mt-0.5">Requisiti per emettere fatture elettroniche</p>
          </div>
          <CardContent className="p-5 space-y-3">
            {[
              { icon: Mail, label: 'PEC', desc: 'Posta Elettronica Certificata', cost: '~€10/anno', color: 'text-blue-600', bg: 'bg-blue-50', required: true },
              { icon: Key, label: 'Firma Digitale', desc: 'Smartcard o token USB', cost: '~€30/anno', color: 'text-violet-600', bg: 'bg-violet-50', required: true },
              { icon: Send, label: 'Canale SDI', desc: ' intermediario o PEC diretta', cost: '~€3/mese', color: 'text-emerald-600', bg: 'bg-emerald-50', required: true },
              { icon: Database, label: 'Software', desc: 'Genera XML FatturaPA', cost: 'Gratuito (FatturaMVP)', color: 'text-amber-600', bg: 'bg-amber-50', required: false },
            ].map(({ icon: Icon, label, desc, cost, color, bg, required }) => (
              <div key={label} className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
                <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center shrink-0`}>
                  <Icon className={`w-5 h-5 ${color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-gray-900">{label}</p>
                    {required && <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-600 rounded font-medium">Obbligatorio</span>}
                  </div>
                  <p className="text-xs text-gray-500">{desc}</p>
                </div>
                <span className="text-sm font-semibold text-gray-700 shrink-0">{cost}</span>
              </div>
            ))}

            <div className="pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-500">
                <strong className="text-gray-700">Totale costi fissi:</strong> ~€46-80/anno + €3/mese per il canale SDI
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Codici notifica SDI */}
        <Card className="border border-gray-200 shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">Codici Notifica SDI</h3>
            <p className="text-xs text-gray-400 mt-0.5">Come interpretare le risposte del sistema</p>
          </div>
          <CardContent className="p-5 space-y-2">
            {SDI_STATI.map((stato) => {
              const Icon = stato.icon
              const cfg = STATO_CONFIG[stato.code]
              const sev: Record<string, string> = {
                error: 'text-red-700',
                warning: 'text-amber-700',
                success: 'text-emerald-700',
                neutral: 'text-gray-600',
              }
              return (
                <div key={stato.code} className="flex items-start gap-3 p-2.5 rounded-xl hover:bg-gray-50 transition-colors">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${cfg.bg}`}>
                    <Icon className={`w-4 h-4 ${cfg.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-gray-500">{stato.code}</span>
                      <span className={`text-xs font-semibold ${sev[stato.severity]}`}>{stato.label}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{stato.desc}</p>
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>
      </div>

      {/* Ultime fatture SDI */}
      <Card className="border border-gray-200 shadow-sm">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">Storico SDI</h3>
            <p className="text-xs text-gray-400 mt-0.5">Ultime fatture trasmesse / ricevute</p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="flex items-center gap-1 px-2 py-1 bg-violet-50 text-violet-700 rounded-lg font-medium">
              <Send className="w-3 h-3" /> 4 Emesse
            </span>
            <span className="flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded-lg font-medium">
              <Download className="w-3 h-3" /> 2 Ricevute
            </span>
          </div>
        </div>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left">
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">ID</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Cliente/ fornitore</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Direzione</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Importo</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Data</th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Stato SDI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {MOCK_SDI_INVOICES.map((inv) => {
                  const cfg = STATO_CONFIG[inv.status]
                  const isIncoming = inv.direction === 'incoming'
                  return (
                    <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-5 py-3.5 font-mono text-xs font-semibold text-gray-900">{inv.id}</td>
                      <td className="px-5 py-3.5 text-sm text-gray-700">{inv.cliente}</td>
                      <td className="px-5 py-3.5">
                        <span className={`inline-flex items-center gap-1 text-xs font-semibold ${isIncoming ? 'text-blue-600' : 'text-violet-600'}`}>
                          {isIncoming ? <Download className="w-3.5 h-3.5" /> : <Send className="w-3.5 h-3.5" />}
                          {isIncoming ? 'Ricevuta' : 'Emessa'}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 font-semibold text-gray-900 tabular-nums">{formatCurrency(inv.amount)}</td>
                      <td className="px-5 py-3.5 text-xs text-gray-400">{inv.date}</td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${cfg.text}`} />
                          <span className={`text-xs font-semibold ${cfg.color}`}>{inv.status}</span>
                          <span className="text-xs text-gray-400">— {cfg.label}</span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* CTA */}
      <div className="bg-gray-900 rounded-2xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-white">Collega FatturaMVP al SDI</h3>
          <p className="text-sm text-gray-400 mt-1">
            Inserisci le tue credenziali PEC e firma digitale. Il resto lo facciamo noi.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-5 py-2.5 bg-white text-gray-900 text-sm font-semibold rounded-xl hover:bg-gray-100 transition-colors">
            Configura SDI
          </button>
          <button className="px-5 py-2.5 bg-white/10 text-white text-sm font-medium rounded-xl hover:bg-white/20 transition-colors border border-white/20">
            Maggiori info
          </button>
        </div>
      </div>
    </div>
  )
}
