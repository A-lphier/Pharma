# FatturaMVP Invoice Parser Plugin v2.0

Browser extension (Chrome/Edge) per estrarre dati da fatture PDF/immagini usando AI.

## 🚀 Quick Start

### Installazione
1. Apri `chrome://extensions/`
2. Attiva **Modalità sviluppatore**
3. Clicca **Carica estensione non compressa**
4. Seleziona `plugins/invoice-parser`

### Configurazione AI
1. Vai su tab **⚙️ Impostazioni**
2. Scegli motore AI (Gemini, OpenAI, Anthropic)
3. Inserisci la tua API Key
4. Salva

#### Get API Key gratis:
- **Gemini**: https://aistudio.google.com/app/apikey (gratuito, 15 req/min)
- **OpenAI**: https://platform.openai.com/api-keys (credito richiesto)
- **Anthropic**: https://console.anthropic.com/ (credito richiesto)

## 📁 Struttura

```
invoice-parser/
├── manifest.json      # Manifest V3
├── popup.html         # UI con 3 tabs
├── popup.js           # Logica + AI integration
├── content.js         # Content script
├── lib/
│   ├── pdf.js         # PDF.js (320KB)
│   └── pdf.worker.js  # PDF.js worker (1MB)
└── icons/
```

## 🔧 Motori di Estrazione

| Motore | Velocità | Qualità | Costo |
|--------|----------|---------|-------|
| **🤖 AI** (default) | 5-15s | ⭐⭐⭐⭐⭐ | Vari |
| **📄 PDF** | 1-3s | ⭐⭐⭐ | Gratuito |
| **🔤 OCR** | 30-90s | ⭐⭐ | Gratuito |

### AI Support
- **Google Gemini 2.0 Flash** — ✅ Consigliato (gratuito)
- **OpenAI GPT-4o** — ✅ Supportato
- **Anthropic Claude 3.5** — ✅ Supportato

## ⚡ Funzionamento

1. **Trascina** un file PDF o immagine nel drop zone
2. **Seleziona** il motore (AI, PDF, OCR)
3. **Elabora** — L'AI estrae i dati in 5-15 secondi
4. **Modifica** i campi se necessario
5. **Salva** — Invia a FatturaMVP API o salva in locale

## 📋 Campi Estratti

- Numero fattura
- Data (DD/MM/YYYY)
- Fornitore
- Totale (€)
- P.IVA
- Descrizione

## ⚠️ Note

- AI è molto più preciso su PDF scansionati/foto
- Gemini Flash è gratuito e consigliato
- Necessita HTTPS per chiamate API (eccetto localhost)