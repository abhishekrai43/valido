// Rules builder behaviour: simple/complex tabs, build JSON preview, call AI endpoint for complex
(() => {
  // Initialize after DOM ready to ensure elements exist in all environments
  function init() {
  const tabButtons = document.querySelectorAll('.tabs button');
  const panels = document.querySelectorAll('.panel');
  const rulesPreview = document.getElementById('rulesPreview');
  const rulesTextarea = document.getElementById('rules');

  // Simple panel elements
  const chkSigned = document.getElementById('chk_validate_signed');
  const chkDated = document.getElementById('chk_validate_dated');
  const chkSignedAndDated = document.getElementById('chk_validate_signed_and_dated');
  const chkMustContain = document.getElementById('chk_must_contain');
  const mustContainText = document.getElementById('must_contain_text');
  const mustContainCaseSensitive = document.getElementById('must_contain_case_sensitive');
  const chkMustNotContain = document.getElementById('chk_must_not_contain');
  const mustNotContainText = document.getElementById('must_not_contain_text');
  const mustNotContainCaseSensitive = document.getElementById('must_not_contain_case_sensitive');
  const chkPageCount = document.getElementById('chk_page_count');
  const pageCountOperator = document.getElementById('page_count_operator');
  const pageCountValue = document.getElementById('page_count_value');
  const newFieldInput = document.getElementById('newField');
  const addFieldBtn = document.getElementById('addFieldBtn');
  const fieldList = document.getElementById('fieldList');

  // Complex panel elements
  const aiPrompt = document.getElementById('aiPrompt');
  const aiGenerate = document.getElementById('aiGenerate');
  const aiStatus = document.getElementById('aiStatus');
  const aiPreview = document.getElementById('aiPreview');

  let fields = [];  // Array of {name: string, strategy: 'first'|'last'|'all'}

  function switchTab(tabName){
    tabButtons.forEach(b => b.classList.toggle('active', b.dataset.tab === tabName));
    panels.forEach(p => p.style.display = (p.dataset.panel === tabName) ? 'block' : 'none');
    buildRulesPreview();
  }

  tabButtons.forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));

  function renderFields(){
    fieldList.innerHTML = '';
    fields.forEach((f, idx) => {
      const li = document.createElement('li');
      li.className = 'chip field-chip';
      
      const fieldName = typeof f === 'string' ? f : f.name;
      const strategy = typeof f === 'object' && f.strategy ? f.strategy : 'first';
      
      const nameSpan = document.createElement('span');
      nameSpan.textContent = fieldName;
      nameSpan.className = 'field-name';
      
      const strategySelect = document.createElement('select');
      strategySelect.className = 'field-strategy';
      strategySelect.innerHTML = `
        <option value="first" ${strategy === 'first' ? 'selected' : ''}>First</option>
        <option value="last" ${strategy === 'last' ? 'selected' : ''}>Last</option>
        <option value="all" ${strategy === 'all' ? 'selected' : ''}>All</option>
      `;
      strategySelect.addEventListener('change', (e) => {
        if (typeof fields[idx] === 'string') {
          fields[idx] = {name: fields[idx], strategy: e.target.value};
        } else {
          fields[idx].strategy = e.target.value;
        }
        buildRulesPreview();
      });
      
      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.innerHTML = '✕';
      removeBtn.title = 'Remove';
      removeBtn.className = 'field-remove';
      removeBtn.addEventListener('click', () => { fields.splice(idx,1); renderFields(); buildRulesPreview(); });
      
      li.appendChild(nameSpan);
      li.appendChild(strategySelect);
      li.appendChild(removeBtn);
      fieldList.appendChild(li);
    });
      // update suggestion visibility
      document.querySelectorAll('.suggestion').forEach(btn => {
        const btnText = btn.textContent.trim();
        const exists = fields.some(f => (typeof f === 'string' ? f : f.name) === btnText);
        btn.disabled = fields.length >= 5 || exists;
      });
  }

  if (addFieldBtn) {
    addFieldBtn.addEventListener('click', (ev) => {
      ev.preventDefault();
    const v = (newFieldInput.value || '').trim();
    if (!v) return;
    if (fields.length >= 5) {
      alert('Maximum 5 fields allowed');
      return;
    }
    // Keep spaces, parentheses, hyphens - allow most characters except problematic ones
    // Remove only: quotes, backslashes, newlines, tabs
    const safe = v.replace(/["'\\|\n\r\t]/g, '').trim();
    const exists = fields.some(f => (typeof f === 'string' ? f : f.name) === safe);
    if (exists) {
      newFieldInput.value = '';
      return;
    }
    fields.push({name: safe, strategy: 'first'});  // Default to 'first'
    newFieldInput.value = '';
    renderFields();
    buildRulesPreview();
  });
    // allow Enter to add field
    if (newFieldInput) {
      newFieldInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          addFieldBtn.click();
        }
      });
    }
  }

  // suggestion clicks
  document.querySelectorAll('.suggestion').forEach(btn => {
    btn.addEventListener('click', (ev) => {
      ev.preventDefault();
      const val = btn.textContent.trim();
      if (!val) return;
      newFieldInput.value = val;
      addFieldBtn && addFieldBtn.click();
    });
  });

  function buildRulesPreview(){
    const activeTab = document.querySelector('.tabs button.active').dataset.tab;
    let rules = { fields: [], validations: {} };
    if (activeTab === 'simple'){
      rules.validations.signed = !!chkSigned.checked;
      rules.validations.dated = !!chkDated.checked;
      rules.validations.signed_and_dated = !!chkSignedAndDated.checked;
      
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
      
      // Convert fields array to object format with strategy
      rules.fields = fields.slice(0,5).map(f => {
        if (typeof f === 'string') return {name: f, strategy: 'first'};
        return {name: f.name, strategy: f.strategy || 'first'};
      });
    } else {
      // complex: try to show last AI preview if present
      try{
        const parsed = JSON.parse(aiPreview.dataset.json || '{}');
        rules = parsed;
      }catch(e){
        rules = { fields: [], validations: {} };
      }
    }
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
        if (rules.validations.signed) vals.push('✓ Check for Signature');
        if (rules.validations.dated) vals.push('✓ Check for Date');
        if (rules.validations.signed_and_dated) vals.push('✓ Check for Signature AND Date');
        if (rules.validations.must_contain) {
          const cs = rules.validations.must_contain.case_sensitive ? ' (case-sensitive)' : '';
          vals.push(`✓ Must contain: "${rules.validations.must_contain.text}"${cs}`);
        }
        if (rules.validations.must_not_contain) {
          const cs = rules.validations.must_not_contain.case_sensitive ? ' (case-sensitive)' : '';
          vals.push(`✓ Must NOT contain: "${rules.validations.must_not_contain.text}"${cs}`);
        }
        if (rules.validations.page_count) {
          const op = rules.validations.page_count.operator === '>=' ? 'At least' :
                     rules.validations.page_count.operator === '<=' ? 'At most' : 'Exactly';
          vals.push(`✓ Page count: ${op} ${rules.validations.page_count.value} page(s)`);
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
        summaryHtml += '<div class="preview-chips">';
        rules.fields.forEach(field => {
          const f = typeof field === 'string' ? {name: field, strategy: 'first'} : field;
          const strategyLabel = f.strategy === 'first' ? 'first' : 
                               f.strategy === 'last' ? 'last' : 'all';
          summaryHtml += `<span class="preview-chip">${escapeHtml(f.name)} <small>(${strategyLabel})</small></span>`;
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
      if (rules.validations.dated) vals.push('dated');
      if (rules.validations.signed_and_dated) vals.push('signed & dated');
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
    const activeTab = document.querySelector('.tabs button.active').dataset.tab;
    if (activeTab === 'simple'){
      // Convert fields to object format with strategy
      const fieldsPayload = fields.slice(0,5).map(f => {
        if (typeof f === 'string') return {name: f, strategy: 'first'};
        return {name: f.name, strategy: f.strategy || 'first'};
      });
      const payload = { validations: {}, fields: fieldsPayload };
      if (chkSigned && chkSigned.checked) payload.validations.signed = true;
      if (chkDated && chkDated.checked) payload.validations.dated = true;
      if (chkSignedAndDated && chkSignedAndDated.checked) payload.validations.signed_and_dated = true;
      
      // Must Contain
      if (chkMustContain && chkMustContain.checked && mustContainText && mustContainText.value.trim()) {
        payload.validations.must_contain = {
          text: mustContainText.value.trim(),
          case_sensitive: !!(mustContainCaseSensitive && mustContainCaseSensitive.checked)
        };
      }
      
      // Must NOT Contain
      if (chkMustNotContain && chkMustNotContain.checked && mustNotContainText && mustNotContainText.value.trim()) {
        payload.validations.must_not_contain = {
          text: mustNotContainText.value.trim(),
          case_sensitive: !!(mustNotContainCaseSensitive && mustNotContainCaseSensitive.checked)
        };
      }
      
      // Page Count
      if (chkPageCount && chkPageCount.checked && pageCountValue) {
        payload.validations.page_count = {
          operator: pageCountOperator ? pageCountOperator.value : '>=',
          value: parseInt(pageCountValue.value) || 1
        };
      }
      
      // prune empty
      if (!payload.fields || payload.fields.length === 0) delete payload.fields;
      if (Object.keys(payload.validations).length === 0) delete payload.validations;
      return payload;
    }
    // complex: prefer aiPrompt.dataset.json if present
    try{
      const j = JSON.parse(aiPrompt.dataset.json || '{}');
      return j;
    }catch(e){
      return {};
    }
  }

  // wire inputs to preview
  [chkSigned, chkDated, chkSignedAndDated, chkMustContain, chkMustNotContain, chkPageCount].forEach(el => el && el.addEventListener('change', buildRulesPreview));
  [mustContainText, mustNotContainText, pageCountOperator, pageCountValue, mustContainCaseSensitive, mustNotContainCaseSensitive].forEach(el => el && el.addEventListener('input', buildRulesPreview));

  // AI integration
  aiGenerate && aiGenerate.addEventListener('click', async () => {
    const text = (aiPrompt.value || '').trim();
    if (!text) { 
      aiStatus.textContent = 'Please describe what you want to check in the text area above.'; 
      aiStatus.style.color = 'var(--error)';
      return; 
    }
    aiStatus.innerHTML = 'Creating your rules... <span class="spinner" style="display:inline-block;width:16px;height:16px;border:2px solid var(--border);border-top-color:var(--primary);border-radius:50%;animation:spin 1s linear infinite;vertical-align:middle;margin-left:4px"></span>';
    aiStatus.style.color = 'var(--text-secondary)';
    aiGenerate.disabled = true;
    try{
      const res = await fetch('/api/v1/ai/convert', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({text}) });
      if (!res.ok) {
        aiStatus.textContent = 'Unable to create rules. Please try again or use Simple Checks.';
        aiStatus.style.color = 'var(--error)';
        return;
      }
      const j = await res.json();
      // Store JSON for building rules
      if (aiPrompt.dataset) {
        aiPrompt.dataset.json = JSON.stringify(j);
      }
      aiStatus.textContent = '✓ Rules created successfully!';
      aiStatus.style.color = 'var(--success)';
      // switch to complex tab preview
      document.querySelector('.tabs button[data-tab="complex"]')?.classList.add('active');
      document.querySelector('.tabs button[data-tab="simple"]')?.classList.remove('active');
      panels.forEach(p => p.style.display = (p.dataset.panel === 'complex') ? 'block' : 'none');
      buildRulesPreview();
    }catch(err){
      aiStatus.textContent = 'Error: ' + err.message;
      aiStatus.style.color = 'var(--error)';
    } finally { aiGenerate.disabled = false; }
  });

  // initial render
  renderFields();
  buildRulesPreview();

  // Ensure rules are up-to-date before the form submits (hook before submit)
  const form = document.getElementById('uploadForm');
  if (form){
    form.addEventListener('submit', (ev) => {
      buildRulesPreview();
      // rulesTextarea already contains JSON
    });
  }

  // Save ruleset button (saves to /api/v1/rulesets)
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
        modalSave.disabled = true;
        modalSave.textContent = 'Saving...';
        
        try {
          const res = await fetch('/api/v1/rulesets/', { 
            method: 'POST', 
            headers: {'Content-Type':'application/json'}, 
            body: JSON.stringify({ name, rules: payload }) 
          });
          
          if (!res.ok) {
            const txt = await res.text();
            alert('Unable to save: ' + txt);
          } else {
            const j = await res.json();
            closeModal();
            // Reload saved rulesets list
            loadSavedRulesets();
            // Show success message
            const successMsg = document.createElement('div');
            successMsg.className = 'success-toast';
            successMsg.textContent = '✓ Rules saved successfully!';
            document.body.appendChild(successMsg);
            setTimeout(() => successMsg.remove(), 3000);
          }
        } catch(err) {
          alert('Error saving rules: ' + err.message);
        } finally {
          modalSave.disabled = false;
          modalSave.textContent = 'Save Rules';
        }
      };
      
      // Enter key to save
      nameInput.onkeydown = (e) => {
        if (e.key === 'Enter') {
          modalSave.click();
        } else if (e.key === 'Escape') {
          closeModal();
        }
      };
    });
  }

  // Load and display saved rulesets
  async function loadSavedRulesets() {
    const container = document.getElementById('savedRulesetsList');
    if (!container) return;

    try {
      const res = await fetch('/api/v1/rulesets/');
      if (!res.ok) {
        container.innerHTML = '<div class="no-rulesets">Unable to load saved rules</div>';
        return;
      }

      const rulesets = await res.json();
      
      if (!rulesets || rulesets.length === 0) {
        container.innerHTML = '<div class="no-rulesets">No saved rules yet. Create some rules and click "Save These Rules" to save them.</div>';
        return;
      }

      // Display rulesets
      container.innerHTML = '';
      rulesets.forEach(ruleset => {
        const item = document.createElement('div');
        item.className = 'ruleset-item';
        
        const nameDiv = document.createElement('div');
        nameDiv.className = 'ruleset-item-name';
        nameDiv.textContent = ruleset.name;
        
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'ruleset-item-actions';
        
        const loadBtn = document.createElement('button');
        loadBtn.textContent = 'Load';
        loadBtn.type = 'button';
        loadBtn.onclick = (e) => {
          e.stopPropagation();
          loadRuleset(ruleset);
        };
        
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.type = 'button';
        deleteBtn.className = 'delete-btn';
        deleteBtn.onclick = async (e) => {
          e.stopPropagation();
          if (!confirm(`Delete ruleset "${ruleset.name}"?`)) return;
          
          try {
            const res = await fetch(`/api/v1/rulesets/${ruleset.id}`, { method: 'DELETE' });
            if (res.ok) {
              loadSavedRulesets(); // Reload list
              const successMsg = document.createElement('div');
              successMsg.className = 'success-toast';
              successMsg.textContent = '✓ Ruleset deleted';
              document.body.appendChild(successMsg);
              setTimeout(() => successMsg.remove(), 3000);
            } else {
              alert('Failed to delete ruleset');
            }
          } catch (err) {
            alert('Error deleting ruleset: ' + err.message);
          }
        };
        
        actionsDiv.appendChild(loadBtn);
        actionsDiv.appendChild(deleteBtn);
        
        item.appendChild(nameDiv);
        item.appendChild(actionsDiv);
        
        // Click anywhere on item to load
        item.onclick = () => loadRuleset(ruleset);
        
        container.appendChild(item);
      });
    } catch (err) {
      container.innerHTML = '<div class="no-rulesets">Error loading saved rules</div>';
      console.error('Error loading rulesets:', err);
    }
  }

  // Load a specific ruleset into the builder
  function loadRuleset(ruleset) {
    if (!ruleset || !ruleset.rules) return;
    
    const rules = ruleset.rules;
    
    // Clear current state
    fields = [];
    if (chkSigned) chkSigned.checked = false;
    if (chkDated) chkDated.checked = false;
    if (chkSignedAndDated) chkSignedAndDated.checked = false;
    if (chkMustContain) chkMustContain.checked = false;
    if (mustContainText) mustContainText.value = '';
    if (mustContainCaseSensitive) mustContainCaseSensitive.checked = false;
    if (chkMustNotContain) chkMustNotContain.checked = false;
    if (mustNotContainText) mustNotContainText.value = '';
    if (mustNotContainCaseSensitive) mustNotContainCaseSensitive.checked = false;
    if (chkPageCount) chkPageCount.checked = false;
    if (pageCountOperator) pageCountOperator.value = '>=';
    if (pageCountValue) pageCountValue.value = '1';
    
    // Load validation checks - support both new format (validations.signed) and legacy format (validate_signed)
    const validations = rules.validations || {};
    if (validations.signed || rules.validate_signed) chkSigned.checked = true;
    if (validations.dated || rules.validate_dated) chkDated.checked = true;
    if (validations.signed_and_dated || rules.validate_signed_and_dated) chkSignedAndDated.checked = true;
    
    // Load must_contain validation
    if (validations.must_contain) {
      if (chkMustContain) chkMustContain.checked = true;
      if (mustContainText) mustContainText.value = validations.must_contain.text || '';
      if (mustContainCaseSensitive) mustContainCaseSensitive.checked = validations.must_contain.case_sensitive || false;
    }
    
    // Load must_not_contain validation
    if (validations.must_not_contain) {
      if (chkMustNotContain) chkMustNotContain.checked = true;
      if (mustNotContainText) mustNotContainText.value = validations.must_not_contain.text || '';
      if (mustNotContainCaseSensitive) mustNotContainCaseSensitive.checked = validations.must_not_contain.case_sensitive || false;
    }
    
    // Load page_count validation
    if (validations.page_count) {
      if (chkPageCount) chkPageCount.checked = true;
      if (pageCountOperator) pageCountOperator.value = validations.page_count.operator || '>=';
      if (pageCountValue) pageCountValue.value = validations.page_count.value || '1';
    }
    
    // Load fields
    if (rules.fields && Array.isArray(rules.fields)) {
      fields = [...rules.fields];
    }
    
    // Update UI
    renderFields();
    buildRulesPreview();
    
    // Show success message
    const successMsg = document.createElement('div');
    successMsg.className = 'success-toast';
    successMsg.textContent = `✓ Loaded "${ruleset.name}"`;
    document.body.appendChild(successMsg);
    setTimeout(() => successMsg.remove(), 3000);
  }

  // Load saved rulesets on page load
  loadSavedRulesets();
  // programmatic reset for the builder
  function resetBuilder(){
    fields = [];
    renderFields();
    if (chkSigned) chkSigned.checked = false;
    if (chkDated) chkDated.checked = false;
    if (chkSignedAndDated) chkSignedAndDated.checked = false;
    if (chkMustContain) chkMustContain.checked = false;
    if (mustContainText) mustContainText.value = '';
    if (mustContainCaseSensitive) mustContainCaseSensitive.checked = false;
    if (chkMustNotContain) chkMustNotContain.checked = false;
    if (mustNotContainText) mustNotContainText.value = '';
    if (mustNotContainCaseSensitive) mustNotContainCaseSensitive.checked = false;
    if (chkPageCount) chkPageCount.checked = false;
    if (pageCountOperator) pageCountOperator.value = '>=';
    if (pageCountValue) pageCountValue.value = '1';
    if (newFieldInput) newFieldInput.value = '';
    if (aiPrompt) {
      aiPrompt.value = '';
      aiPrompt.dataset.json = '';
    }
    if (aiStatus) { aiStatus.textContent = ''; }
    buildRulesPreview();
  }
  window.resetBuilder = resetBuilder;
  // helper for history to read current fields
  window.getHistoryFields = () => fields.slice();

  // Recent/history feature removed to simplify the UI. No local history is stored.
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
})();
