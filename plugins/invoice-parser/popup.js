// Popup script for FatturaMVP Invoice Parser

let extractedData = null;
let history = [];
let currentEngine = 'ai';
const API_CONFIG = {
  gemini: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent',
  openai: 'https://api.openai.com/v1/chat/completions',
  anthropic: 'https://api.anthropic.com/v1/messages'
};

const PDFJS = window.pdfjsLib;
PDFJS.GlobalWorkerOptions.workerSrc = chrome.runtime.getURL('lib/pdf.worker.js');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  loadHistory();
  setupEventListeners();
});

function setupEventListeners() {
  // Tab switching
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });
  
  // Engine toggle
  document.querySelectorAll('.engine-btn').forEach(btn => {
    btn.addEventListener('click', () => setEngine(btn.dataset.engine));
  });
  
  // File drop zone
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  
  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', handleFileDrop);
  fileInput.addEventListener('change', handleFileSelect);
  
  // Page scan button
  document.getElementById('pageScanBtn').addEventListener('click', scanCurrentPage);
  
  // Action buttons
  document.getElementById('saveBtn').addEventListener('click', saveInvoice);
  document.getElementById('clearBtn').addEventListener('click', clearData);
  document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
}

function switchTab(tabId) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  
  document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');
  document.getElementById(`tab-${tabId}`).classList.add('active');
}

function setEngine(engine) {
  currentEngine = engine;
  document.querySelectorAll('.engine-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.engine-btn[data-engine="${engine}"]`).classList.add('active');
  
  const dropIcon = document.getElementById('dropIcon');
  const dropText = document.getElementById('dropText');
  const dropSub = document.getElementById('dropSub');
  const fileInput = document.getElementById('fileInput');
  
  if (engine === 'ai') {
    dropIcon.textContent = '🤖';
    dropText.textContent = 'Trascina file PDF o immagine';
    dropSub.textContent = 'Estrazione AI avanzata';
    fileInput.accept = '.pdf,.jpg,.jpeg,.png,.webp';
  } else if (engine === 'pdf') {
    dropIcon.textContent = '📄';
    dropText.textContent = 'Trascina file PDF';
    dropSub.textContent = 'Estrazione testo nativa';
    fileInput.accept = '.pdf';
  } else if (engine === 'ocr') {
    dropIcon.textContent = '🔤';
    dropText.textContent = 'Trascina PDF scansionato o immagine';
    dropSub.textContent = 'OCR locale (Tesseract)';
    fileInput.accept = '.pdf,.jpg,.jpeg,.png,.webp';
  }
}

// ============= File Handling =============

function handleFileDrop(e) {
  e.preventDefault();
  document.getElementById('dropZone').classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  processFile(file);
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) processFile(file);
}

async function processFile(file) {
  if (!file) return;
  
  const isImage = file.type.startsWith('image/');
  const isPDF = file.type === 'application/pdf';
  
  if (!isImage && !isPDF) {
    showStatus('❌ Formato non supportato', 'error');
    return;
  }
  
  showStatus('⏳ Elaboro il file...', 'loading');
  showProgress(10);
  
  try {
    if (currentEngine === 'ai') {
      await processWithAI(file);
    } else if (currentEngine === 'pdf') {
      await processWithPDF(file);
    } else if (currentEngine === 'ocr') {
      await processWithOCR(file);
    }
  } catch (err) {
    console.error('Processing error:', err);
    showStatus('❌ Errore: ' + err.message, 'error');
  }
}

// ============= AI Processing =============

async function processWithAI(file) {
  showStatus('🤖 Estraggo con AI...', 'loading');
  showProgress(20);
  
  const apiKey = localStorage.getItem('fatturamvp_ai_key');
  const engine = localStorage.getItem('fatturamvp_ai_engine') || 'gemini';
  
  if (!apiKey) {
    showStatus('⚠️ API Key mancante. Configurala nelle impostazioni.', 'error');
    return;
  }
  
  // Convert file to base64
  const base64 = await fileToBase64(file);
  showProgress(40);
  
  const prompt = `Sei un assistente specializzato nell'estrazione dati da fatture italiane.

Estrai i seguenti campi dalla fattura:
- numero: Numero fattura (es. "FATT 2024/001")
- data: Data fattura in formato DD/MM/YYYY
- fornitore: Nome del fornitore/ente emittente
- totale: Importo totale in euro (solo numero, es. "150.00")
- piva: Partita IVA (11 cifre)
- descrizione: Eventuale descrizione

Rispondi SOLO con un oggetto JSON valido, senza markdown:
{"numero":"...", "data":"...", "fornitore":"...", "totale":"...", "piva":"...", "descrizione":"..."}`;

  let result;
  
  if (engine === 'gemini') {
    result = await callGemini(base64, file.type, prompt, apiKey);
  } else if (engine === 'openai') {
    result = await callOpenAI(base64, file.type, prompt, apiKey);
  } else if (engine === 'anthropic') {
    result = await callAnthropic(base64, file.type, prompt, apiKey);
  }
  
  showProgress(90);
  
  if (result) {
    extractedData = { ...result, found: true, engine: 'ai' };
    showStatus('✅ Dati estratti con AI!', 'success');
    displayExtractedData();
  } else {
    showStatus('❌ Errore nell\'estrazione AI', 'error');
  }
}

async function callGemini(base64, mimeType, prompt, apiKey) {
  const url = `${API_CONFIG.gemini}?key=${apiKey}`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{
        parts: [
          { text: prompt },
          { inline_data: { mime_type: mimeType, data: base64 } }
        ]
      }],
      generationConfig: {
        temperature: 0.1,
        maxOutputTokens: 1000
      }
    })
  });
  
  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Gemini API error: ${err}`);
  }
  
  const data = await response.json();
  const text = data.candidates[0].content.parts[0].text;
  
  // Parse JSON from response
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    return JSON.parse(jsonMatch[0]);
  }
  return null;
}

async function callOpenAI(base64, mimeType, prompt, apiKey) {
  const url = API_CONFIG.openai;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: 'gpt-4o',
      messages: [
        { role: 'user', content: [
          { type: 'text', text: prompt },
          { type: 'image_url', image_url: { url: `data:${mimeType};base64,${base64}` } }
        ]}
      ],
      max_tokens: 1000
    })
  });
  
  if (!response.ok) throw new Error('OpenAI API error');
  
  const data = await response.json();
  const text = data.choices[0].message.content;
  
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) return JSON.parse(jsonMatch[0]);
  return null;
}

async function callAnthropic(base64, mimeType, prompt, apiKey) {
  const url = API_CONFIG.anthropic;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01'
    },
    body: JSON.stringify({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 1000,
      messages: [
        { role: 'user', content: [
          { type: 'text', text: prompt },
          { type: 'image', source: { type: 'base64', media_type: mimeType, data: base64 } }
        ]}
      ]
    })
  });
  
  if (!response.ok) throw new Error('Anthropic API error');
  
  const data = await response.json();
  const text = data.content[0].text;
  
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) return JSON.parse(jsonMatch[0]);
  return null;
}

// ============= PDF Processing =============

async function processWithPDF(file) {
  showStatus('📄 Leggo il PDF...', 'loading');
  showProgress(20);
  
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await PDFJS.getDocument({ data: arrayBuffer }).promise;
  
  let fullText = '';
  const totalPages = pdf.numPages;
  
  for (let i = 1; i <= totalPages; i++) {
    showProgress(20 + (70 * i / totalPages));
    const page = await pdf.getPage(i);
    const textContent = await page.getTextContent();
    const pageText = textContent.items.map(item => item.str).join(' ');
    fullText += pageText + '\n';
  }
  
  extractedData = { ...parseInvoiceText(fullText), found: true, engine: 'pdf' };
  showProgress(100);
  
  if (extractedData.number || extractedData.fornitore) {
    showStatus('✅ Dati estratti!', 'success');
    displayExtractedData();
  } else {
    showStatus('⚠️ Dati non riconosciuti. Prova AI.', 'error');
  }
}

// ============= OCR Processing =============

async function processWithOCR(file) {
  showStatus('🔤 OCR in corso...', 'loading');
  showProgress(20);
  
  const Tesseract = window.Tesseract;
  
  const result = await Tesseract.recognize(file, 'ita', {
    logger: (m) => {
      if (m.status === 'recognizing text') {
        showProgress(20 + Math.round(m.progress * 70));
      }
    }
  });
  
  extractedData = { ...parseInvoiceText(result.data.text), found: true, engine: 'ocr' };
  showProgress(100);
  
  if (extractedData.number || extractedData.fornitore) {
    showStatus('✅ Dati estratti con OCR!', 'success');
    displayExtractedData();
  } else {
    showStatus('⚠️ Dati non riconosciuti. Prova AI.', 'error');
  }
}

// ============= Helpers =============

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function parseInvoiceText(text) {
  const result = {};
  
  const patterns = {
    numero: [/fattura\s*n[°.]?\s*([A-Z0-9\-\/]+)/i, /n[\s:]*([A-Z0-9]{4,20})/i],
    data: [/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})/],
    totale: [/totale[:\s]*[€]?\s*([\d.,]+)/i, /€\s*([\d.,]+)/],
    fornitore: [/fornitore[:\s]*([A-Z][^\n]{3,60})/i, /^([A-Z][A-Za-z\s&]+(?:S\.?R\.?L\.?|S\.?p\.?A\.?)?)/im],
    piva: [/IVA[:\s]*(\d+)/i, /(?:P\.?I\.?)\s*([\d]{11})/i]
  };
  
  for (const [key, regexes] of Object.entries(patterns)) {
    for (const regex of regexes) {
      const match = text.match(regex);
      if (match) {
        if (key === 'data') {
          result[key] = `${match[1]}/${match[2]}/${match[3]}`;
        } else if (key === 'totale') {
          result[key] = parseFloat(match[1].replace(',', '.')).toFixed(2);
        } else {
          result[key] = match[1].trim();
        }
        break;
      }
    }
  }
  
  return result;
}

// ============= Page Scanning =============

async function scanCurrentPage() {
  showStatus('🔍 Analizzo la pagina...', 'loading');
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractPageData
    });
    
    extractedData = { ...results[0].result, found: true };
    
    if (extractedData.number || extractedData.fornitore) {
      showStatus('✅ Dati estratti!', 'success');
      displayExtractedData();
    } else {
      showStatus('❌ Nessun dato trovato.', 'error');
    }
  } catch (err) {
    showStatus('❌ Errore: ' + err.message, 'error');
  }
}

function extractPageData() {
  const text = document.body.innerText;
  const result = {};
  
  const numberMatch = text.match(/fattura\s*n[°.]?\s*([A-Z0-9\-\/]+)/i);
  if (numberMatch) result.numero = numberMatch[1];
  
  const dateMatch = text.match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})/);
  if (dateMatch) result.data = `${dateMatch[1]}/${dateMatch[2]}/${dateMatch[3]}`;
  
  const totalMatch = text.match(/totale[:\s]*[€]?\s*([\d.,]+)/i);
  if (totalMatch) result.totale = parseFloat(totalMatch[1].replace(',', '.')).toFixed(2);
  
  const supplierMatch = text.match(/fornitore[:\s]*([A-Z][^\n]{3,50})/i);
  if (supplierMatch) result.fornitore = supplierMatch[1].trim();
  
  result.found = !!(result.numero || (result.fornitore && result.totale));
  return result;
}

// ============= UI =============

function displayExtractedData() {
  const dataPreview = document.getElementById('dataPreview');
  const dataContent = document.getElementById('dataContent');
  const engineBadge = document.getElementById('engineBadge');
  
  if (extractedData.engine === 'ai') {
    engineBadge.className = 'engine-badge ai';
    engineBadge.textContent = 'AI';
  } else if (extractedData.engine === 'ocr') {
    engineBadge.className = 'engine-badge ocr';
    engineBadge.textContent = 'OCR';
  } else {
    engineBadge.className = 'engine-badge';
    engineBadge.textContent = 'PDF';
  }
  
  const fieldMap = {
    editNumero: extractedData.numero || '',
    editData: extractedData.data || '',
    editFornitore: extractedData.fornitore || '',
    editTotale: extractedData.totale || '0.00',
    editPiva: extractedData.piva || ''
  };
  
  dataContent.innerHTML = `
    <div class="data-row"><span class="data-label">Numero</span><input class="data-value editable" id="editNumero" value="${fieldMap.editNumero}"></div>
    <div class="data-row"><span class="data-label">Data</span><input class="data-value editable" id="editData" value="${fieldMap.editData}"></div>
    <div class="data-row"><span class="data-label">Fornitore</span><input class="data-value editable" id="editFornitore" value="${fieldMap.editFornitore}"></div>
    <div class="data-row"><span class="data-label">Totale</span><input class="data-value editable" id="editTotale" value="${fieldMap.editTotale}"></div>
    <div class="data-row"><span class="data-label">P.IVA</span><input class="data-value editable" id="editPiva" value="${fieldMap.editPiva}"></div>
    <div class="data-row"><span class="data-label">Descrizione</span><input class="data-value editable" id="editDescrizione" value="${extractedData.descrizione || ''}"></div>
  `;
  
  dataPreview.classList.add('visible');
}

function showStatus(message, type) {
  const status = document.getElementById('status');
  status.className = `status ${type}`;
  status.textContent = message;
  status.style.display = 'block';
}

function showProgress(percent) {
  const progressBar = document.getElementById('progressBar');
  const progressFill = document.getElementById('progressFill');
  progressBar.classList.add('visible');
  progressFill.style.width = `${percent}%`;
}

function clearData() {
  extractedData = null;
  document.getElementById('dataPreview').classList.remove('visible');
  document.getElementById('status').style.display = 'none';
  document.getElementById('progressBar').classList.remove('visible');
}

// ============= Save =============

async function saveInvoice() {
  if (!extractedData) return;
  
  extractedData.numero = document.getElementById('editNumero').value;
  extractedData.data = document.getElementById('editData').value;
  extractedData.fornitore = document.getElementById('editFornitore').value;
  extractedData.totale = document.getElementById('editTotale').value;
  extractedData.piva = document.getElementById('editPiva').value;
  extractedData.descrizione = document.getElementById('editDescrizione').value;
  
  history.unshift({ ...extractedData, savedAt: new Date().toISOString() });
  saveHistory();
  
  const apiEndpoint = localStorage.getItem('fatturamvp_api_endpoint') || 'http://localhost:8000';
  const apiKey = localStorage.getItem('fatturamvp_api_key');
  
  try {
    const response = await fetch(`${apiEndpoint}/api/invoices`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {})
      },
      body: JSON.stringify({
        invoice_number: extractedData.numero,
        date: extractedData.data,
        supplier_name: extractedData.fornitore,
        total: parseFloat(extractedData.totale) || 0,
        tax_id: extractedData.piva,
        status: 'pending',
        description: extractedData.descrizione || `Importato con ${extractedData.engine}`
      })
    });
    
    if (response.ok) {
      showStatus('✅ Salvato e importato!', 'success');
    } else throw new Error('API error');
  } catch (err) {
    showStatus('💾 Salvato in locale', 'success');
    switchTab('history');
  }
}

// ============= History =============

function loadHistory() {
  const saved = localStorage.getItem('fatturamvp_history');
  if (saved) history = JSON.parse(saved);
  renderHistory();
}

function saveHistory() {
  localStorage.setItem('fatturamvp_history', JSON.stringify(history.slice(0, 50)));
}

function renderHistory() {
  const container = document.getElementById('historyList');
  if (history.length === 0) {
    container.innerHTML = '<p style="text-align:center;color:#94a3b8;font-size:12px;padding:20px;">Nessuna fattura salvata</p>';
    return;
  }
  
  container.innerHTML = history.map((item, idx) => `
    <div class="history-item" onclick="loadFromHistory(${idx})">
      <span class="history-item-number">${item.numero || 'N. ' + (idx+1)}</span>
      <span class="history-item-amount">€ ${item.totale || '0.00'}</span>
      <div class="history-item-date">${item.fornitore || 'Fornitore'} • ${item.data || '-'}</div>
    </div>
  `).join('');
}

window.loadFromHistory = function(idx) {
  extractedData = history[idx];
  displayExtractedData();
  switchTab('extract');
  showStatus('📋 Caricato da storico', 'success');
};

// ============= Settings =============

function loadSettings() {
  const aiEngine = localStorage.getItem('fatturamvp_ai_engine');
  const aiKey = localStorage.getItem('fatturamvp_ai_key');
  const endpoint = localStorage.getItem('fatturamvp_api_endpoint');
  const apiKey = localStorage.getItem('fatturamvp_api_key');
  
  if (aiEngine) document.getElementById('aiEngine').value = aiEngine;
  if (aiKey) document.getElementById('aiApiKey').value = aiKey;
  if (endpoint) document.getElementById('apiEndpoint').value = endpoint;
  if (apiKey) document.getElementById('apiKey').value = apiKey;
}

function saveSettings() {
  localStorage.setItem('fatturamvp_ai_engine', document.getElementById('aiEngine').value);
  localStorage.setItem('fatturamvp_ai_key', document.getElementById('aiApiKey').value);
  localStorage.setItem('fatturamvp_api_endpoint', document.getElementById('apiEndpoint').value);
  localStorage.setItem('fatturamvp_api_key', document.getElementById('apiKey').value);
  showStatus('✅ Impostazioni salvate', 'success');
}