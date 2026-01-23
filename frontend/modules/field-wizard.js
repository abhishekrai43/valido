// Field Wizard Module
// Handles the field extraction wizard modal

// Make fields globally accessible for rules-builder.js
window.fields = window.fields || [];
let fields = window.fields;

// Flag to prevent duplicate initialization
let isFieldWizardInitialized = false;

async function _fetchAnchorCandidates({ anchorText, valueHint, maxPages = 3 } = {}) {
  try {
    const pdfFile = window.currentPdfFile || window.currentPdfFileForWizard || null;
    if (!pdfFile) {
      return { success: false, candidates: [], message: 'No PDF loaded' };
    }

    const form = new FormData();
    form.append('file', pdfFile);
    form.append('anchor_text', String(anchorText || ''));
    form.append('max_pages', String(maxPages));
    if (valueHint) form.append('value_hint', String(valueHint));

    const res = await fetch('/api/v1/pdf-anchor-candidates', {
      method: 'POST',
      body: form
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return null;
    }
    return data;
  } catch (e) {
    console.warn('Candidate fetch failed', e);
    return null;
  }
}

function _deriveValueHintFromFieldType(type) {
  const t = String(type || '').toLowerCase();
  if (t === 'number') return 'number';
  if (t === 'date') return 're:\\b\\d{1,2}[/\\-]\\d{1,2}[/\\-]\\d{2,4}\\b';
  return null;
}

function _openCandidatePickerModal(candidates = [], anchorText = '') {
  return new Promise((resolve) => {
    const modal = document.createElement('div');
    modal.className = 'candidate-picker-modal';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.6);
      z-index: 10050;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    `;

    const safe = (s) => String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

    const itemsHtml = candidates.map((c, idx) => {
      const page = c.page;
      const ctx = safe(c.context);
      const val = safe(c.previewValueRight);
      const reasons = Array.isArray(c.reasons) ? c.reasons.slice(0, 4).join(', ') : '';
      return `
        <div data-idx="${idx}" style="border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; cursor: pointer; background: white; transition: box-shadow .15s;">
          <div style="display:flex; justify-content:space-between; gap:10px; align-items:center;">
            <div style="font-weight:700; color:#111827;">Page ${page}</div>
            <div style="font-size:12px; color:#6b7280;">score ${Number(c.score || 0).toFixed(2)}</div>
          </div>
          <div style="margin-top:8px; font-size:12px; color:#374151; line-height:1.4;">
            <div style="color:#6b7280; font-weight:600;">Context</div>
            <div style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; background:#f9fafb; padding:8px; border-radius:8px;">${ctx}</div>
          </div>
          <div style="margin-top:10px; font-size:12px; color:#374151; line-height:1.4;">
            <div style="color:#6b7280; font-weight:600;">Right-cell preview</div>
            <div style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; background:#f0f9ff; padding:8px; border-radius:8px; border:1px solid #bae6fd;">${val || '<empty>'}</div>
          </div>
          <div style="margin-top:8px; font-size:11px; color:#9ca3af;">${safe(reasons)}</div>
        </div>
      `;
    }).join('');

    modal.innerHTML = `
      <div style="background: white; width: 920px; max-width: 100%; max-height: 90vh; border-radius: 14px; overflow: hidden; box-shadow: 0 30px 80px rgba(0,0,0,0.35); display:flex; flex-direction:column;">
        <div style="padding: 16px 18px; border-bottom: 1px solid #e5e7eb; display:flex; align-items:center; justify-content:space-between; gap:12px;">
          <div>
            <div style="font-size: 16px; font-weight: 800; color:#111827;">Multiple matches for “${safe(anchorText)}”</div>
            <div style="font-size: 13px; color:#6b7280; margin-top: 2px;">Pick the correct occurrence so extractions never flip again.</div>
          </div>
          <button id="candidatePickerCancel" style="border:none; background:#f3f4f6; color:#111827; padding:10px 12px; border-radius:10px; cursor:pointer; font-weight:700;">Cancel</button>
        </div>
        <div style="padding: 16px 18px; overflow:auto; display:grid; grid-template-columns: 1fr 1fr; gap: 12px; background:#f9fafb;">
          ${itemsHtml}
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const cleanup = () => {
      modal.remove();
    };

    modal.querySelector('#candidatePickerCancel')?.addEventListener('click', () => {
      cleanup();
      resolve(null);
    });

    modal.addEventListener('click', (e) => {
      const card = e.target.closest('[data-idx]');
      if (!card) return;
      const idx = parseInt(card.getAttribute('data-idx'), 10);
      const picked = candidates[idx] || null;
      cleanup();
      resolve(picked);
    });
  });
}

function _normalizeFieldName(name) {
  return String(name || '')
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase();
}

function _getFieldsArray() {
  // Always read from global to avoid stale references if another script reassigns window.fields
  if (!Array.isArray(window.fields)) {
    window.fields = [];
  }
  fields = window.fields;
  return fields;
}

function _fieldNameExists(name) {
  const norm = _normalizeFieldName(name);
  if (!norm) return false;
  const arr = _getFieldsArray();
  return arr.some(f => _normalizeFieldName(f && f.name) === norm);
}

function initFieldWizard() {
  // Prevent duplicate initialization
  if (isFieldWizardInitialized) {
    return;
  }
  isFieldWizardInitialized = true;
  
  const addFieldWizardBtn = document.getElementById('addFieldWizardBtn');
  const fieldWizardModal = document.getElementById('fieldWizardModal');
  const fieldWizardClose = document.getElementById('fieldWizardClose');
  const fieldWizardCancel = document.getElementById('fieldWizardCancel');
  const fieldWizardSave = document.getElementById('fieldWizardSave');
  const fieldNameInput = document.getElementById('fieldNameInput');
  const fieldLookForInput = document.getElementById('fieldLookForInput');
  const fieldStrategySelect = document.getElementById('fieldStrategySelect');
  const fieldStrategySection = document.getElementById('fieldStrategySection');
  const fieldInTableCheckbox = document.getElementById('fieldInTableCheckbox');
  const fieldColumnSection = document.getElementById('fieldColumnSection');
  const fieldColumnInput = document.getElementById('fieldColumnInput');
  const fieldsList = document.getElementById('fieldsList');

  // Toggle column section visibility
  if (fieldInTableCheckbox) {
    fieldInTableCheckbox.addEventListener('change', (e) => {
      if (fieldColumnSection) {
        fieldColumnSection.style.display = e.target.checked ? 'block' : 'none';
      }
      if (!e.target.checked && fieldColumnInput) {
        fieldColumnInput.value = '';
      }
    });
  }

  // Type selection handler for showing validation rules
  const fieldTypeRadios = document.querySelectorAll('input[name="fieldType"]');
  const validationRulesSection = document.getElementById('validationRulesSection');
  const textValidations = document.getElementById('textValidations');
  const numberValidations = document.getElementById('numberValidations');
  const dateValidations = document.getElementById('dateValidations');

  // Show/hide validation rules based on type
  fieldTypeRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
      const type = e.target.value;
      validationRulesSection.style.display = 'block';
      textValidations.style.display = type === 'text' ? 'block' : 'none';
      numberValidations.style.display = type === 'number' ? 'block' : 'none';
      dateValidations.style.display = type === 'date' ? 'block' : 'none';
    });
  });

  // Open wizard modal
  if (addFieldWizardBtn) {
    addFieldWizardBtn.addEventListener('click', () => {
      // Reset wizard inputs
      fieldNameInput.value = '';
      fieldLookForInput.value = '';
      if (fieldInTableCheckbox) fieldInTableCheckbox.checked = false;
      if (fieldColumnInput) fieldColumnInput.value = '';
      document.querySelectorAll('input[name="fieldType"]').forEach(radio => {
        radio.checked = radio.value === 'text';
      });
      fieldStrategySelect.value = 'first';
      
      // Reset visibility states
      fieldStrategySection.style.display = 'block';
      if (fieldColumnSection) fieldColumnSection.style.display = 'none';
      validationRulesSection.style.display = 'none';
      
      // Reset validation checkboxes
      document.querySelectorAll('.validation-checkbox input[type="checkbox"]').forEach(cb => cb.checked = false);
      document.querySelectorAll('.inline-number, .inline-text, .inline-date').forEach(input => input.value = '');
      
      // Show modal
      fieldWizardModal.style.display = 'flex';
    });
  }

  // Close modal handlers
  if (fieldWizardClose) {
    fieldWizardClose.addEventListener('click', () => {
      fieldWizardModal.style.display = 'none';
    });
  }

  if (fieldWizardCancel) {
    fieldWizardCancel.addEventListener('click', () => {
      fieldWizardModal.style.display = 'none';
    });
  }

  // Save field
  if (fieldWizardSave) {
    fieldWizardSave.addEventListener('click', async () => {
      // Ensure we always validate against the current global fields array
      _getFieldsArray();

      const name = fieldNameInput.value.trim();
      const lookFor = fieldLookForInput.value.trim();
      const type = document.querySelector('input[name="fieldType"]:checked')?.value || 'text';
      const strategy = fieldStrategySelect.value;
      
      // Re-query elements to ensure we have latest state
      const inTableCheckbox = document.getElementById('fieldInTableCheckbox');
      const columnInput = document.getElementById('fieldColumnInput');
      const inTable = inTableCheckbox?.checked || false;
      const column = inTable && columnInput ? columnInput.value.trim() : null;

      // Validation
      if (!name) {
        window.toast.error('Please enter a field name');
        return;
      }
      if (!lookFor) {
        window.toast.error('Please enter text to look for');
        return;
      }
      if (inTable && !column) {
        window.toast.error('Please specify which column to extract from');
        return;
      }

      // Check for duplicate field names
      if (_fieldNameExists(name)) {
        window.toast.error('A field with this name already exists');
        return;
      }

      // Collect validations based on type
      const validations = [];
      if (type === 'text') {
        if (document.getElementById('textMinLength').checked) {
          const val = document.getElementById('textMinLengthValue').value;
          if (val) validations.push({ type: 'minLength', value: parseInt(val) });
        }
        if (document.getElementById('textMaxLength').checked) {
          const val = document.getElementById('textMaxLengthValue').value;
          if (val) validations.push({ type: 'maxLength', value: parseInt(val) });
        }
        if (document.getElementById('textPattern').checked) {
          const val = document.getElementById('textPatternValue').value;
          if (val) validations.push({ type: 'pattern', value: val });
        }
      } else if (type === 'number') {
        if (document.getElementById('numberMin').checked) {
          const val = document.getElementById('numberMinValue').value;
          if (val) validations.push({ type: 'min', value: parseFloat(val) });
        }
        if (document.getElementById('numberMax').checked) {
          const val = document.getElementById('numberMaxValue').value;
          if (val) validations.push({ type: 'max', value: parseFloat(val) });
        }
        if (document.getElementById('numberEquals').checked) {
          const val = document.getElementById('numberEqualsValue').value;
          if (val) validations.push({ type: 'equals', value: parseFloat(val) });
        }
      } else if (type === 'date') {
        if (document.getElementById('dateBefore').checked) {
          const val = document.getElementById('dateBeforeValue').value;
          if (val) validations.push({ type: 'before', value: val });
        }
        if (document.getElementById('dateAfter').checked) {
          const val = document.getElementById('dateAfterValue').value;
          if (val) validations.push({ type: 'after', value: val });
        }
      }

      // Add field (regular extraction with lookFor)
      const newField = {
        name,
        lookFor,
        type,
        validations,
        strategy
      };

      // If a selectionTarget was chosen in the PDF viewer (pre-wizard), persist it.
      try {
        if (window.pendingSelectionTarget && typeof window.pendingSelectionTarget === 'object') {
          newField.selectionTarget = window.pendingSelectionTarget;
          // consume it so it doesn't leak to the next field
          window.pendingSelectionTarget = null;
        }
      } catch (e) {
        // ignore
      }
      
      // Add column if specified
      if (column) {
        newField.column = column;
      } else {
      }

      // Ambiguity elimination: if the same lookFor exists multiple times in the PDF,
      // ask the user to choose which occurrence they meant.
      // Only applies when a PDF is loaded for the wizard.
      try {
        // If we already have a selectionTarget from the viewer, don't prompt again.
        if (newField.selectionTarget) {
          throw new Error('skip-picker');
        }
        const typeHint = _deriveValueHintFromFieldType(type);
        const candidateResponse = await _fetchAnchorCandidates({
          anchorText: lookFor,
          // For table fields, the column name helps ranking; for non-table fields,
          // use a lightweight hint derived from field type.
          valueHint: column || typeHint,
          maxPages: 3
        });

        const candidates = candidateResponse?.candidates || [];

        if (candidateResponse?.success === false && candidateResponse?.message === 'No PDF loaded') {
          // No PDF = no disambiguation available; continue normally.
        }

        // If multiple candidates, show picker.
        if (Array.isArray(candidates) && candidates.length > 1) {
          const picked = await _openCandidatePickerModal(candidates, lookFor);
          if (!picked) {
            // User cancelled: don't create the field.
            return;
          }

          newField.selectionTarget = {
            page: picked.page,
            occurrenceIndexOnPage: picked.occurrenceIndexOnPage,
            anchorBBox: picked.anchorBBox
          };
        }
      } catch (e) {
        // Best-effort only; never block field creation.
      }
      
  _getFieldsArray().push(newField);
      

      // Reset form for next field
      fieldNameInput.value = '';
      fieldLookForInput.value = '';
      fieldStrategySelect.value = 'first';
      if (fieldInTableCheckbox) fieldInTableCheckbox.checked = false;
      if (fieldColumnSection) fieldColumnSection.style.display = 'none';
      if (fieldColumnInput) fieldColumnInput.value = '';
      document.querySelectorAll('input[name="fieldType"]')[0].checked = true;
      validationRulesSection.style.display = 'none';

      // Close modal and refresh
      fieldWizardModal.style.display = 'none';
      renderFields();
      if (typeof buildRulesPreview === 'function') {
        buildRulesPreview();
      } else {
        console.error('buildRulesPreview function not found!');
      }
    });
  }
  
  // ===== Between Words Modal Handlers =====
  const addBetweenWordsBtn = document.getElementById('addBetweenWordsBtn');
  const betweenWordsModal = document.getElementById('betweenWordsModal');
  const betweenWordsClose = document.getElementById('betweenWordsClose');
  const betweenWordsCancel = document.getElementById('betweenWordsCancel');
  const betweenWordsSave = document.getElementById('betweenWordsSave');
  
  // Open between words modal
  if (addBetweenWordsBtn) {
    addBetweenWordsBtn.addEventListener('click', () => {
      // Reset inputs
      document.getElementById('betweenFieldName').value = '';
      document.getElementById('betweenStartWord').value = '';
      document.getElementById('betweenEndWord').value = '';
      document.querySelectorAll('input[name="betweenFieldType"]').forEach(radio => {
        radio.checked = radio.value === 'text';
      });
      document.querySelectorAll('input[name="betweenOccurrence"]').forEach(radio => {
        radio.checked = radio.value === 'first';
      });
      
      // Show modal
      betweenWordsModal.style.display = 'flex';
    });
  }
  
  // Close between words modal
  if (betweenWordsClose) {
    betweenWordsClose.addEventListener('click', () => {
      betweenWordsModal.style.display = 'none';
    });
  }
  
  if (betweenWordsCancel) {
    betweenWordsCancel.addEventListener('click', () => {
      betweenWordsModal.style.display = 'none';
    });
  }
  
  // Save between words field
  if (betweenWordsSave) {
    betweenWordsSave.addEventListener('click', () => {
      // Ensure we always validate against the current global fields array
      _getFieldsArray();

      const name = document.getElementById('betweenFieldName').value.trim();
      const startWord = document.getElementById('betweenStartWord').value.trim();
      const endWord = document.getElementById('betweenEndWord').value.trim();
      const type = document.querySelector('input[name="betweenFieldType"]:checked')?.value || 'text';
      const occurrence = document.querySelector('input[name="betweenOccurrence"]:checked')?.value || 'first';
      
      // Validation
      if (!name) {
        window.toast.error('Please enter a field name');
        return;
      }
      if (!startWord || !endWord) {
        window.toast.error('Please enter both start and end words');
        return;
      }
      
      // Check for duplicate field names
      if (_fieldNameExists(name)) {
        window.toast.error('A field with this name already exists');
        return;
      }
      
      // Add field with between strategy
      const newField = {
        name,
        type,
        strategy: 'between',
        startMarker: startWord,
        endMarker: endWord,
        occurrence: occurrence,
        validations: []
      };
      
  _getFieldsArray().push(newField);
      
      // Reset between words form
      document.getElementById('betweenFieldName').value = '';
      document.getElementById('betweenStartWord').value = '';
      document.getElementById('betweenEndWord').value = '';
      document.querySelectorAll('input[name="betweenOccurrence"]').forEach(radio => {
        radio.checked = radio.value === 'first';
      });
      
      // Close modal and refresh
      betweenWordsModal.style.display = 'none';
      renderFields();
      if (typeof buildRulesPreview === 'function') buildRulesPreview();
    });
  }
  
  // ===== Table Extraction Integration =====
  // Listen for table-selected events from table wizard
  document.addEventListener('table-selected', (event) => {
    const { page, tableIndex, extractionType } = event.detail;

    // Ensure we always validate against the current global fields array
    _getFieldsArray();
    
    // Create a descriptive field name
    let fieldName;
    if (extractionType === 'all-pages') {
      fieldName = `All_Tables_All_Pages`;
    } else if (extractionType === 'all') {
      fieldName = `Table_Data_Page_${page}`;
    } else {
      fieldName = `Table_${tableIndex}_Page_${page}`;
    }
    
    // Check if field already exists
    if (_fieldNameExists(fieldName)) {
      window.toast && window.toast.error(`Field "${fieldName}" already exists. Remove it first or use a different name.`);
      return;
    }
    
    // Add table extraction field
    const newField = {
      name: fieldName,
      type: 'table',
      strategy: 'table_extraction',
      extractionType: extractionType,
      validations: []
    };
    
    // Add page and tableIndex only if not all-pages
    if (extractionType !== 'all-pages') {
      newField.page = page;
    }
    
    if (extractionType === 'single') {
      newField.tableIndex = tableIndex;
    }
    
  _getFieldsArray().push(newField);
    
    // Close table wizard modal if it exists
    const tableWizardModal = document.getElementById('tableWizardModal');
    if (tableWizardModal) {
      tableWizardModal.style.display = 'none';
    }
    
    // Refresh field list
    renderFields();
    if (typeof buildRulesPreview === 'function') buildRulesPreview();
    
    // Show success message
    window.toast && window.toast.success(`Table extraction field "${fieldName}" added successfully!`);
  });
}

function renderFields() {
  const fieldsList = document.getElementById('fieldsList');
  
  if (!fieldsList) return;

  if (fields.length === 0) {
    fieldsList.innerHTML = `
      <div class="fields-empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" style="opacity: 0.3; margin-bottom: 12px;">
          <path d="M12 4v16m8-8H4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-opacity="0.2"/>
        </svg>
        <p style="color: #9ca3af; font-size: 14px; margin: 0;">No fields added yet</p>
        <p style="color: #d1d5db; font-size: 13px; margin: 4px 0 0 0;">Click "Add Field to Extract" to get started</p>
      </div>
    `;
    if (typeof buildRulesPreview === 'function') buildRulesPreview();
    return;
  }
  
  fieldsList.innerHTML = '';
  
  fields.forEach((f, idx) => {
    const fieldCard = document.createElement('div');
    fieldCard.className = 'field-card';
    
    // Type icon badge
    const typeBadge = document.createElement('span');
    typeBadge.className = `field-type-badge field-type-${f.type}`;
    let typeIcon = '';
    if (f.type === 'text') {
      typeIcon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M9.6 15.6h4.8L12 7.2zM11 3h2l7 18h-2.3l-1.7-4.5H8l-1.7 4.5H4z"/></svg>';
    } else if (f.type === 'number') {
      typeIcon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><text x="2" y="18" font-size="16" font-weight="bold">123</text></svg>';
    } else if (f.type === 'date') {
      typeIcon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M7 10h2v2H7zm4 0h2v2h-2zm4 0h2v2h-2zm-8 4h2v2H7zm4 0h2v2h-2zm4 0h2v2h-2z"/><path d="M5 22h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-1V2h-2v2H8V2H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2zm0-2V9h14v11H5z"/></svg>';
    } else if (f.type === 'table') {
      typeIcon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9" stroke="white" stroke-width="2"/><line x1="3" y1="15" x2="21" y2="15" stroke="white" stroke-width="2"/><line x1="9" y1="9" x2="9" y2="21" stroke="white" stroke-width="2"/></svg>';
    }
    typeBadge.innerHTML = typeIcon;
    
    // Field info
    const fieldInfo = document.createElement('div');
    fieldInfo.className = 'field-info';
    
    const fieldName = document.createElement('div');
    fieldName.className = 'field-name';
    fieldName.textContent = f.name;
    
    const fieldLookFor = document.createElement('div');
    fieldLookFor.className = 'field-lookfor';
    if (f.strategy === 'table_extraction') {
      if (f.extractionType === 'all-pages') {
        fieldLookFor.textContent = `Extract all tables from all pages`;
      } else if (f.extractionType === 'all') {
        fieldLookFor.textContent = `Extract all tables from page ${f.page}`;
      } else {
        fieldLookFor.textContent = `Extract table ${f.tableIndex} from page ${f.page}`;
      }
    } else if (f.strategy === 'between') {
      fieldLookFor.textContent = `Between: "${f.startMarker}" and "${f.endMarker}"`;
    } else {
      fieldLookFor.textContent = f.lookFor;
    }
    
    fieldInfo.appendChild(fieldName);
    fieldInfo.appendChild(fieldLookFor);
    
    // Strategy selector (hide for table extraction fields)
    const strategySelect = document.createElement('select');
    strategySelect.className = 'field-strategy';
    if (f.strategy === 'table_extraction') {
      strategySelect.style.display = 'none';
    } else {
      strategySelect.innerHTML = `
        <option value="first" ${f.strategy === 'first' ? 'selected' : ''}>First</option>
        <option value="last" ${f.strategy === 'last' ? 'selected' : ''}>Last</option>
        <option value="all" ${f.strategy === 'all' ? 'selected' : ''}>All</option>
        <option value="between" ${f.strategy === 'between' ? 'selected' : ''}>Between</option>
      `;
      strategySelect.addEventListener('change', (e) => {
        fields[idx].strategy = e.target.value;
        if (typeof buildRulesPreview === 'function') buildRulesPreview();
      });
    }
    
    // Remove button
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'field-remove';
    removeBtn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    `;
    removeBtn.addEventListener('click', () => {
      window.toast.confirm(`Remove field "${f.name}"?`, () => {
        fields.splice(idx, 1);
        renderFields();
        if (typeof buildRulesPreview === 'function') buildRulesPreview(); 
      });
    });
    
    fieldCard.appendChild(typeBadge);
    fieldCard.appendChild(fieldInfo);
    fieldCard.appendChild(strategySelect);
    fieldCard.appendChild(removeBtn);
    fieldsList.appendChild(fieldCard);
  });
  if (typeof buildRulesPreview === 'function') buildRulesPreview();
}

function getFields() {
  return fields;
}

function setFields(newFields) {
  fields = newFields || [];
  window.fields = fields; // Keep global reference in sync
  renderFields();
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { initFieldWizard, renderFields, getFields, setFields };
}
