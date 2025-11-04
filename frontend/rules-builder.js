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
  const newFieldInput = document.getElementById('newField');
  const addFieldBtn = document.getElementById('addFieldBtn');
  const fieldList = document.getElementById('fieldList');

  // Complex panel elements
  const aiPrompt = document.getElementById('aiPrompt');
  const aiGenerate = document.getElementById('aiGenerate');
  const aiStatus = document.getElementById('aiStatus');
  const aiPreview = document.getElementById('aiPreview');

  let fields = [];

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
      li.className = 'chip';
      li.textContent = f;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.innerHTML = '✕';
      btn.title = 'Remove';
      btn.addEventListener('click', () => { fields.splice(idx,1); renderFields(); buildRulesPreview(); });
      li.appendChild(btn);
      fieldList.appendChild(li);
    });
      // update suggestion visibility
      document.querySelectorAll('.suggestion').forEach(btn => {
        btn.disabled = fields.length >=5 || fields.includes(btn.textContent);
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
    // basic sanitization: alphanum + underscore
    const safe = v.replace(/[^a-zA-Z0-9_]/g, '_');
    if (fields.includes(safe)) {
      newFieldInput.value = '';
      return;
    }
    fields.push(safe);
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
      rules.fields = fields.slice(0,5);
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
    // present a human-readable summary for non-technical users
    let summary = [];
    if (rules.validations) {
      const vals = [];
      if (rules.validations.signed) vals.push('signed');
      if (rules.validations.dated) vals.push('dated');
      if (rules.validations.signed_and_dated) vals.push('signed & dated');
      if (vals.length) summary.push('Require: ' + vals.join(', '));
    }
    if (rules.fields && rules.fields.length) {
      summary.push('Extract fields: ' + rules.fields.join(', '));
    }
    let pretty;
    if (Object.keys(rules).length === 0) {
      pretty = 'No rules selected yet. Choose some checks above to get started.';
    } else if (summary.length) {
      pretty = summary.join(' • ');
    } else {
      pretty = JSON.stringify(rules);
    }
    rulesPreview.textContent = pretty;
    // keep the textarea user-facing but also store a canonical JSON string in data for saving
    rulesTextarea.value = pretty;
    try { rulesTextarea.dataset.json = JSON.stringify(rules); } catch(e) { rulesTextarea.dataset.json = '{}'; }
  }

  // return a canonical rules payload (object) for saving/submitting
  function getRulesPayload(){
    const activeTab = document.querySelector('.tabs button.active').dataset.tab;
    if (activeTab === 'simple'){
      const payload = { validations: {}, fields: fields.slice(0,5) };
      if (chkSigned && chkSigned.checked) payload.validations.signed = true;
      if (chkDated && chkDated.checked) payload.validations.dated = true;
      if (chkSignedAndDated && chkSignedAndDated.checked) payload.validations.signed_and_dated = true;
      // prune empty
      if (!payload.fields || payload.fields.length === 0) delete payload.fields;
      if (Object.keys(payload.validations).length === 0) delete payload.validations;
      return payload;
    }
    // complex: prefer aiPreview.dataset.json if present
    try{
      const j = JSON.parse(aiPreview.dataset.json || '{}');
      return j;
    }catch(e){
      return {};
    }
  }

  // wire inputs to preview
  [chkSigned, chkDated, chkSignedAndDated].forEach(el => el && el.addEventListener('change', buildRulesPreview));

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
      // show preview and store JSON for preview tab
      aiPreview.style.display = 'block';
      const pretty = JSON.stringify(j, null, 2);
      aiPreview.textContent = pretty;
      aiPreview.dataset.json = JSON.stringify(j);
      aiStatus.textContent = '✓ Rules created successfully!';
      aiStatus.style.color = 'var(--success)';
      // switch to complex tab preview
      document.querySelector('.tabs button[data-tab="complex"]').classList.add('active');
      document.querySelector('.tabs button[data-tab="simple"]').classList.remove('active');
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
      const name = prompt('Give your rules a name so you can use them again later:');
      if (!name) return;
      const payload = getRulesPayload();
      saveBtn.disabled = true;
      try{
        const res = await fetch('/api/v1/rulesets', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, rules: payload }) });
        if (!res.ok) {
          const txt = await res.text();
          alert('Unable to save: ' + txt);
        } else {
          const j = await res.json();
          alert('✓ Your rules have been saved as "' + j.name + '"');
        }
      }catch(err){
        alert('Error saving rules: ' + err.message);
      } finally { saveBtn.disabled = false; }
    });
  }
  // programmatic reset for the builder
  function resetBuilder(){
    fields = [];
    renderFields();
    if (chkSigned) chkSigned.checked = false;
    if (chkDated) chkDated.checked = false;
    if (chkSignedAndDated) chkSignedAndDated.checked = false;
    if (newFieldInput) newFieldInput.value = '';
    if (aiPrompt) aiPrompt.value = '';
    if (aiPreview) { aiPreview.style.display = 'none'; aiPreview.textContent = ''; aiPreview.dataset.json = ''; }
    if (aiStatus) { aiStatus.textContent = ''; }
    buildRulesPreview();
  }
  window.resetBuilder = resetBuilder;
  // helper for history to read current fields
  window.getHistoryFields = () => fields.slice();

  // History: localStorage-backed recent submissions
  const HISTORY_KEY = 'valido_history_v1';
  function getHistory(){ try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); } catch(e){ return []; } }
  function saveHistory(list){ try { localStorage.setItem(HISTORY_KEY, JSON.stringify(list)); } catch(e){} }
  function pushHistory(entry){ const h = getHistory(); h.unshift(entry); if (h.length>50) h.pop(); saveHistory(h); renderHistory(); }
  window.pushHistory = pushHistory;

  function renderHistory(){
    const container = document.getElementById('historyList');
    if (!container) return;
    const items = getHistory();
    container.innerHTML = '';
    if (!items.length) { 
      container.innerHTML = '<div class="helper" style="text-align:center;padding:40px 20px;color:var(--text-tertiary)">No recent validations yet. Once you validate documents, they\'ll appear here.</div>'; 
      return; 
    }
    items.forEach((it, idx) => {
      const card = document.createElement('div');
      card.className = 'card';
      card.style.marginBottom = '12px';
      const ts = new Date(it.timestamp).toLocaleString();
      const fileCount = it.files.length;
      const fileText = fileCount === 1 ? '1 document' : `${fileCount} documents`;
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap">
          <div style="flex:1;min-width:200px">
            <div style="font-weight:600;color:var(--text-primary);margin-bottom:4px">${fileText}</div>
            <div class="helper" style="margin-bottom:4px">${it.rulesSummary||'No rules'}</div>
            <div class="helper" style="font-size:12px;color:var(--text-tertiary)">${ts}</div>
          </div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-secondary" data-idx="${idx}" data-action="rerun" style="padding:8px 14px">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M14 8C14 11.3137 11.3137 14 8 14C4.68629 14 2 11.3137 2 8C2 4.68629 4.68629 2 8 2C9.5 2 10.8 2.6 11.7 3.6M12 2V5H9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Re-run
            </button>
            <button class="btn btn-ghost" data-idx="${idx}" data-action="delete" style="padding:8px 14px">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M5 5L11 11M5 11L11 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        </div>
      `;
      container.appendChild(card);
    });
    // wire buttons
    container.querySelectorAll('button[data-action]').forEach(b => {
      b.addEventListener('click', (ev) => {
        const action = b.dataset.action;
        const idx = parseInt(b.dataset.idx,10);
        const items = getHistory();
        const item = items[idx];
        if (!item) return;
        if (action === 'delete'){
          if (confirm('Remove this validation from history?')) {
            items.splice(idx,1); 
            saveHistory(items); 
            renderHistory();
          }
        } else if (action === 'rerun'){
          // populate builder with saved rules and switch to upload tab
          if (item.mode === 'complex'){ 
            document.querySelector('.tabs button[data-tab="complex"]')?.click(); 
            if (aiPrompt) aiPrompt.value = item.prompt || ''; 
          }
          if (item.mode === 'simple'){
            document.querySelector('.tabs button[data-tab="simple"]').click();
            if (chkSigned) chkSigned.checked = !!item.validations?.signed;
            if (chkDated) chkDated.checked = !!item.validations?.dated;
            if (chkSignedAndDated) chkSignedAndDated.checked = !!item.validations?.signed_and_dated;
            if (item.fields) { fields = item.fields.slice(0,5); renderFields(); }
          }
          // scroll to upload section and focus file input
          document.getElementById('navUpload').click();
          const fileInput = document.getElementById('files'); if (fileInput) fileInput.focus();
        }
      });
    });
  }
  window.renderHistory = renderHistory;
  // initial render
  renderHistory();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
})();
