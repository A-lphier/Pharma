// Background service worker for FatturaMVP Invoice Parser

chrome.runtime.onInstalled.addListener(() => {
  console.log('FatturaMVP Invoice Parser installed');
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'parsePDF') {
    // In a real implementation, this would use PDF.js to parse
    sendResponse({ success: true, data: request.data });
  }
  return true;
});