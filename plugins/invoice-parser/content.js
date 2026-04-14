// Content script - runs on all pages to detect PDF invoices

console.log('FatturaMVP: Content script loaded');

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getInvoiceData') {
    // Return data for current page
    sendResponse({ ready: true });
  }
  return true;
});

// Optional: Auto-detect and highlight invoice elements
function highlightInvoices() {
  const pdfLinks = document.querySelectorAll('a[href*=".pdf"]');
  pdfLinks.forEach(link => {
    if (link.href.toLowerCase().includes('fattura') || 
        link.href.toLowerCase().includes('invoice')) {
      link.style.border = '2px dashed #2563eb';
      link.title = 'FatturaMVP: Click estrai';
    }
  });
}

// Run after page load
if (document.readyState === 'complete') {
  highlightInvoices();
} else {
  window.addEventListener('load', highlightInvoices);
}