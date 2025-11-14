// Rules builder - Simple validation rules with field extraction
(() => {
  function init() {
  const panels = document.querySelectorAll('.panel');
  const rulesPreview = document.getElementById('rulesPreview');
  const rulesTextarea = document.getElementById('rules');

  // Simple panel elements
  const chkSigned = document.getElementById('chk_validate_signed');
  const chkMustContain = document.getElementById('chk_must_contain');
  const mustContainText = document.getElementById('must_contain_text');
  const mustContainCaseSensitive = document.getElementById('must_contain_case_sensitive');
  const chkMustNotContain = document.getElementById('chk_must_not_contain');
  const mustNotContainText = document.getElementById('must_not_contain_text');
  const mustNotContainCaseSensitive = document.getElementById('must_not_contain_case_sensitive');
  const chkPageCount = document.getElementById('chk_page_count');
  const pageCountOperator = document.getElementById('page_count_operator');
  const pageCountValue = document.getElementById('page_count_value');
  
  // Wizard modal elements
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
  const fieldFormulaSection = document.getElementById('fieldFormulaSection');
  const fieldFormulaInput = document.getElementById('fieldFormulaInput');
  const fieldsList = document.getElementById('fieldsList');

  // Toggle column section visibility
  if (fieldInTableCheckbox) {
    fieldInTableCheckbox.addEventListener('change', (e) => {
      if (fieldColumnSection) fieldColumnSection.style.display = e.target.checked ? 'block' : 'none';
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
      
      // Show/hide formula section for computed type
      if (type === 'computed') {
        if (fieldFormulaSection) fieldFormulaSection.style.display = 'block';
        if (fieldStrategySection) fieldStrategySection.style.display = 'none';
        if (validationRulesSection) validationRulesSection.style.display = 'none';
      } else {
        if (fieldFormulaSection) fieldFormulaSection.style.display = 'none';
        if (fieldStrategySection) fieldStrategySection.style.display = 'block';
        if (validationRulesSection) validationRulesSection.style.display = 'block';
        if (textValidations) textValidations.style.display = type === 'text' ? 'block' : 'none';
        if (numberValidations) numberValidations.style.display = type === 'number' ? 'block' : 'none';
        if (dateValidations) dateValidations.style.display = type === 'date' ? 'block' : 'none';
      }
    });
  });

  // Always start with empty fields array - loadRuleset() will populate if loading saved ruleset
  let fields = [];
  // Keep window.fields in sync
  window.fields = fields;

  function renderFields(){
    if (!fieldsList) return;
    
    fieldsList.innerHTML = '';
    
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
      buildRulesPreview();
      return;
    }
    
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
      } else if (f.type === 'computed') {
        typeIcon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><text x="6" y="18" font-size="18" font-weight="bold">=</text></svg>';
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
      // Show formula for computed fields, lookFor for others
      fieldLookFor.textContent = f.type === 'computed' ? f.formula : f.lookFor;
      
      fieldInfo.appendChild(fieldName);
      fieldInfo.appendChild(fieldLookFor);
      
      // Strategy selector (not for computed fields)
      let strategySelect = null;
      if (f.type !== 'computed') {
        strategySelect = document.createElement('select');
        strategySelect.className = 'field-strategy';
        strategySelect.innerHTML = `
          <option value="first" ${f.strategy === 'first' ? 'selected' : ''}>First</option>
          <option value="last" ${f.strategy === 'last' ? 'selected' : ''}>Last</option>
          <option value="all" ${f.strategy === 'all' ? 'selected' : ''}>All</option>
        `;
        strategySelect.addEventListener('change', (e) => {
          fields[idx].strategy = e.target.value;
          buildRulesPreview();
        });
      }
      
      // Remove button
      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.innerHTML = '✕';
      removeBtn.title = 'Remove field';
      removeBtn.className = 'field-remove';
      removeBtn.addEventListener('click', () => { 
        fields.splice(idx, 1); 
        renderFields(); 
        buildRulesPreview(); 
      });
      
      fieldCard.appendChild(typeBadge);
      fieldCard.appendChild(fieldInfo);
      if (strategySelect) {
        fieldCard.appendChild(strategySelect);
      }
      fieldCard.appendChild(removeBtn);
      fieldsList.appendChild(fieldCard);
    });
    buildRulesPreview();
  }

  // Wizard modal handlers
  if (addFieldWizardBtn) {
    addFieldWizardBtn.addEventListener('click', () => {
      // Reset wizard inputs
      if (fieldNameInput) fieldNameInput.value = '';
      if (fieldLookForInput) fieldLookForInput.value = '';
      if (fieldFormulaInput) fieldFormulaInput.value = '';
      if (fieldInTableCheckbox) fieldInTableCheckbox.checked = false;
      if (fieldColumnInput) fieldColumnInput.value = '';
      document.querySelectorAll('input[name="fieldType"]').forEach(radio => {
        radio.checked = radio.value === 'text';
      });
      if (fieldStrategySelect) fieldStrategySelect.value = 'first';
      
      // Reset visibility states
      if (fieldFormulaSection) fieldFormulaSection.style.display = 'none';
      if (fieldStrategySection) fieldStrategySection.style.display = 'block';
      if (fieldColumnSection) fieldColumnSection.style.display = 'none';
      if (validationRulesSection) validationRulesSection.style.display = 'none';
      
      // Reset validation checkboxes
      document.querySelectorAll('.validation-checkbox input[type="checkbox"]').forEach(cb => cb.checked = false);
      document.querySelectorAll('.inline-number, .inline-text, .inline-date').forEach(input => input.value = '');
      
      // Show modal
      if (fieldWizardModal) fieldWizardModal.style.display = 'flex';
    });
  }

  if (fieldWizardClose) {
    fieldWizardClose.addEventListener('click', () => {
      if (fieldWizardModal) fieldWizardModal.style.display = 'none';
    });
  }

  if (fieldWizardCancel) {
    fieldWizardCancel.addEventListener('click', () => {
      if (fieldWizardModal) fieldWizardModal.style.display = 'none';
    });
  }

  if (fieldWizardSave) {
    fieldWizardSave.addEventListener('click', () => {
      const name = fieldNameInput ? fieldNameInput.value.trim() : '';
      const lookFor = fieldLookForInput ? fieldLookForInput.value.trim() : '';
      const type = document.querySelector('input[name="fieldType"]:checked')?.value || 'text';
      const strategy = fieldStrategySelect ? fieldStrategySelect.value : 'first';
      const inTable = fieldInTableCheckbox?.checked || false;
      const column = inTable && fieldColumnInput ? fieldColumnInput.value.trim() : null;
      const formula = fieldFormulaInput ? fieldFormulaInput.value.trim() : '';

      // Validation
      if (!name) {
        alert('Please enter a field name');
        return;
      }
      
      // For computed fields, require formula and skip lookFor
      if (type === 'computed') {
        if (!formula) {
          alert('Please enter a formula for computed field');
          return;
        }
      } else {
        // For non-computed fields, require lookFor
        if (!lookFor) {
          alert('Please enter text to look for');
          return;
        }
      }
      
      if (inTable && !column) {
        alert('Please specify which column to extract from');
        return;
      }

      // Check for duplicate field names (case-insensitive, trimmed)
      const normalizedName = name.trim().toLowerCase();
      const duplicate = fields.find(f => f.name.trim().toLowerCase() === normalizedName);
      if (duplicate) {
        alert(`A field with the name "${duplicate.name}" already exists. Please use a different name.`);
        return;
      }

      // Collect validation rules based on type
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

      // Add field
      const newField = {
        name,
        type,
        validations
      };
      
      // Add type-specific properties
      if (type === 'computed') {
        newField.formula = formula;
      } else {
        newField.lookFor = lookFor;
        newField.strategy = strategy;
      }
      
      // Add column if specified
      if (column) {
        newField.column = column;
      }
      fields.push(newField);

      // Close modal and refresh
      fieldWizardModal.style.display = 'none';
      renderFields();
    });
  }

  function buildRulesPreview(){
    let rules = { fields: [], validations: {}, calculations: [] };
    
    if (chkSigned && chkSigned.checked) {
      rules.validations.signed = true;
    }
    
    // Must Contain rule
    if (chkMustContain && chkMustContain.checked && mustContainText && mustContainText.value.trim()) {
      rules.validations.must_contain = {
        text: mustContainText.value.trim(),
        case_sensitive: !!(mustContainCaseSensitive && mustContainCaseSensitive.checked)
      };
    }
    
    // Must NOT Contain rule
    if (chkMustNotContain && chkMustNotContain.checked && mustNotContainText && mustNotContainText.value.trim()) {
      rules.validations.must_not_contain = {
        text: mustNotContainText.value.trim(),
        case_sensitive: !!(mustNotContainCaseSensitive && mustNotContainCaseSensitive.checked)
      };
    }
    
    // Page Count rule
    if (chkPageCount && chkPageCount.checked && pageCountValue) {
      rules.validations.page_count = {
        operator: pageCountOperator ? pageCountOperator.value : '>=',
        value: parseInt(pageCountValue.value) || 1
      };
    }
    
    // Convert fields array to object format with lookFor and type
    rules.fields = fields.map(f => {
      const field = {
        name: f.name,
        lookFor: f.lookFor,
        type: f.type,
        strategy: f.strategy || 'first',
        validations: f.validations || [],
        ...(f.column && { column: f.column })
      };
      
      // Include startMarker, endMarker, and occurrence for 'between' strategy
      if (f.strategy === 'between') {
        field.startMarker = f.startMarker;
        field.endMarker = f.endMarker;
        field.occurrence = f.occurrence || 'first';
      }
      
      return field;
    });
    
    // Add calculations if available
    if (typeof getCalculations === 'function') {
      rules.calculations = getCalculations();
    }
    
    // remove empty objects
    if (Object.keys(rules.validations).length === 0) delete rules.validations;
    if (!rules.fields || rules.fields.length===0) delete rules.fields;
    if (!rules.calculations || rules.calculations.length===0) delete rules.calculations;
    
    // Build human-readable summary with HTML formatting
    let summaryHtml = '';
    
    if (Object.keys(rules).length === 0) {
      summaryHtml = '<div class="preview-empty">No rules selected yet. Choose some checks above to get started.</div>';
    } else {
      summaryHtml = '<div class="preview-content">';
      
      // Show validations
      if (rules.validations) {
        const vals = [];
        if (rules.validations.signed) {
          vals.push('Check for Signature');
        }
        if (rules.validations.must_contain) {
          const cs = rules.validations.must_contain.case_sensitive ? ' (case-sensitive)' : '';
          vals.push(`Must contain: "${rules.validations.must_contain.text}"${cs}`);
        }
        if (rules.validations.must_not_contain) {
          const cs = rules.validations.must_not_contain.case_sensitive ? ' (case-sensitive)' : '';
          vals.push(`Must NOT contain: "${rules.validations.must_not_contain.text}"${cs}`);
        }
        if (rules.validations.page_count) {
          const op = rules.validations.page_count.operator === '>=' ? 'At least' :
                     rules.validations.page_count.operator === '<=' ? 'At most' : 'Exactly';
          vals.push(`Page count: ${op} ${rules.validations.page_count.value} page(s)`);
        }
        
        if (vals.length) {
          summaryHtml += '<div class="preview-section">';
          summaryHtml += '<div class="preview-label">Document Checks:</div>';
          summaryHtml += '<ul class="preview-list">';
          vals.forEach(v => summaryHtml += `<li>${v}</li>`);
          summaryHtml += '</ul>';
          summaryHtml += '</div>';
        }
      }
      
      // Show fields to extract
      if (rules.fields && rules.fields.length) {
        summaryHtml += '<div class="preview-section">';
        summaryHtml += '<div class="preview-label">Information to Extract:</div>';
        summaryHtml += '<div class="preview-field-list">';
        rules.fields.forEach(field => {
          const strategyLabel = field.strategy === 'first' ? 'first' : 
                               field.strategy === 'last' ? 'last' : 'all';
          const typeLabel = field.type.charAt(0).toUpperCase() + field.type.slice(1);
          
          // Build validation rules description
          let validationsDesc = '';
          if (field.validations && field.validations.length > 0) {
            const valStrs = field.validations.map(v => {
              if (v.type === 'minLength') return `min ${v.value} chars`;
              if (v.type === 'maxLength') return `max ${v.value} chars`;
              if (v.type === 'pattern') return `pattern: ${v.value}`;
              if (v.type === 'min') return `min ${v.value}`;
              if (v.type === 'max') return `max ${v.value}`;
              if (v.type === 'equals') return `equals ${v.value}`;
              if (v.type === 'before') return `before ${v.value}`;
              if (v.type === 'after') return `after ${v.value}`;
              return '';
            }).filter(s => s);
            if (valStrs.length) {
              validationsDesc = ` <span class="preview-validation-rules">• ${valStrs.join(' • ')}</span>`;
            }
          }
          
          // Determine the occurrence label for between strategy
          let occurrenceLabel = strategyLabel;
          if (field.strategy === 'between' && field.occurrence) {
            occurrenceLabel = field.occurrence === 'first' ? 'first match' : 'all matches';
          }
          
          // Build the field description based on strategy
          let fieldDescription = '';
          if (field.strategy === 'between') {
            fieldDescription = `<div class="preview-field-lookfor">Between: "${escapeHtml(field.startMarker || '')}" and "${escapeHtml(field.endMarker || '')}" (${occurrenceLabel})</div>`;
          } else {
            fieldDescription = `<div class="preview-field-lookfor">Look for: "${escapeHtml(field.lookFor)}"</div>`;
          }
          
          summaryHtml += `<div class="preview-field-item">
            <strong>${escapeHtml(field.name)}</strong> 
            <span class="preview-field-meta">(${typeLabel}, ${field.strategy === 'between' ? 'between' : strategyLabel})</span>${validationsDesc}
            ${fieldDescription}
          </div>`;
        });
        summaryHtml += '</div>';
        summaryHtml += '</div>';
      }
      
      // Calculations section
      if (rules.calculations && rules.calculations.length > 0) {
        summaryHtml += '<div class="preview-section">';
        summaryHtml += '<div class="preview-label">Calculations:</div>';
        summaryHtml += '<div class="preview-field-list">';
        rules.calculations.forEach(calc => {
          summaryHtml += `<div class="preview-field-item" style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border-left: 3px solid #10b981;">
            <strong>${escapeHtml(calc.name)}</strong>
            <div class="preview-field-lookfor" style="font-family: 'Courier New', monospace; font-size: 13px;">= ${escapeHtml(calc.formula)}</div>
          </div>`;
        });
        summaryHtml += '</div>';
        summaryHtml += '</div>';
      }
      
      summaryHtml += '</div>';
    }
    
    rulesPreview.innerHTML = summaryHtml;
    
    // Store a simple text version for form submission
    let textSummary = [];
    if (rules.validations) {
      const vals = [];
      if (rules.validations.signed) vals.push('signed');
      if (vals.length) textSummary.push('Checks: ' + vals.join(', '));
    }
    if (rules.fields && rules.fields.length) {
      const fieldNames = rules.fields.map(f => {
        const field = typeof f === 'string' ? {name: f, strategy: 'first'} : f;
        const strat = field.strategy === 'first' ? 'first' : 
                     field.strategy === 'last' ? 'last' : 'all';
        return `${field.name} (${strat})`;
      });
      textSummary.push('Extract: ' + fieldNames.join(', '));
    }
    rulesTextarea.value = textSummary.join(' | ') || 'No rules selected';
    
    // Store canonical JSON for backend
  try { rulesTextarea.dataset.json = JSON.stringify(rules); } catch(e) { rulesTextarea.dataset.json = '{}'; }
  
  // Enable/disable "Continue to Validation" button based on rules
  const continueBtn = document.getElementById('continueToValidate');
  const hasRules = Object.keys(rules).length > 0;
  if (continueBtn) {
    continueBtn.disabled = !hasRules;
    if (hasRules) {
      continueBtn.classList.remove('btn-disabled');
    } else {
      continueBtn.classList.add('btn-disabled');
    }
  }
  
  // Notify other parts of the app (frontend) that rules changed so UI can update (button label, summaries, etc.)
  try { document.dispatchEvent(new CustomEvent('rulesUpdated', { detail: rules })); } catch (e) { /* non-fatal */ }
  }
  
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // return a canonical rules payload (object) for saving/submitting
  function getRulesPayload(){
    let rules = { fields: [], validations: {} };
    
    if (chkSigned && chkSigned.checked) {
      rules.validations.signed = true;
    }
    
    if (chkMustContain && chkMustContain.checked && mustContainText && mustContainText.value.trim()) {
      rules.validations.must_contain = {
        text: mustContainText.value.trim(),
        case_sensitive: !!(mustContainCaseSensitive && mustContainCaseSensitive.checked)
      };
    }
    
    if (chkMustNotContain && chkMustNotContain.checked && mustNotContainText && mustNotContainText.value.trim()) {
      rules.validations.must_not_contain = {
        text: mustNotContainText.value.trim(),
        case_sensitive: !!(mustNotContainCaseSensitive && mustNotContainCaseSensitive.checked)
      };
    }
    
    if (chkPageCount && chkPageCount.checked && pageCountValue) {
      rules.validations.page_count = {
        operator: pageCountOperator ? pageCountOperator.value : '>=',
        value: parseInt(pageCountValue.value) || 1
      };
    }
    
    // Use global fields array from field-wizard.js
    const fields = window.fields || [];
    rules.fields = fields.map(f => {
      if (typeof f === 'string') {
        return {name: f, strategy: 'first'};
      }
      const field = {
        name: f.name, 
        lookFor: f.lookFor || f.name,  // Use lookFor if available, otherwise fall back to name
        type: f.type || 'text',         // Include field type
        strategy: f.strategy || 'first',
        validations: f.validations || []  // Include field-level validations
      };
      
      // Include startMarker and endMarker for 'between' strategy
      if (f.strategy === 'between') {
        field.startMarker = f.startMarker;
        field.endMarker = f.endMarker;
      }
      
      return field;
    });
    
    if (Object.keys(rules.validations).length === 0) delete rules.validations;
    if (!rules.fields || rules.fields.length===0) delete rules.fields;
    
    // Include calculations if present
    if (typeof window.getCalculations === 'function') {
      const calcs = window.getCalculations();
      if (calcs && calcs.length > 0) {
        rules.calculations = calcs;
      }
    }
    
    return rules;
  }

  // Listen for changes to rebuild preview
  [chkSigned, chkMustContain, chkMustNotContain, chkPageCount,
   mustContainText, mustNotContainText, mustContainCaseSensitive, mustNotContainCaseSensitive,
   pageCountOperator, pageCountValue
  ].forEach(el => {
    if (el) el.addEventListener('change', buildRulesPreview);
    if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
      el.addEventListener('input', buildRulesPreview);
    }
  });

  // initial render
  renderFields();
  buildRulesPreview();
  
  // Initialize "Continue to Validation" button state
  const continueBtn = document.getElementById('continueToValidate');
  if (continueBtn) {
    continueBtn.disabled = true; // Disabled by default until rules are added
  }

  // Ensure rules are up-to-date before the form submits
  const form = document.getElementById('uploadForm');
  if (form){
    form.addEventListener('submit', (ev) => {
      buildRulesPreview();
    });
  }

  // Save ruleset button
  const saveBtn = document.getElementById('saveRulesetBtn');
  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const modal = document.getElementById('saveRulesetModal');
      const nameInput = document.getElementById('rulesetNameInput');
      const modalClose = document.getElementById('modalClose');
      const modalCancel = document.getElementById('modalCancel');
      const modalSave = document.getElementById('modalSave');
      
      if (!modal || !nameInput) return;
      
      // Show modal
      modal.style.display = 'flex';
      nameInput.value = '';
      nameInput.focus();
      
      // Close handlers
      const closeModal = () => {
        modal.style.display = 'none';
      };
      
      modalClose.onclick = closeModal;
      modalCancel.onclick = closeModal;
      modal.querySelector('.modal-overlay').onclick = closeModal;
      
      // Save handler
      modalSave.onclick = async () => {
        const name = nameInput.value.trim();
        if (!name) {
          nameInput.style.borderColor = 'var(--error)';
          return;
        }
        
        const payload = getRulesPayload();
        console.log('Saving ruleset with payload:', payload);
        
        try {
          const res = await fetch('/api/v1/rulesets/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name, rules: payload })
          });
          
          if (!res.ok) throw new Error('Failed to save ruleset');
          
          const saved = await res.json();
          console.log('Ruleset saved:', saved);
          
          closeModal();
          
          // Show success message
          const successMsg = document.createElement('div');
          successMsg.className = 'status-message success-message';
          successMsg.textContent = `✓ Ruleset "${name}" saved successfully!`;
          successMsg.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:10000;background:#10b981;color:white;padding:12px 20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:14px;';
          document.body.appendChild(successMsg);
          setTimeout(() => successMsg.remove(), 3000);
          
          // Refresh saved rulesets list and auto-select the newly saved one
          await loadSavedRulesets();
          
          // Auto-select the newly saved ruleset in the dropdown (with small delay for rendering)
          setTimeout(() => {
            const rulesetSelect = document.getElementById('rulesetSelect');
            if (rulesetSelect && saved.id) {
              rulesetSelect.value = saved.id;
              // Highlight it briefly
              rulesetSelect.style.background = '#e8f4fd';
              setTimeout(() => {
                rulesetSelect.style.background = '';
              }, 1500);
            }
          }, 100);
          
        } catch (err) {
          console.error('Error saving ruleset:', err);
          
          // Show error message
          const errorMsg = document.createElement('div');
          errorMsg.textContent = '✗ Failed to save ruleset';
          errorMsg.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:10000;background:#dc2626;color:white;padding:12px 20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:14px;';
          document.body.appendChild(errorMsg);
          setTimeout(() => errorMsg.remove(), 3000);
        }
      };
    });
  }

  // Load saved rulesets
  async function loadSavedRulesets() {
    const container = document.getElementById('savedRulesetsList');
    if (!container) return;
    
    try {
      const res = await fetch('/api/v1/rulesets/');
      if (!res.ok) throw new Error('Failed to load rulesets');
      
      const rulesets = await res.json();
      
      if (!rulesets || rulesets.length === 0) {
        container.innerHTML = '<div class="no-rulesets">No saved rulesets yet. Create and save your first ruleset above!</div>';
        return;
      }
      
      container.innerHTML = '';
      
      // Create label
      const label = document.createElement('div');
      label.style.cssText = 'margin-bottom: 0.5rem; color: #666; font-size: 0.9rem;';
      label.textContent = 'Select a ruleset to load or create new rules above';
      container.appendChild(label);
      
      // Create dropdown
      const selectWrapper = document.createElement('div');
      selectWrapper.style.cssText = 'display: flex; gap: 0.5rem; align-items: center;';
      
      const select = document.createElement('select');
      select.id = 'rulesetSelect';
      select.className = 'form-input';
      select.style.cssText = 'flex: 1; font-size: 1rem; padding: 0.6rem;';
      
      // Add placeholder option
      const placeholderOption = document.createElement('option');
      placeholderOption.value = '';
      placeholderOption.textContent = 'Select a saved ruleset...';
      placeholderOption.disabled = true;
      placeholderOption.selected = true;
      select.appendChild(placeholderOption);
      
      // Add rulesets as options
      rulesets.forEach(ruleset => {
        const option = document.createElement('option');
        option.value = ruleset.id;
        option.textContent = ruleset.name;
        option.dataset.ruleset = JSON.stringify(ruleset);
        select.appendChild(option);
      });
      
      // Load button
      const loadBtn = document.createElement('button');
      loadBtn.className = 'btn btn-primary';
      loadBtn.textContent = 'Load';
      loadBtn.onclick = () => {
        const selectedOption = select.options[select.selectedIndex];
        if (selectedOption && selectedOption.value) {
          const ruleset = JSON.parse(selectedOption.dataset.ruleset);
          loadRuleset(ruleset);
        }
      };
      
      // Delete button
      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'btn btn-ghost';
      deleteBtn.textContent = 'Delete';
      deleteBtn.onclick = () => {
        const selectedOption = select.options[select.selectedIndex];
        if (selectedOption && selectedOption.value) {
          const ruleset = JSON.parse(selectedOption.dataset.ruleset);
          deleteRuleset(ruleset.id, ruleset.name);
        }
      };
      
      selectWrapper.appendChild(select);
      selectWrapper.appendChild(loadBtn);
      selectWrapper.appendChild(deleteBtn);
      container.appendChild(selectWrapper);
      
    } catch (err) {
      console.error('Error loading rulesets:', err);
      container.innerHTML = '<div class="error-message">Failed to load saved rulesets</div>';
    }
  }

  function loadRuleset(ruleset) {
    console.log('loadRuleset called with:', ruleset);
    const rules = ruleset.rules || {};
    console.log('Rules to load:', rules);
    
    // Load validations
    if (chkSigned) chkSigned.checked = !!rules.validations?.signed;
    
    if (rules.validations?.must_contain) {
      if (chkMustContain) chkMustContain.checked = true;
      if (mustContainText) mustContainText.value = rules.validations.must_contain.text || '';
      if (mustContainCaseSensitive) mustContainCaseSensitive.checked = !!rules.validations.must_contain.case_sensitive;
    }
    
    if (rules.validations?.must_not_contain) {
      if (chkMustNotContain) chkMustNotContain.checked = true;
      if (mustNotContainText) mustNotContainText.value = rules.validations.must_not_contain.text || '';
      if (mustNotContainCaseSensitive) mustNotContainCaseSensitive.checked = !!rules.validations.must_not_contain.case_sensitive;
    }
    
    if (rules.validations?.page_count) {
      if (chkPageCount) chkPageCount.checked = true;
      if (pageCountOperator) pageCountOperator.value = rules.validations.page_count.operator || '>=';
      if (pageCountValue) pageCountValue.value = rules.validations.page_count.value || 1;
    }
    
    // Load fields - preserve all properties
    // Clear the existing array and populate it (maintains reference)
    fields.length = 0;
    const loadedFields = (rules.fields || []).map(f => {
      if (typeof f === 'string') {
        return {name: f, lookFor: '', type: 'text', strategy: 'first', validations: []};
      }
      const field = {
        name: f.name || '',
        lookFor: f.lookFor || '',
        type: f.type || 'text',
        strategy: f.strategy || 'first',
        validations: f.validations || [],
        ...(f.column && { column: f.column })
      };
      
      // Preserve startMarker, endMarker, and occurrence for 'between' strategy
      if (f.strategy === 'between') {
        field.startMarker = f.startMarker || '';
        field.endMarker = f.endMarker || '';
        field.occurrence = f.occurrence || 'first';
      }
      
      return field;
    });
    
    // Push all loaded fields into the existing array
    fields.push(...loadedFields);
    
    console.log('Fields loaded:', fields);
    console.log('window.fields:', window.fields);
    console.log('Same reference?', fields === window.fields);
    
    // Load calculations if present
    if (rules.calculations) {
      if (typeof setCalculations === 'function') {
        setCalculations(rules.calculations);
      } else if (typeof window.setCalculations === 'function') {
        window.setCalculations(rules.calculations);
      }
    } else {
      // Clear calculations if none in the ruleset
      if (typeof setCalculations === 'function') {
        setCalculations([]);
      } else if (typeof window.setCalculations === 'function') {
        window.setCalculations([]);
      }
    }
    
    renderFields();
    console.log('About to call buildRulesPreview');
    buildRulesPreview();
    console.log('buildRulesPreview completed');
    
    // CRITICAL: Ensure the Continue button is properly enabled after loading
    setTimeout(() => {
      const continueBtn = document.getElementById('continueToValidate');
      const rulesTextarea = document.getElementById('rules');
      if (continueBtn && rulesTextarea && rulesTextarea.dataset.json) {
        try {
          const rules = JSON.parse(rulesTextarea.dataset.json);
          const hasRules = Object.keys(rules).length > 0;
          continueBtn.disabled = !hasRules;
          if (hasRules) {
            continueBtn.classList.remove('btn-disabled');
          }
        } catch (e) {
          console.error('Error checking rules after load:', e);
        }
      }
    }, 100);
    
    // Show success message
    const successMsg = document.createElement('div');
    successMsg.className = 'status-message success-message';
    successMsg.textContent = `✓ Loaded ruleset "${ruleset.name}"`;
    successMsg.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:10000;background:#10b981;color:white;padding:12px 20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:14px;';
    document.body.appendChild(successMsg);
    setTimeout(() => successMsg.remove(), 2000);
  }

  function showDeleteConfirmation(id, name) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10000;';
    
    // Create modal content
    const content = document.createElement('div');
    content.style.cssText = 'background:white;padding:24px;border-radius:8px;max-width:400px;box-shadow:0 20px 60px rgba(0,0,0,0.3);';
    
    const title = document.createElement('h3');
    title.textContent = 'Delete Ruleset';
    title.style.cssText = 'margin:0 0 12px 0;color:#dc2626;font-size:18px;';
    
    const message = document.createElement('p');
    message.textContent = `Are you sure you want to delete "${name}"? This action cannot be undone.`;
    message.style.cssText = 'margin:0 0 20px 0;color:#666;line-height:1.5;';
    
    const buttonRow = document.createElement('div');
    buttonRow.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;';
    
    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancel';
    cancelBtn.className = 'btn btn-secondary';
    cancelBtn.onclick = () => modal.remove();
    
    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = 'Delete';
    deleteBtn.style.cssText = 'background:#dc2626;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:14px;font-weight:500;';
    deleteBtn.onclick = async () => {
      modal.remove();
      await performDelete(id, name);
    };
    
    buttonRow.appendChild(cancelBtn);
    buttonRow.appendChild(deleteBtn);
    content.appendChild(title);
    content.appendChild(message);
    content.appendChild(buttonRow);
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    // Close on overlay click
    modal.onclick = (e) => {
      if (e.target === modal) modal.remove();
    };
  }

  async function performDelete(id, name) {
    
    try {
      const res = await fetch(`/api/v1/rulesets/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete ruleset');
      
      // Show success message
      const successMsg = document.createElement('div');
      successMsg.className = 'status-message success-message';
      successMsg.textContent = `✓ Deleted ruleset "${name}"`;
      successMsg.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:10000;background:#10b981;color:white;padding:12px 20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:14px;';
      document.body.appendChild(successMsg);
      setTimeout(() => successMsg.remove(), 2000);
      
      // Refresh list
      loadSavedRulesets();
      
    } catch (err) {
      console.error('Error deleting ruleset:', err);
      
      // Show error message
      const errorMsg = document.createElement('div');
      errorMsg.textContent = '✗ Failed to delete ruleset';
      errorMsg.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:10000;background:#dc2626;color:white;padding:12px 20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:14px;';
      document.body.appendChild(errorMsg);
      setTimeout(() => errorMsg.remove(), 3000);
    }
  }
  
  function deleteRuleset(id, name) {
    showDeleteConfirmation(id, name);
  }

  // Reset builder function for "Validate More" button
  function resetBuilder() {
    // Clear all fields
    fields.length = 0;
    
    // Clear calculations using the proper setter if available
    if (typeof window.setCalculations === 'function') {
      window.setCalculations([]);
    } else if (typeof window.calculations !== 'undefined') {
      window.calculations = [];
    }
    
    // Reset all validation checkboxes
    const checkboxes = [
      'chkSignature',
      'chkMustContain',
      'chkMustNotContain',
      'chkPageCount'
    ];
    
    checkboxes.forEach(id => {
      const checkbox = document.getElementById(id);
      if (checkbox) checkbox.checked = false;
    });
    
    // Clear all text inputs
    const textInputs = [
      'mustContainText',
      'mustNotContainText',
      'pageCountValue'
    ];
    
    textInputs.forEach(id => {
      const input = document.getElementById(id);
      if (input) input.value = '';
    });
    
    // Reset dropdown selectors
    const pageCountOperator = document.getElementById('pageCountOperator');
    if (pageCountOperator) pageCountOperator.value = '>=';
    
    // Reset UI
    renderFields();
    buildRulesPreview();
    
    // Reset dropdown selection if it exists
    const rulesetSelect = document.getElementById('rulesetSelect');
    if (rulesetSelect) {
      rulesetSelect.selectedIndex = 0;  // Reset to placeholder
    }
    
    console.log('Builder reset - all fields, calculations, and validations cleared');
  }
  
  // Load saved rulesets on init
  loadSavedRulesets();

  // Export functions for use by other scripts
  window.buildRulesPreview = buildRulesPreview;
  window.loadRuleset = loadRuleset;
  window.resetBuilder = resetBuilder;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
})();
