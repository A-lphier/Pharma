import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui'
import {
  CalendarDays, Zap, Shield, Check, ChevronDown, ChevronUp, Euro, Users,
  Star, ArrowRight, TrendingUp, AlertTriangle, Clock,
} from 'lucide-react'

// ─── FAQ data ───────────────────────────────────────────────────────────────

const faqs = [
  {
    q: 'Come funziona l\'integrazione SDI?',
    a: 'FatturaMVP si collega direttamente al Sistema di Interscambio (SDI). Le tue fatture elettroniche vengono scaricate automaticamente e analizzate per estrarre scadenze, importi e stati di pagamento. Non serve nessuna configurazione manuale complessa.',
  },
  {
    q: 'Quanto tempo serve per il setup?',
    a: 'Il setup richiede circa 5 minuti. Dopo la registrazione, colleghi il tuo primo cliente o importi fatture esistenti. Il sistema è pronto e inizia subito a monitorare le scadenze e a inviarti alert intelligenti.',
  },
  {
    q: 'Posso cancellare quando voglio?',
    a: 'Assolutamente sì. Puoi cancellare la tua sottoscrizione in qualsiasi momento dall\'area billing, senza penali e senza vincoli. Non ci sono costi di uscita o tariffe nascoste.',
  },
  {
    q: 'I miei dati sono al sicuro?',
    a: 'I tuoi dati sono crittografati in transit e at rest, ospitati su server in Europa (GDPR compliant). Non condividiamo mai i tuoi dati con terze parti. L\'accesso è protetto da autenticazione JWT e audit log completi.',
  },
  {
    q: 'Cosa succede se non ho la fattura elettronica?',
    a: 'FatturaMVP funziona anche senza fattura elettronica. Puoi inserire fatture cartacee manualmente o importarle da CSV/Excel. Il sistema funziona come scadenziario e promemoria indipendentemente dal formato.',
  },
]

// ─── Features ───────────────────────────────────────────────────────────────

const features = [
  {
    icon: CalendarDays,
    title: 'Scadenziario intelligente',
    desc: 'Vedi tutte le scadenze in un colpo d\'occhio. Filtra per data, cliente o stato. Non perdere mai più una rata o una scadenza.',
  },
  {
    icon: Zap,
    title: 'Sollecito AI',
    desc: 'Il sistema sollecita al momento giusto, col tono giusto. L\'AI analizza il comportamento del cliente e sceglie il momento e le parole più efficaci per massimizzare la probabilità di incasso.',
  },
  {
    icon: Shield,
    title: 'Trust Score',
    desc: 'Sai prima chi pagherà in ritardo. Il Trust Score analizza lo storico pagamenti e ti dà un voto da 0 a 100 per ogni cliente, così puoi decidere se fidarti o no.',
  },
]

// ─── Testimonials ───────────────────────────────────────────────────────────

const testimonials = [
  {
    name: 'Marco R.',
    role: 'Consulente IT',
    text: 'Prima perdevo ore a controllare le scadenze. Ora FatturaMVP fa tutto da solo e gli incassi sono arrivati prima.',
    stars: 5,
  },
  {
    name: 'Giulia T.',
    role: 'Commercialista',
    text: 'Il sollecito AI è impressionante. I miei clienti dicono che i messaggi sembrano scritti da me, non da una macchina.',
    stars: 5,
  },
  {
    name: 'Alessandro B.',
    role: 'Art Director',
    text: 'Ho ridotto i ritardi del 60% in tre mesi. Il Trust Score mi ha fatto capire chi dovevo davvero monitorare.',
    stars: 5,
  },
]

// ─── Pricing tiers ─────────────────────────────────────────────────────────

const tiers = [
  {
    name: 'Starter',
    price: '19',
    period: '/mese',
    tagline: 'Per freelancer',
    highlighted: false,
    features: [
      'Fino a 50 fatture',
      'Scadenziario intelligente',
      'Sollecito AI (100 msg/mese)',
      'Trust Score base',
      '1 utente',
      'Email di supporto',
    ],
  },
  {
    name: 'Professional',
    price: '29',
    period: '/mese',
    tagline: 'Per micro-imprese',
    highlighted: true,
    features: [
      'Fino a 500 fatture',
      'Scadenziario intelligente',
      'Sollecito AI (illimitato)',
      'Trust Score avanzato',
      '5 utenti',
      'Dashboard analytics',
      'Integrazione SDI',
      'Priorità supporto',
    ],
  },
  {
    name: 'Studio',
    price: '79',
    period: '/mese',
    tagline: 'Per commercialisti',
    highlighted: false,
    features: [
      'Fatture illimitate',
      'Tutto di Professional',
      'Gestione multi-cliente',
      'Report avanzati',
      '20 utenti',
      'API access',
      'Dedicated account manager',
      'Onboarding personalizzato',
    ],
  },
]

// ─── ROI Calculator ────────────────────────────────────────────────────────

function ROICalculator() {
  const [revenue, setRevenue] = useState(100000)
  const [delayDays, setDelayDays] = useState(60)
  const costOfCapital = 0.05
  const frozenCapital = revenue * 0.8 * (delayDays / 365)
  const yearlyCost = frozenCapital * costOfCapital
  const targetDelay = 55
  const newFrozenCapital = revenue * 0.8 * (targetDelay / 365)
  const newYearlyCost = newFrozenCapital * costOfCapital
  const savings = yearlyCost - newYearlyCost
  const fmt = (n: number) => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n)

  return (
    <section className="py-20 bg-slate-50" id="calcolatore">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            Quanto ti costa il ritardo nei pagamenti?
          </h2>
          <p className="mt-3 text-lg text-gray-600">
            Calcola in pochi secondi quanto liquidità stai lasciando sul tavolo
          </p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8">
          <div className="mb-6">
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-gray-700">Quanto fatturi all'anno?</label>
              <span className="text-sm font-bold text-primary-600">{fmt(revenue)}</span>
            </div>
            <input type="range" min={20000} max={500000} step={5000} value={revenue} onChange={(e) => setRevenue(Number(e.target.value))}
              className="w-full h-2 bg-blue-100 rounded-lg appearance-none cursor-pointer accent-primary-600" />
            <div className="flex justify-between text-xs text-gray-400 mt-1"><span>€20k</span><span>€500k</span></div>
          </div>
          <div className="mb-8">
            <div className="flex justify-between items-center mb-2">
              <label className="text-sm font-medium text-gray-700">Giorni medi di ritardo pagamento?</label>
              <span className="text-sm font-bold text-red-600">{delayDays} gg</span>
            </div>
            <input type="range" min={15} max={180} step={5} value={delayDays} onChange={(e) => setDelayDays(Number(e.target.value))}
              className="w-full h-2 bg-red-100 rounded-lg appearance-none cursor-pointer accent-red-500" />
            <div className="flex justify-between text-xs text-gray-400 mt-1"><span>15 gg</span><span>180 gg</span></div>
          </div>
          <div className="grid sm:grid-cols-2 gap-4 mb-6">
            <div className="bg-red-50 rounded-xl p-4 border border-red-100">
              <p className="text-sm text-red-700 font-medium mb-1">Stai perdendo circa</p>
              <p className="text-2xl font-bold text-red-700">{fmt(yearlyCost)}</p>
              <p className="text-xs text-red-600 mt-1">l'anno in liquidità congelata</p>
            </div>
            <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-100">
              <p className="text-sm text-emerald-700 font-medium mb-1">Con FatturaMVP recuperi</p>
              <p className="text-2xl font-bold text-emerald-700">{fmt(savings)}</p>
              <p className="text-xs text-emerald-600 mt-1">portando il ritardo medio a {targetDelay}gg</p>
            </div>
          </div>
          <div className="text-center">
            <Link to="/register">
              <Button size="lg" className="bg-primary-600 hover:bg-primary-700">
                Scopri come <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── FAQ Accordion ─────────────────────────────────────────────────────────

function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border-b border-gray-200 last:border-0">
      <button className="w-full flex items-center justify-between py-4 text-left" onClick={() => setOpen((o) => !o)}>
        <span className="font-medium text-gray-900">{q}</span>
        {open ? <ChevronUp className="h-5 w-5 text-gray-400 flex-shrink-0" /> : <ChevronDown className="h-5 w-5 text-gray-400 flex-shrink-0" />}
      </button>
      {open && <p className="pb-4 text-gray-600 leading-relaxed">{a}</p>}
    </div>
  )
}

// ─── Animated Dashboard Preview ──────────────────────────────────────────────

function DashboardPreview() {
  const mockInvoices = [
    { name: 'Tech Solutions S.r.l.', amount: 12400, status: 'overdue', days: 12, score: 45 },
    { name: 'Studio Associato Rossi', amount: 5800, status: 'pending', days: 5, score: 78 },
    { name: 'Marco Bianchi', amount: 3200, status: 'paid', days: 0, score: 92 },
    { name: 'NewCo S.p.A.', amount: 8900, status: 'pending', days: 2, score: 65 },
    { name: 'Freelance Verdi', amount: 1500, status: 'overdue', days: 28, score: 30 },
  ]

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl overflow-hidden">
      {/* Top bar */}
      <div className="bg-gray-900 px-4 py-3 flex items-center gap-2">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-400" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
        </div>
        <div className="flex-1 bg-gray-800 rounded-md px-3 py-1 text-xs text-gray-400 text-center">
          fatturamvp.it/dashboard
        </div>
      </div>
      {/* Dashboard content */}
      <div className="p-4 space-y-3">
        {/* North star */}
        <div className="bg-gray-900 rounded-xl p-4">
          <p className="text-gray-400 text-xs font-medium uppercase tracking-wider mb-1">Da incassare</p>
          <p className="text-2xl font-bold text-white">€ 37.208</p>
          <p className="text-red-400 text-xs mt-1">1 fattura scaduta (€8.900)</p>
        </div>
        {/* Invoice rows */}
        {mockInvoices.slice(0, 4).map((inv, i) => (
          <div key={i} className="flex items-center gap-3 p-2.5 bg-gray-50 rounded-lg border border-gray-100">
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
              inv.status === 'paid' ? 'bg-emerald-100' : inv.status === 'overdue' ? 'bg-red-100' : 'bg-gray-100'
            }`}>
              {inv.status === 'paid' ? (
                <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
              ) : inv.status === 'overdue' ? (
                <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
              ) : (
                <Clock className="w-3.5 h-3.5 text-gray-400" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-800 truncate">{inv.name}</p>
              <p className="text-[10px] text-gray-400">{inv.status === 'overdue' ? `Scaduta ${inv.days}gg fa` : inv.status === 'paid' ? 'Pagata' : `Tra ${inv.days}gg`}</p>
            </div>
            <div className="text-right shrink-0">
              <p className={`text-xs font-semibold ${inv.status === 'paid' ? 'text-emerald-600' : inv.status === 'overdue' ? 'text-red-600' : 'text-gray-900'}`}>
                {new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(inv.amount)}
              </p>
              <div className={`inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
                inv.score >= 80 ? 'bg-emerald-100 text-emerald-700' : inv.score >= 60 ? 'bg-blue-100 text-blue-700' : inv.score >= 40 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'
              }`}>
                <div className={`w-1 h-1 rounded-full ${inv.score >= 80 ? 'bg-emerald-500' : inv.score >= 60 ? 'bg-blue-500' : inv.score >= 40 ? 'bg-amber-500' : 'bg-red-500'}`} />
                {inv.score}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── How it works ──────────────────────────────────────────────────────────

const steps = [
  {
    num: '01',
    title: 'Collega il tuo sistema SDI',
    desc: 'In 5 minuti connetti FatturaMVP al Sistema di Interscambio. Le tue fatture vengono scaricate e analizzate automaticamente.',
  },
  {
    num: '02',
    title: 'Vedi chi pagherà in ritardo',
    desc: 'Il Trust Score analizza lo storico di ogni cliente e ti dice chi è affidabile e chi no — prima che sia troppo tardi.',
  },
  {
    num: '03',
    title: 'Incassa senza dare fastidio',
    desc: 'L\'AI sollecita al momento giusto, col tono giusto. Tu pensi al tuo lavoro, FatturaMVP pensa agli incassi.',
  },
]

// ─── Trust badges ─────────────────────────────────────────────────────────

const trustBadges = [
  { icon: Shield, label: 'GDPR Compliant', sub: 'Server in Europa' },
  { icon: Zap, label: 'Setup 5 minuti', sub: 'Senza carta credito' },
  { icon: Users, label: '2.400+ professionisti', sub: 'In tutta Italia' },
]

// ─── Landing Page ─────────────────────────────────────────────────────────

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white font-sans">

      {/* ── Navbar ─────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
                <Euro className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold text-xl text-gray-900">FatturaMVP</span>
            </div>
            <nav className="hidden md:flex items-center gap-6 text-sm text-gray-500">
              <a href="#funzionalita" className="hover:text-gray-900 transition-colors">Funzionalità</a>
              <a href="#pricing" className="hover:text-gray-900 transition-colors">Prezzi</a>
              <a href="#calcolatore" className="hover:text-gray-900 transition-colors">Calcolatore</a>
              <a href="#faq" className="hover:text-gray-900 transition-colors">FAQ</a>
            </nav>
            <div className="flex items-center gap-3">
              <Link to="/login">
                <Button variant="ghost" size="sm" className="text-gray-600">Accedi</Button>
              </Link>
              <Link to="/register">
                <Button size="sm" className="bg-gray-900 hover:bg-gray-800 text-white">
                  Prova gratis →
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* ── HERO — Dark, Stripe-style ─────────────────────────────────── */}
      <section className="relative bg-gray-950 text-white overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-[200px] -right-[200px] w-[600px] h-[600px] bg-blue-600 rounded-full opacity-10 blur-3xl" />
          <div className="absolute -bottom-[200px] -left-[200px] w-[500px] h-[500px] bg-indigo-600 rounded-full opacity-10 blur-3xl" />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left: copy */}
            <div>
              {/* Badge */}
              <div className="inline-flex items-center gap-2 bg-white/10 border border-white/10 rounded-full px-3.5 py-1.5 text-xs font-medium text-blue-300 mb-6">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                AI-powered payment intelligence
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-[3.5rem] font-bold leading-[1.1] tracking-tight mb-6">
                Smetti di rincorrere.<br />
                <span className="text-blue-400">Inizia a incassare.</span>
              </h1>

              <p className="text-lg text-gray-400 leading-relaxed mb-8 max-w-lg">
                FatturaMVP è l'unico strumento che combina scadenziario intelligente, Trust Score e sollecito AI — per farti dormire tranquillo sapendo che i tuoi soldi stanno tornando.
              </p>

              <div className="flex flex-col sm:flex-row gap-3 mb-8">
                <Link to="/register">
                  <Button size="lg" className="bg-blue-500 hover:bg-blue-600 text-white font-semibold px-8 h-12">
                    Inizia gratis — 30gg
                  </Button>
                </Link>
                <a href="#calcolatore">
                  <Button variant="outline" size="lg" className="border-gray-700 text-gray-300 hover:bg-white/5 h-12 px-6">
                    Vedi quanto puoi risparmiare
                  </Button>
                </a>
              </div>

              <div className="flex flex-wrap items-center gap-6 text-sm text-gray-500">
                {[
                  'No carta di credito',
                  'Setup in 5 minuti',
                  'Cancella quando vuoi',
                ].map(item => (
                  <span key={item} className="flex items-center gap-1.5">
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    {item}
                  </span>
                ))}
              </div>
            </div>

            {/* Right: dashboard preview */}
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-r from-blue-600/20 to-indigo-600/20 rounded-3xl blur-xl" />
              <DashboardPreview />
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust badges ──────────────────────────────────────────────── */}
      <section className="bg-white border-b border-gray-100 py-6">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-3 gap-6">
            {trustBadges.map(({ icon: Icon, label, sub }) => (
              <div key={label} className="flex items-center gap-3 justify-center">
                <div className="w-9 h-9 bg-gray-100 rounded-xl flex items-center justify-center shrink-0">
                  <Icon className="w-4 h-4 text-gray-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{label}</p>
                  <p className="text-xs text-gray-500">{sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats bar ────────────────────────────────────────────────── */}
      <section className="bg-gray-50 border-b border-gray-100 py-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { v: '2.400+', l: 'Professionisti in Italia' },
              { v: '-55%', l: 'Ritardo medio incassi' },
              { v: '96%', l: 'Clienti soddisfatti' },
              { v: '30gg', l: 'Prova gratuita' },
            ].map(({ v, l }) => (
              <div key={l}>
                <div className="text-3xl font-bold text-gray-900 mb-1">{v}</div>
                <div className="text-sm text-gray-500">{l}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────── */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <p className="text-xs font-semibold uppercase tracking-widest text-blue-600 mb-3">Come funziona</p>
            <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
              Tre passaggi per incassare prima
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {steps.map(({ num, title, desc }) => (
              <div key={num} className="relative">
                <div className="text-6xl font-bold text-gray-100 mb-4">{num}</div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
                <p className="text-gray-600 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── ROI Calculator ──────────────────────────────────────────── */}
      <ROICalculator />

      {/* ── Features ───────────────────────────────────────────────── */}
      <section className="py-20 bg-white" id="funzionalita">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <p className="text-xs font-semibold uppercase tracking-widest text-blue-600 mb-3">Funzionalità</p>
            <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl mb-4">
              Tutto quello che ti serve per incassare prima
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Tre strumenti potenti, integrati in un unico flusso di lavoro.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {features.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="bg-gray-50 rounded-2xl p-6 border border-gray-100 hover:shadow-lg hover:border-gray-200 transition-all duration-200">
                <div className="w-11 h-11 bg-gray-900 rounded-xl flex items-center justify-center mb-5">
                  <Icon className="h-5 w-5 text-white" />
                </div>
                <h3 className="text-base font-bold text-gray-900 mb-2">{title}</h3>
                <p className="text-gray-600 leading-relaxed text-sm">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Social Proof ──────────────────────────────────────────────── */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <p className="text-xs font-semibold uppercase tracking-widest text-blue-600 mb-3">Testimonianze</p>
            <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
              Chi lo usa, non torna indietro
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map(({ name, role, text, stars }) => (
              <div key={name} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <div className="flex gap-1 mb-3">
                  {Array.from({ length: stars }).map((_, i) => (
                    <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
                  ))}
                </div>
                <p className="text-gray-700 italic mb-4 leading-relaxed text-sm">"{text}"</p>
                <div>
                  <p className="font-semibold text-gray-900 text-sm">{name}</p>
                  <p className="text-xs text-gray-500">{role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ─────────────────────────────────────────────────── */}
      <section className="py-20 bg-white" id="pricing">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <p className="text-xs font-semibold uppercase tracking-widest text-blue-600 mb-3">Prezzi</p>
            <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl mb-4">
              Scegli il piano giusto per te
            </h2>
            <p className="text-lg text-gray-600">
              Tutti i piani includono la prova gratuita di 30 giorni.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6 items-start">
            {tiers.map((tier) => (
              <div key={tier.name} className={`relative rounded-2xl p-6 flex flex-col ${
                tier.highlighted ? 'bg-gray-900 text-white shadow-xl' : 'bg-white border border-gray-200 shadow-sm'
              }`}>
                {tier.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                    PIÙ POPOLARE
                  </div>
                )}
                <div className="mb-1">
                  <h3 className={`text-lg font-bold ${tier.highlighted ? 'text-white' : 'text-gray-900'}`}>{tier.name}</h3>
                  <p className={`text-sm ${tier.highlighted ? 'text-gray-400' : 'text-gray-500'}`}>{tier.tagline}</p>
                </div>
                <div className="flex items-baseline gap-1 mb-6">
                  <span className={`text-4xl font-extrabold ${tier.highlighted ? 'text-white' : 'text-gray-900'}`}>€{tier.price}</span>
                  <span className={tier.highlighted ? 'text-gray-400' : 'text-gray-500'}>{tier.period}</span>
                </div>
                <ul className="flex flex-col gap-2.5 mb-8 flex-1">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <Check className={`h-4 w-4 flex-shrink-0 mt-0.5 ${tier.highlighted ? 'text-blue-400' : 'text-emerald-500'}`} />
                      <span className={tier.highlighted ? 'text-gray-300' : 'text-gray-600'}>{f}</span>
                    </li>
                  ))}
                </ul>
                <Link to="/register">
                  <Button variant={tier.highlighted ? 'secondary' : 'outline'}
                    className={`w-full ${tier.highlighted ? 'bg-white text-gray-900 hover:bg-gray-100' : 'border-gray-300 text-gray-700 hover:bg-gray-50'}`}>
                    Inizia gratis
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ──────────────────────────────────────────────────────── */}
      <section className="py-20 bg-gray-50" id="faq">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <p className="text-xs font-semibold uppercase tracking-widest text-blue-600 mb-3">FAQ</p>
            <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">Domande frequenti</h2>
          </div>
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 px-6">
            {faqs.map(({ q, a }) => <FAQItem key={q} q={q} a={a} />)}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ───────────────────────────────────────────────── */}
      <section className="bg-gray-900 py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Pronto a smettere di perdere soldi?
          </h2>
          <p className="text-gray-400 text-lg mb-8">
            Unisciti a oltre 2.400 professionisti che incassano prima con FatturaMVP.
          </p>
          <Link to="/register">
            <Button size="lg" className="bg-blue-500 hover:bg-blue-600 text-white font-semibold px-8 h-12">
              Inizia gratis — 30 giorni
            </Button>
          </Link>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="bg-gray-950 text-gray-500 py-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-gray-800 rounded-lg flex items-center justify-center">
                <Euro className="h-4 w-4 text-white" />
              </div>
              <span className="font-bold text-white">FatturaMVP</span>
            </div>
            <div className="flex flex-wrap items-center gap-6 text-sm">
              <a href="/privacy" className="hover:text-white transition-colors">Privacy Policy</a>

              <a href="/terms" className="hover:text-white transition-colors">Termini di servizio</a>
              <a href="/cookies" className="hover:text-white transition-colors">Cookie Policy</a>
              <a href="mailto:contatti@fatturamvp.it" className="hover:text-white transition-colors">contatti@fatturamvp.it</a>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-xs">
            © {new Date().getFullYear()} FatturaMVP. Tutti i diritti riservati.
          </div>
        </div>
      </footer>
    </div>
  )
}

