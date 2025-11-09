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
  const fieldsList = document.getElementById('fieldsList');

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

  let fields = [];  // Array of {name, lookFor, type, strategy, validations}

  function renderFields(){
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
      fieldLookFor.textContent = f.lookFor;
      
      fieldInfo.appendChild(fieldName);
      fieldInfo.appendChild(fieldLookFor);
      
      // Strategy selector
      const strategySelect = document.createElement('select');
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
      fieldCard.appendChild(strategySelect);
      fieldCard.appendChild(removeBtn);
      fieldsList.appendChild(fieldCard);
    });
    buildRulesPreview();
  }

  // Wizard modal handlers
  if (addFieldWizardBtn) {
    addFieldWizardBtn.addEventListener('click', () => {
      // Reset wizard inputs
      fieldNameInput.value = '';
      fieldLookForInput.value = '';
      document.querySelectorAll('input[name="fieldType"]').forEach(radio => {
        radio.checked = radio.value === 'text';
      });
      fieldStrategySelect.value = 'first';
      
      // Reset and hide validation rules
      validationRulesSection.style.display = 'none';
      document.querySelectorAll('.validation-checkbox input[type="checkbox"]').forEach(cb => cb.checked = false);
      document.querySelectorAll('.inline-number, .inline-text, .inline-date').forEach(input => input.value = '');
      
      // Show modal
      fieldWizardModal.style.display = 'flex';
    });
  }

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

  if (fieldWizardSave) {
    fieldWizardSave.addEventListener('click', () => {
      const name = fieldNameInput.value.trim();
      const lookFor = fieldLookForInput.value.trim();
      const type = document.querySelector('input[name="fieldType"]:checked')?.value || 'text';
      const strategy = fieldStrategySelect.value;

      // Validation
      if (!name) {
        alert('Please enter a field name');
        return;
      }
      if (!lookFor) {
        alert('Please enter text to look for');
        return;
      }

      // Check for duplicate field names
      const exists = fields.some(f => f.name === name);
      if (exists) {
        alert('A field with this name already exists');
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
      fields.push({
        name,
        lookFor,
        type,
        strategy,
        validations
      });

      // Close modal and refresh
      fieldWizardModal.style.display = 'none';
      renderFields();
    });
  }


  function buildRulesPreview(){
    let rules = { fields: [], validations: {} };
    
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
    rules.fields = fields.map(f => ({
      name: f.name,
      lookFor: f.lookFor,
      type: f.type,
      strategy: f.strategy || 'first',
      validations: f.validations || []
    }));
    
    // remove empty objects
    if (Object.keys(rules.validations).length === 0) delete rules.validations;
    if (!rules.fields || rules.fields.length===0) delete rules.fields;
    
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
          
          summaryHtml += `<div class="preview-field-item">
            <strong>${escapeHtml(field.name)}</strong> 
            <span class="preview-field-meta">(${typeLabel}, ${strategyLabel})</span>${validationsDesc}
            <div class="preview-field-lookfor">Look for: "${escapeHtml(field.lookFor)}"</div>
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
    
    rules.fields = fields.map(f => {
      if (typeof f === 'string') {
        return {name: f, strategy: 'first'};
      }
      return {
        name: f.name, 
        lookFor: f.lookFor || f.name,  // Use lookFor if available, otherwise fall back to name
        type: f.type || 'text',         // Include field type
        strategy: f.strategy || 'first',
        validations: f.validations || []  // Include field-level validations
      };
    });
    
    if (Object.keys(rules.validations).length === 0) delete rules.validations;
    if (!rules.fields || rules.fields.length===0) delete rules.fields;
    
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
          successMsg.style.cssText = 'position:fixed;top:20px;right:20px;z-index:10000;';
          document.body.appendChild(successMsg);
          setTimeout(() => successMsg.remove(), 3000);
          
          // Refresh saved rulesets list
          loadSavedRulesets();
          
        } catch (err) {
          console.error('Error saving ruleset:', err);
          alert('Failed to save ruleset. Please try again.');
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
      rulesets.forEach(ruleset => {
        const card = document.createElement('div');
        card.className = 'ruleset-card';
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'ruleset-name';
        nameSpan.textContent = ruleset.name;
        
        const btnContainer = document.createElement('div');
        btnContainer.className = 'ruleset-actions';
        
        const loadBtn = document.createElement('button');
        loadBtn.className = 'btn btn-secondary btn-small';
        loadBtn.textContent = 'Load';
        loadBtn.onclick = () => loadRuleset(ruleset);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-ghost btn-small';
        deleteBtn.textContent = 'Delete';
        deleteBtn.onclick = () => deleteRuleset(ruleset.id, ruleset.name);
        
        btnContainer.appendChild(loadBtn);
        btnContainer.appendChild(deleteBtn);
        
        card.appendChild(nameSpan);
        card.appendChild(btnContainer);
        container.appendChild(card);
      });
      
    } catch (err) {
      console.error('Error loading rulesets:', err);
      container.innerHTML = '<div class="error-message">Failed to load saved rulesets</div>';
    }
  }

  function loadRuleset(ruleset) {
    const rules = ruleset.rules || {};
    
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
    fields = (rules.fields || []).map(f => {
      if (typeof f === 'string') {
        return {name: f, lookFor: '', type: 'text', strategy: 'first', validations: []};
      }
      return {
        name: f.name || '',
        lookFor: f.lookFor || '',
        type: f.type || 'text',
        strategy: f.strategy || 'first',
        validations: f.validations || []
      };
    });
    
    renderFields();
    buildRulesPreview();
    
    // Show success message
    const successMsg = document.createElement('div');
    successMsg.className = 'status-message success-message';
    successMsg.textContent = `✓ Loaded ruleset "${ruleset.name}"`;
    successMsg.style.cssText = 'position:fixed;top:20px;right:20px;z-index:10000;';
    document.body.appendChild(successMsg);
    setTimeout(() => successMsg.remove(), 2000);
  }

  async function deleteRuleset(id, name) {
    if (!confirm(`Are you sure you want to delete the ruleset "${name}"?`)) return;
    
    try {
      const res = await fetch(`/api/v1/rulesets/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete ruleset');
      
      // Show success message
      const successMsg = document.createElement('div');
      successMsg.className = 'status-message success-message';
      successMsg.textContent = `✓ Deleted ruleset "${name}"`;
      successMsg.style.cssText = 'position:fixed;top:20px;right:20px;z-index:10000;';
      document.body.appendChild(successMsg);
      setTimeout(() => successMsg.remove(), 2000);
      
      // Refresh list
      loadSavedRulesets();
      
    } catch (err) {
      console.error('Error deleting ruleset:', err);
      alert('Failed to delete ruleset. Please try again.');
    }
  }

  // Load saved rulesets on init
  loadSavedRulesets();

  // Export buildRulesPreview for use by other scripts
  window.buildRulesPreview = buildRulesPreview;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
})();
