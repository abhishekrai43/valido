// Rules builder behaviour: simple/complex tabs, build JSON preview, call AI endpoint for complex
(() => {
  // Initialize after DOM ready to ensure elements exist in all environments
  function init() {
  const tabButtons = document.querySelectorAll('.tabs button');
  const panels = document.querySelectorAll('.panel');
  const rulesPreview = document.getElementById('rulesPreview');
  const rulesTextarea = document.getElementById('rules');
  const showJsonToggle = document.getElementById('showJsonToggle');

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
      pretty = 'No rules selected yet.';
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

  // show/hide raw JSON when user toggles
  if (showJsonToggle) {
    showJsonToggle.addEventListener('change', (ev) => {
      if (ev.target.checked) {
        // show raw JSON in a dialog-like area
        try {
          const json = JSON.parse(rulesTextarea.value || '{}');
          rulesPreview.textContent = JSON.stringify(json, null, 2);
        } catch (e) {
          // leave as-is
        }
      } else {
        buildRulesPreview();
      }
    });
  }

  // wire inputs to preview
  [chkSigned, chkDated, chkSignedAndDated].forEach(el => el && el.addEventListener('change', buildRulesPreview));

  // AI integration
  aiGenerate && aiGenerate.addEventListener('click', async () => {
    const text = (aiPrompt.value || '').trim();
    if (!text) { aiStatus.textContent = 'Please enter instructions for the AI.'; return; }
    aiStatus.innerHTML = 'Calling AI... <span class="ai-spinner" aria-hidden="true"></span>';
    aiGenerate.disabled = true;
    try{
      const res = await fetch('/api/v1/ai/convert', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({text}) });
      if (!res.ok) {
        aiStatus.textContent = 'AI request failed: ' + res.status;
        return;
      }
      const j = await res.json();
      // show preview and store JSON for preview tab
      aiPreview.style.display = 'block';
      const pretty = JSON.stringify(j, null, 2);
      aiPreview.textContent = pretty;
      aiPreview.dataset.json = JSON.stringify(j);
      aiStatus.textContent = 'AI returned rules. Preview below.';
      // switch to complex tab preview
      document.querySelector('.tabs button[data-tab="complex"]').classList.add('active');
      document.querySelector('.tabs button[data-tab="simple"]').classList.remove('active');
      panels.forEach(p => p.style.display = (p.dataset.panel === 'complex') ? 'block' : 'none');
      buildRulesPreview();
    }catch(err){
      aiStatus.textContent = 'AI error: '+err.message;
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
      const name = prompt('Enter a name for this ruleset (unique)');
      if (!name) return;
      const payload = getRulesPayload();
      saveBtn.disabled = true;
      try{
        const res = await fetch('/api/v1/rulesets', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, rules: payload }) });
        if (!res.ok) {
          const txt = await res.text();
          alert('Failed to save ruleset: ' + res.status + '\n' + txt);
        } else {
          const j = await res.json();
          alert('Saved ruleset "' + j.name + '" (id: ' + j.id + ')');
        }
      }catch(err){
        alert('Error saving ruleset: ' + err.message);
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
    if (showJsonToggle) showJsonToggle.checked = false;
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
    if (!items.length) { container.innerHTML = '<div class="helper">No history yet.</div>'; return; }
    items.forEach((it, idx) => {
      const card = document.createElement('div');
      card.className = 'card';
      card.style.marginBottom = '10px';
      const ts = new Date(it.timestamp).toLocaleString();
      card.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;gap:12px"><div><strong>${it.files.join(', ')}</strong><div class="helper">${it.rulesSummary||'No rules'}</div><div class="helper" style="font-size:12px">${ts}</div></div><div style="display:flex;flex-direction:column;gap:6px"><button class="btn btn-primary" data-idx="${idx}" data-action="rerun">Re-run</button><button class="btn btn-ghost" data-idx="${idx}" data-action="delete">Delete</button></div></div>`;
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
          items.splice(idx,1); saveHistory(items); renderHistory();
        } else if (action === 'rerun'){
          // populate builder with saved rules and switch to upload tab
          if (item.mode === 'complex'){ document.querySelector('.tabs button[data-tab="complex"]').click(); if (aiPrompt) aiPrompt.value = item.prompt || ''; }
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
