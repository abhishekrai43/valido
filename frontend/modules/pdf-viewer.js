/**
 * PDF Viewer with Text Selection
 * 
 * Displays uploaded PDF and allows users to click/select text
 * to automatically populate extraction fields.
 * 
 * Uses PDF.js library for rendering and text layer extraction.
 */

(() => {
  let pdfDoc = null;
  let pageNum = 1;
  let pageRendering = false;
  let pageNumPending = null;
  let scale = 1.5;
  let currentPdfFile = null;
  let selectedText = '';
  let currentPdfText = ''; // Store full PDF text for analysis

  // Canvas for PDF rendering
  let canvas = null;
  let ctx = null;
  let textLayerDiv = null;

  function init() {
    
    // Listen for file uploads
    window.addEventListener('filesUploaded', handleFilesUploaded);
    
    // Listen for wizard modal opening
    const addFieldWizardBtn = document.getElementById('addFieldWizardBtn');
    if (addFieldWizardBtn) {
      addFieldWizardBtn.addEventListener('click', () => {
        // Show PDF viewer in wizard if PDF is loaded
        if (currentPdfFile) {
          setTimeout(showPdfInWizard, 200);
        }
      });
    }
    
  }

  /**
   * Handle uploaded files
   */
  async function handleFilesUploaded(event) {
    const files = event.detail?.files;
    if (!files || files.length === 0) return;

    // Get first PDF
    const firstPdf = files.find(f => f.name.toLowerCase().endsWith('.pdf'));
    if (!firstPdf) {
      return;
    }

    currentPdfFile = firstPdf;
  }

  /**
   * Show PDF viewer in wizard modal
   */
  async function showPdfInWizard() {
    if (!currentPdfFile) return;


    // Create or get PDF viewer modal (separate from wizard)
    let viewerModal = document.getElementById('pdfViewerModal');
    if (!viewerModal) {
      viewerModal = createViewerModal();
    }

    // Show the modal
    viewerModal.style.display = 'flex';

    // Load and render PDF
    await loadPdf(currentPdfFile);
  }

  /**
   * Create PDF viewer modal (full-screen)
   */
  function createViewerModal() {
    const modal = document.createElement('div');
    modal.id = 'pdfViewerModal';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.85);
      z-index: 10000;
      display: none;
      align-items: center;
      justify-content: center;
      animation: fadeIn 0.2s ease;
    `;

    modal.innerHTML = `
      <div style="background: white; width: 90%; max-width: 1200px; max-height: 90vh; border-radius: 12px; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden;">
        
        <!-- Header -->
        <div style="padding: 20px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;">
          <div>
            <h3 style="margin: 0 0 4px 0; color: #111827; font-size: 18px; font-weight: 700;">
              📄 Select Text to Extract
            </h3>
            <p style="margin: 0; color: #6b7280; font-size: 14px;">Click and drag to highlight text in the PDF, then click "Use Selected Text"</p>
          </div>
          <button id="closePdfViewerModal" style="background: none; border: none; font-size: 32px; color: #6b7280; cursor: pointer; padding: 0; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 6px; transition: all 0.2s;" title="Close">&times;</button>
        </div>

        <!-- Controls -->
        <div style="padding: 12px 20px; border-bottom: 1px solid #e5e7eb; display: flex; gap: 12px; align-items: center; background: #f9fafb; flex-shrink: 0;">
          <button id="prevPage" class="pdf-control-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 18l-6-6 6-6"/>
            </svg>
            Previous
          </button>
          <span id="pageInfo" style="font-size: 14px; color: #374151; font-weight: 500; min-width: 100px; text-align: center;">Page 1 of 1</span>
          <button id="nextPage" class="pdf-control-btn">
            Next
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </button>
          
          <div style="flex: 1;"></div>
          
          <button id="zoomOut" class="pdf-control-btn" title="Zoom Out">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35M8 11h6"/>
            </svg>
          </button>
          <span style="font-size: 13px; color: #6b7280; min-width: 50px; text-align: center;" id="zoomLevel">150%</span>
          <button id="zoomIn" class="pdf-control-btn" title="Zoom In">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35M11 8v6M8 11h6"/>
            </svg>
          </button>
        </div>

        <!-- PDF Canvas -->
        <div id="pdfCanvasWrapper" style="flex: 1; overflow: auto; background: #525252; display: flex; align-items: flex-start; justify-content: center; padding: 20px; min-height: 0;">
          <div style="position: relative; background: white; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
            <canvas id="pdfCanvas"></canvas>
            <div id="textLayer" style="position: absolute; left: 0; top: 0; right: 0; bottom: 0; overflow: hidden; line-height: 1.0; user-select: text;"></div>
          </div>
        </div>

        <!-- Selection Panel - Simple: Show selected text and table/column option -->
        <div id="fieldConfigPanel" style="display: none; max-height: 40vh; background: white; border-top: 3px solid #0ea5e9; flex-shrink: 0;">
          
          <!-- Content (scrollable) -->
          <div style="padding: 20px; overflow-y: auto; flex: 1; max-height: calc(40vh - 80px);">
          
          <!-- Selected Text Display -->
          <div style="margin-bottom: 16px; padding: 12px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border: 2px solid #7dd3fc; border-radius: 8px;">
            <div style="font-weight: 600; color: #0c4a6e; margin-bottom: 6px; font-size: 13px; display: flex; align-items: center; gap: 6px;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z"/>
              </svg>
              Selected Text:
            </div>
            <div id="selectedTextValue" style="font-family: 'Consolas', 'Monaco', monospace; color: #0c4a6e; font-size: 13px; word-break: break-word;"></div>
          </div>

          <!-- Table/Column Section -->
          <div id="tableColumnSection" style="display: none; padding: 14px; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 2px solid #fbbf24; border-radius: 8px; margin-bottom: 16px;">
            <label style="display: flex; align-items: flex-start; gap: 12px; cursor: pointer; margin-bottom: 12px;">
              <input type="checkbox" id="pdfTableCheckbox" style="width: 20px; height: 20px; cursor: pointer; margin-top: 2px; flex-shrink: 0;" />
              <div>
                <div style="color: #92400e; font-weight: 700; font-size: 14px; margin-bottom: 4px;">This is in a table column</div>
                <div style="color: #78350f; font-size: 13px;">Check if the value is in a specific column of a table</div>
              </div>
            </label>
            
            <!-- Column Name Input (shown when checkbox is checked) -->
            <div id="pdfColumnNameSection" style="display: none; margin-top: 12px; padding-top: 12px; border-top: 2px solid #fbbf24;">
              <label style="display: block; color: #92400e; font-weight: 600; font-size: 13px; margin-bottom: 6px;">
                Which column?
              </label>
              <input type="text" id="pdfColumnNameInput" placeholder="e.g., Particulars, Salary, Amount" style="width: 100%; padding: 10px; border: 2px solid #fbbf24; border-radius: 6px; font-size: 14px; color: #92400e; background: white;" />
            </div>
          </div>

          </div>
          
          <!-- Button (always visible at bottom) -->
          <div style="padding: 16px 20px; background: #f9fafb; border-top: 2px solid #e5e7eb; display: flex; justify-content: flex-end; flex-shrink: 0;">
            <button id="addFieldFromPdf" style="padding: 12px 28px; background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 15px; box-shadow: 0 4px 12px rgba(14, 165, 233, 0.4); transition: all 0.2s; display: flex; align-items: center; gap: 8px;">
              <span>Use Selected Text</span>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </button>
          </div>

        </div>

      </div>
    `;

    // Add CSS for buttons
    const style = document.createElement('style');
    style.textContent = `
      .pdf-control-btn {
        padding: 8px 16px;
        background: white;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
        font-weight: 500;
        color: #374151;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
      }
      .pdf-control-btn:hover {
        background: #f3f4f6;
        border-color: #9ca3af;
      }
      .pdf-control-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .pdf-control-btn:disabled:hover {
        background: white;
        border-color: #d1d5db;
      }
      #textLayer span {
        color: transparent;
        position: absolute;
        white-space: pre;
        cursor: text;
        transform-origin: 0% 0%;
      }
      #textLayer span::selection {
        background: rgba(59, 130, 246, 0.3);
      }
      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
      #addFieldFromPdf:hover {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        box-shadow: 0 6px 16px rgba(14, 165, 233, 0.4);
        transform: translateY(-1px);
      }
      #cancelFieldConfig:hover {
        background: #f0f9ff;
        border-color: #0ea5e9;
      }
    `;
    document.head.appendChild(style);

    document.body.appendChild(modal);

    // Setup event listeners
    setupViewerControls(modal);

    return modal;
  }

  /**
   * Setup viewer controls
   */
  function setupViewerControls(modal) {
    const closePdfViewerModal = modal.querySelector('#closePdfViewerModal');
    const prevPage = modal.querySelector('#prevPage');
    const nextPage = modal.querySelector('#nextPage');
    const zoomIn = modal.querySelector('#zoomIn');
    const zoomOut = modal.querySelector('#zoomOut');
    const zoomLevel = modal.querySelector('#zoomLevel');

    // Close button
    closePdfViewerModal?.addEventListener('click', () => {
      modal.style.display = 'none';
      hideFieldConfig(); // Clear all state when closing
    });

    // Close on backdrop click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.style.display = 'none';
        hideFieldConfig(); // Clear all state when closing
      }
    });

    // ESC key to close
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.style.display === 'flex') {
        modal.style.display = 'none';
      }
    });

    prevPage?.addEventListener('click', () => {
      if (pageNum <= 1) return;
      pageNum--;
      queueRenderPage(pageNum);
    });

    nextPage?.addEventListener('click', () => {
      if (pageNum >= pdfDoc.numPages) return;
      pageNum++;
      queueRenderPage(pageNum);
    });

    zoomIn?.addEventListener('click', () => {
      scale += 0.25;
      if (zoomLevel) zoomLevel.textContent = Math.round(scale * 100) + '%';
      queueRenderPage(pageNum);
    });

    zoomOut?.addEventListener('click', () => {
      if (scale <= 0.5) return;
      scale -= 0.25;
      if (zoomLevel) zoomLevel.textContent = Math.round(scale * 100) + '%';
      queueRenderPage(pageNum);
    });

    // Field config buttons
    const cancelFieldConfig = modal.querySelector('#cancelFieldConfig');
    const addFieldFromPdf = modal.querySelector('#addFieldFromPdf');

    cancelFieldConfig?.addEventListener('click', () => {
      hideFieldConfig();
    });

    addFieldFromPdf?.addEventListener('click', handleAddFieldFromPdf);

    // Get canvas and text layer
    canvas = modal.querySelector('#pdfCanvas');
    ctx = canvas.getContext('2d');
    textLayerDiv = modal.querySelector('#textLayer');

    // Setup text selection detection
    document.addEventListener('mouseup', handleTextSelection);
  }

  /**
   * Load PDF using PDF.js
   */
  async function loadPdf(file) {
    try {
      
      const arrayBuffer = await file.arrayBuffer();
      const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
      
      pdfDoc = await loadingTask.promise;
      
      // Update page info
      document.getElementById('pageInfo').textContent = `Page 1 of ${pdfDoc.numPages}`;
      
      // Render first page
      pageNum = 1;
      await renderPage(pageNum);
      
    } catch (error) {
      console.error('Failed to load PDF:', error);
      window.toast.error('Failed to load PDF. Please try a different file.');
    }
  }

  /**
   * Render a page
   */
  async function renderPage(num) {
    pageRendering = true;
    
    try {
      const page = await pdfDoc.getPage(num);
      const viewport = page.getViewport({ scale });
      
      // Set canvas size
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      
      // Render PDF page into canvas
      const renderContext = {
        canvasContext: ctx,
        viewport: viewport
      };
      
      await page.render(renderContext).promise;
      
      // Render text layer for selection
      await renderTextLayer(page, viewport);
      
      pageRendering = false;
      
      if (pageNumPending !== null) {
        renderPage(pageNumPending);
        pageNumPending = null;
      }
      
      // Update controls
      document.getElementById('pageInfo').textContent = `Page ${num} of ${pdfDoc.numPages}`;
      document.getElementById('prevPage').disabled = num <= 1;
      document.getElementById('nextPage').disabled = num >= pdfDoc.numPages;
      
    } catch (error) {
      console.error('Failed to render page:', error);
      pageRendering = false;
    }
  }

  /**
   * Queue page render (debounce)
   */
  function queueRenderPage(num) {
    if (pageRendering) {
      pageNumPending = num;
    } else {
      renderPage(num);
    }
  }

  /**
   * Render text layer for selection
   */
  async function renderTextLayer(page, viewport) {
    // Clear existing text layer
    textLayerDiv.innerHTML = '';
    textLayerDiv.style.width = `${viewport.width}px`;
    textLayerDiv.style.height = `${viewport.height}px`;
    
    try {
      const textContent = await page.getTextContent();
      
      // Render text layer using PDF.js built-in renderer
      pdfjsLib.renderTextLayer({
        textContent: textContent,
        container: textLayerDiv,
        viewport: viewport,
        textDivs: []
      });
      
      // Enable text selection
      enableTextSelection();
      
    } catch (error) {
      console.error('Failed to render text layer:', error);
    }
  }

  /**
   * Enable text selection in PDF
   */
  function enableTextSelection() {
    textLayerDiv.addEventListener('mouseup', handleTextSelection);
  }

  /**
   * Handle text selection
   */
  function handleTextSelection() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();
    
    if (selectedText.length > 0) {
      showSelectedText(selectedText);
    }
  }

  /**
   * Show selected text preview
   */
  function showSelectedText(text) {
    const preview = document.getElementById('selectedTextPreview');
    const valueDiv = document.getElementById('selectedTextValue');
    
    if (preview && valueDiv) {
      valueDiv.textContent = text;
      preview.style.display = 'block';
      preview.dataset.selectedText = text;
    }
  }

  /**
   * Handle text selection in PDF
   */
  function handleTextSelection() {
    const modal = document.getElementById('pdfViewerModal');
    if (!modal || modal.style.display !== 'flex') return;

    const selection = window.getSelection();
    const text = selection.toString().trim();

    if (text && text.length > 0) {
      selectedText = text;
      showFieldConfig(text);
    }
  }

  /**
   * Show field configuration panel
   */
  async function showFieldConfig(text) {
    const panel = document.getElementById('fieldConfigPanel');
    const textDisplay = document.getElementById('selectedTextValue');
    const tableColumnSection = document.getElementById('tableColumnSection');

    if (!panel || !textDisplay) return;

    // Display selected text
    textDisplay.textContent = text;

    // Show table/column section immediately
    if (tableColumnSection) {
      tableColumnSection.style.display = 'block';
      
      // Setup checkbox change listener (only once)
      const tableCheckbox = document.getElementById('pdfTableCheckbox');
      const columnSection = document.getElementById('pdfColumnNameSection');
      
      if (tableCheckbox && columnSection && !tableCheckbox.hasAttribute('data-listener-added')) {
        tableCheckbox.setAttribute('data-listener-added', 'true');
        tableCheckbox.addEventListener('change', function() {
          columnSection.style.display = this.checked ? 'block' : 'none';
        });
      }
      
      // Reset checkbox and column input
      if (tableCheckbox) tableCheckbox.checked = false;
      if (columnSection) columnSection.style.display = 'none';
      const columnInput = document.getElementById('pdfColumnNameInput');
      if (columnInput) columnInput.value = '';
    }

    // Show panel with flexbox layout
    panel.style.display = 'flex';
    panel.style.flexDirection = 'column';
  }

  /**
   * Search PDF for all occurrences and show them
   */
  async function searchAndShowOccurrences(searchText) {
    const matchStatusContainer = document.getElementById('matchStatus');
    const tableColumnSection = document.getElementById('tableColumnSection');
    
    if (!matchStatusContainer) return;

    // Get PDF text from backend
    if (!currentPdfFile) {
      matchStatusContainer.innerHTML = '<p style="color: #6b7280; font-size: 13px;">No PDF loaded</p>';
      return;
    }

    try {
      // Extract text from PDF
      const formData = new FormData();
      formData.append('file', currentPdfFile);

      const response = await fetch('/api/preview-pdf-text', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Failed to extract PDF text');

      const data = await response.json();
      currentPdfText = data.text || '';

      // Find all occurrences
      const occurrences = findAllOccurrences(currentPdfText, searchText);

      if (occurrences.length === 0) {
        matchStatusContainer.innerHTML = `
          <div style="padding: 12px; background: #fef3c7; border: 2px solid #fbbf24; border-radius: 6px; color: #92400e;">
            <strong>⚠️ Not found in PDF</strong>
            <p style="margin: 8px 0 0 0; font-size: 13px;">Try selecting different text or check your selection.</p>
          </div>
        `;
        if (tableColumnSection) tableColumnSection.style.display = 'none';
        return;
      }

      // Show match count
      matchStatusContainer.innerHTML = `
        <div style="padding: 12px; background: #d1fae5; border: 2px solid #10b981; border-radius: 6px;">
          <div style="font-weight: 600; color: #065f46; font-size: 14px; display: flex; align-items: center; gap: 6px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z"/>
            </svg>
            Found in PDF (${occurrences.length} ${occurrences.length === 1 ? 'match' : 'matches'})
          </div>
        </div>
      `;

      // Show table/column section
      if (tableColumnSection) {
        tableColumnSection.style.display = 'block';
        
        // Add checkbox change listener
        const tableCheckbox = document.getElementById('pdfTableCheckbox');
        const columnSection = document.getElementById('pdfColumnNameSection');
        
        if (tableCheckbox && columnSection) {
          // Remove old listeners by cloning
          const newCheckbox = tableCheckbox.cloneNode(true);
          tableCheckbox.parentNode.replaceChild(newCheckbox, tableCheckbox);
          
          newCheckbox.addEventListener('change', function() {
            columnSection.style.display = this.checked ? 'block' : 'none';
          });
        }
      }

    } catch (error) {
      console.error('Error searching PDF:', error);
      matchStatusContainer.innerHTML = `
        <div style="padding: 12px; background: #fee; border: 2px solid #f87171; border-radius: 6px; color: #991b1b;">
          <strong>❌ Error</strong>
          <p style="margin: 8px 0 0 0; font-size: 13px;">Could not search PDF. Please try again.</p>
        </div>
      `;
      if (tableColumnSection) tableColumnSection.style.display = 'none';
    }
  }

  /**
   * Find all occurrences of text in PDF
   */
  function findAllOccurrences(pdfText, searchText) {
    const occurrences = [];
    const lines = pdfText.split('\n');
    
    // Normalize search text
    const normalizedSearch = searchText.trim();
    
    lines.forEach((line, lineIndex) => {
      const index = line.indexOf(normalizedSearch);
      if (index !== -1) {
        // Extract context (show ~50 chars before and after)
        const start = Math.max(0, index - 20);
        const end = Math.min(line.length, index + normalizedSearch.length + 50);
        let context = line.substring(start, end);
        
        if (start > 0) context = '...' + context;
        if (end < line.length) context = context + '...';
        
        occurrences.push({
          lineIndex: lineIndex,
          charIndex: index,
          context: context,
          fullLine: line
        });
      }
    });
    
    return occurrences;
  }

  /**
   * Escape HTML for safe display
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Hide field configuration panel
   */
  function hideFieldConfig() {
    const panel = document.getElementById('fieldConfigPanel');
    if (panel) {
      panel.style.display = 'none';
    }
    
    // Clear all state
    const tableCheckbox = document.getElementById('pdfTableCheckbox');
    const columnInput = document.getElementById('pdfColumnNameInput');
    const columnSection = document.getElementById('pdfColumnNameSection');
    const selectedTextDisplay = document.getElementById('selectedTextValue');
    const tableColumnSection = document.getElementById('tableColumnSection');
    
    if (tableCheckbox) tableCheckbox.checked = false;
    if (columnInput) columnInput.value = '';
    if (columnSection) columnSection.style.display = 'none';
    if (selectedTextDisplay) selectedTextDisplay.textContent = '';
    if (tableColumnSection) tableColumnSection.style.display = 'none';
    
    hideTableOptions();
    selectedText = '';
  }

  /**
   * Handle "Use Selected Text" button
   */
  function handleAddFieldFromPdf() {
    if (!selectedText) {
      window.toast.error('Please select text first');
      return;
    }

    // Get table/column info from PDF viewer
    const tableCheckbox = document.getElementById('pdfTableCheckbox');
    const columnInput = document.getElementById('pdfColumnNameInput');
    
    const isTable = tableCheckbox?.checked || false;
    const columnName = isTable && columnInput ? columnInput.value.trim() : '';

    // Validate: if table is checked, column name is required
    if (isTable && !columnName) {
      window.toast.error('Please enter the column name');
      return;
    }


    // Close PDF viewer
    const modal = document.getElementById('pdfViewerModal');
    if (modal) {
      modal.style.display = 'none';
    }

    // Open wizard modal with pre-filled data
    openWizardWithData(selectedText, isTable, columnName);
  }

  /**
   * Open wizard modal with pre-filled text and table/column info
   */
  function openWizardWithData(text, isTable, columnName) {
    // Open wizard
    const wizardModal = document.getElementById('fieldWizardModal');
    if (!wizardModal) {
      console.error('Wizard modal not found');
      return;
    }

    wizardModal.style.display = 'flex';

    // Wait a moment for modal to render
    setTimeout(() => {
      const fieldLookForInput = document.getElementById('fieldLookForInput');
      const fieldInTableCheckbox = document.getElementById('fieldInTableCheckbox');
      const fieldColumnInput = document.getElementById('fieldColumnInput');
      const fieldColumnSection = document.getElementById('fieldColumnSection');
      
      // Pre-fill text to look for
      if (fieldLookForInput) {
        fieldLookForInput.value = text;
        fieldLookForInput.dispatchEvent(new Event('input', { bubbles: true }));
      }

      // Pre-fill table checkbox and column name
      if (isTable && fieldInTableCheckbox) {
        fieldInTableCheckbox.checked = true;
        fieldInTableCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
        
        // Pre-fill column name
        if (columnName && fieldColumnInput) {
          setTimeout(() => {
            fieldColumnInput.value = columnName;
          }, 50);
        }
      }
    }, 50);
  }

  /**
   * Show toast notification
   */
  function showToast(message, type = 'info') {
    // Simple toast - can be enhanced later
    const toast = document.createElement('div');
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 12px 20px;
      background: ${type === 'success' ? '#10b981' : '#3b82f6'};
      color: white;
      border-radius: 8px;
      font-weight: 600;
      z-index: 10000;
      animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // Expose public API
  window.pdfViewer = {
    init,
    showPdfInWizard
  };

  // Auto-init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
