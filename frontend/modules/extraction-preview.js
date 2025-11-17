/**
 * Live Extraction Preview
 * 
 * Shows users in real-time what will be extracted from their PDF
 * as they type in the "Text to Look For" field.
 * 
 * Features:
 * - Smart paste detection (auto-splits label from value)
 * - Live search in uploaded PDF
 * - Suggestions when text not found
 * - Visual feedback (success/error states)
 */

(() => {
  let currentPdfText = null;
  let previewTimeout = null;

  function init() {
    const fieldLookForInput = document.getElementById('fieldLookForInput');
    const fieldNameInput = document.getElementById('fieldNameInput');
    
    if (!fieldLookForInput) {
      console.warn('Extraction Preview: fieldLookForInput not found - will retry when modal opens');
      // Retry when wizard modal opens
      const addFieldWizardBtn = document.getElementById('addFieldWizardBtn');
      if (addFieldWizardBtn) {
        addFieldWizardBtn.addEventListener('click', () => {
          setTimeout(init, 100); // Retry after modal renders
        }, { once: true }); // Only attach once
      }
      return;
    }
    
    // Check if already initialized
    if (fieldLookForInput.dataset.previewInitialized === 'true') {
      return;
    }
    

    // Paste event - Smart detection
    fieldLookForInput.addEventListener('paste', async (e) => {
      // Wait for paste to complete
      setTimeout(() => {
        handleSmartPaste(fieldLookForInput.value, fieldNameInput);
      }, 10);
    });

    // Input event - Live preview
    fieldLookForInput.addEventListener('input', (e) => {
      // Debounce: wait 500ms after user stops typing
      clearTimeout(previewTimeout);
      previewTimeout = setTimeout(() => {
        showLivePreview(e.target.value);
      }, 500);
    });

    // When user uploads files, extract text for preview
    window.addEventListener('filesUploaded', handleFilesUploaded);
    
    // Mark as initialized to prevent duplicate listeners
    fieldLookForInput.dataset.previewInitialized = 'true';
  }

  /**
   * Smart Paste Detection
   * Detects if user pasted "Label: Value" and auto-splits
   */
  function handleSmartPaste(pastedText, fieldNameInput) {
    if (!pastedText || pastedText.length < 3) return;

    // Pattern 1: "Label: Value" or "Label : Value"
    const colonPattern = /^([^:]+?)\s*:\s*(.+)$/;
    const match = pastedText.match(colonPattern);

    if (match) {
      const label = match[1].trim();
      const value = match[2].trim();

      // Show smart paste notification
      showSmartPasteNotification(label, value, fieldNameInput);
    }
  }

  /**
   * Show notification when smart paste is detected
   */
  function showSmartPasteNotification(label, value, fieldNameInput) {
    const preview = document.getElementById('extractionPreview');
    if (!preview) return;

    preview.style.display = 'block';
    preview.style.background = 'linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)';
    preview.style.border = '2px solid #0ea5e9';
    preview.innerHTML = `
      <div style="display: flex; align-items: start; gap: 12px;">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2.5" style="flex-shrink: 0;">
          <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
        <div style="flex: 1;">
          <div style="font-weight: 700; color: #0c4a6e; margin-bottom: 8px; font-size: 15px;">
            💡 Smart Paste Detected!
          </div>
          <div style="background: white; padding: 10px; border-radius: 6px; margin-bottom: 10px; border: 1px solid #7dd3fc;">
            <div style="font-size: 13px; color: #64748b; margin-bottom: 4px;">Will search for:</div>
            <div style="font-family: monospace; color: #0369a1; font-weight: 600; font-size: 14px;">"${escapeHtml(label)}:"</div>
          </div>
          <div style="background: white; padding: 10px; border-radius: 6px; border: 1px solid #7dd3fc;">
            <div style="font-size: 13px; color: #64748b; margin-bottom: 4px;">Expected value:</div>
            <div style="font-family: monospace; color: #059669; font-weight: 600; font-size: 14px;">"${escapeHtml(value)}"</div>
          </div>
          <button onclick="extractionPreview.applySuggestion('${escapeHtml(label)}', '${escapeHtml(label)}')" 
                  style="margin-top: 10px; padding: 8px 16px; background: #0284c7; color: white; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 13px;">
            ✓ Use "${escapeHtml(label)}" as field name
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Apply smart paste suggestion
   */
  function applySuggestion(searchText, suggestedFieldName) {
    const fieldNameInput = document.getElementById('fieldNameInput');
    const fieldLookForInput = document.getElementById('fieldLookForInput');

    // Update field name if empty
    if (fieldNameInput && !fieldNameInput.value.trim()) {
      fieldNameInput.value = suggestedFieldName;
    }

    // Update look for text (ensure it ends with colon)
    if (fieldLookForInput) {
      const cleanText = searchText.trim();
      fieldLookForInput.value = cleanText.endsWith(':') ? cleanText : cleanText + ':';
    }

    // Show live preview
    showLivePreview(fieldLookForInput.value);
  }

  /**
   * Live Preview - Shows what will be extracted
   */
  async function showLivePreview(searchText) {
    const preview = document.getElementById('extractionPreview');
    const previewLoading = document.getElementById('previewLoading');
    const previewSuccess = document.getElementById('previewSuccess');
    const previewNotFound = document.getElementById('previewNotFound');

    if (!preview || !searchText || searchText.length < 2) {
      if (preview) preview.style.display = 'none';
      return;
    }

    // Show loading state
    preview.style.display = 'block';
    preview.style.background = '#f9fafb';
    preview.style.border = '1px solid #e5e7eb';
    if (previewLoading) previewLoading.style.display = 'block';
    if (previewSuccess) previewSuccess.style.display = 'none';
    if (previewNotFound) previewNotFound.style.display = 'none';

    // Wait for PDF text
    if (!currentPdfText) {
      // No PDF uploaded yet
      hidePreview();
      return;
    }

    // Search in PDF text (simulate extraction)
    const results = searchInPdf(searchText, currentPdfText);

    // Hide loading
    if (previewLoading) previewLoading.style.display = 'none';

    if (results.found) {
      // Success state
      preview.style.background = 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)';
      preview.style.border = '2px solid #10b981';
      if (previewSuccess) {
        previewSuccess.style.display = 'block';
        const previewValue = document.getElementById('previewValue');
        const previewCount = document.getElementById('previewCount');
        
        if (previewValue) {
          previewValue.textContent = results.value || '(extracted value will appear here)';
        }
        if (previewCount) {
          // Hide the count message
          previewCount.style.display = 'none';
        }
      }
    } else {
      // Not found state
      preview.style.background = 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)';
      preview.style.border = '2px solid #f59e0b';
      if (previewNotFound) {
        previewNotFound.style.display = 'block';
        showSuggestions(searchText, currentPdfText);
      }
    }
  }

  /**
   * Search for text in PDF
   */
  function searchInPdf(searchText, pdfText) {
    if (!pdfText) return { found: false };

    // Escape special regex characters
    const escaped = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    
    // Try exact match first
    const exactRegex = new RegExp(escaped, 'gi');
    const matches = pdfText.match(exactRegex);

    if (matches && matches.length > 0) {
      // Try to extract value after the match
      const valueRegex = new RegExp(`${escaped}\\s*([^\\n]+)`, 'i');
      const valueMatch = pdfText.match(valueRegex);
      
      return {
        found: true,
        count: matches.length,
        value: valueMatch ? valueMatch[1].trim().substring(0, 100) : null,
        strategy: 'first'
      };
    }

    return { found: false };
  }

  /**
   * Show suggestions when text not found
   */
  function showSuggestions(searchText, pdfText) {
    const suggestionsDiv = document.getElementById('previewSuggestions');
    if (!suggestionsDiv) return;

    // Find similar text (fuzzy matching)
    const suggestions = findSimilarText(searchText, pdfText);

    if (suggestions.length > 0) {
      suggestionsDiv.innerHTML = `
        <div style="font-size: 13px; color: #92400e; margin-bottom: 8px;">Try these variations:</div>
        <div style="display: flex; flex-direction: column; gap: 6px;">
          ${suggestions.slice(0, 3).map(s => `
            <button onclick="extractionPreview.trySuggestion('${escapeHtml(s)}')" 
                    style="text-align: left; padding: 8px 12px; background: white; border: 1px solid #fbbf24; border-radius: 6px; cursor: pointer; font-size: 13px; color: #92400e; font-weight: 500;">
              "${escapeHtml(s)}"
            </button>
          `).join('')}
        </div>
      `;
    } else {
      suggestionsDiv.innerHTML = `
        <div style="font-size: 13px; color: #92400e;">
          <p style="margin: 0 0 8px 0;"><strong>Tips:</strong></p>
          <ul style="margin: 0; padding-left: 20px;">
            <li>Try with or without punctuation ("Total" vs "Total:")</li>
            <li>Use shorter text</li>
            <li>Copy exact text from your PDF</li>
          </ul>
        </div>
      `;
    }
  }

  /**
   * Find similar text using fuzzy matching
   */
  function findSimilarText(searchText, pdfText) {
    const search = searchText.toLowerCase();
    const lines = pdfText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    const suggestions = [];

    for (const line of lines) {
      const lower = line.toLowerCase();
      
      // Check if line contains any word from search text
      const searchWords = search.split(/\s+/);
      for (const word of searchWords) {
        if (word.length >= 3 && lower.includes(word)) {
          // Extract potential label (text before colon or first few words)
          const colonIndex = line.indexOf(':');
          if (colonIndex > 0 && colonIndex < 50) {
            const label = line.substring(0, colonIndex + 1);
            if (!suggestions.includes(label) && label.toLowerCase().includes(word)) {
              suggestions.push(label);
            }
          } else {
            // No colon, take first 3-5 words
            const words = line.split(/\s+/).slice(0, 4).join(' ');
            if (!suggestions.includes(words) && words.length > 3) {
              suggestions.push(words);
            }
          }
        }
      }

      if (suggestions.length >= 5) break;
    }

    return suggestions;
  }

  /**
   * Try a suggested search term
   */
  function trySuggestion(suggestion) {
    const fieldLookForInput = document.getElementById('fieldLookForInput');
    if (fieldLookForInput) {
      fieldLookForInput.value = suggestion;
      showLivePreview(suggestion);
    }
  }

  /**
   * Hide preview
   */
  function hidePreview() {
    const preview = document.getElementById('extractionPreview');
    if (preview) preview.style.display = 'none';
  }

  /**
   * Handle uploaded files - extract text for preview
   */
  async function handleFilesUploaded(event) {
    const files = event.detail?.files;
    if (!files || files.length === 0) {
      console.warn('No files in upload event');
      return;
    }

    // Take first PDF for preview
    const firstPdf = files.find(f => f.name.toLowerCase().endsWith('.pdf'));
    if (!firstPdf) {
      console.warn('No PDF file found in uploaded files');
      return;
    }


    try {
      // Extract text from first page for preview
      const formData = new FormData();
      formData.append('file', firstPdf);

      const response = await fetch('/api/preview-pdf-text', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        currentPdfText = data.text;
      } else {
        console.error('Failed to extract PDF text:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Failed to load PDF for preview:', error);
    }
  }

  /**
   * Escape HTML
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Expose public API
  window.extractionPreview = {
    applySuggestion,
    trySuggestion,
    init
  };

  // Auto-init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
