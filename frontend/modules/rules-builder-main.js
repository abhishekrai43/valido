// Main Rules Builder
// Orchestrates all modules and handles ruleset save/load

document.addEventListener('DOMContentLoaded', () => {
  // Initialize all modules
  if (typeof initFieldWizard === 'function') initFieldWizard();
  if (typeof initValidationsBuilder === 'function') initValidationsBuilder();
  if (typeof initCalculations === 'function') initCalculations();
  
  // Load saved rulesets list
  loadSavedRulesets();
  
  // Initial preview
  if (typeof buildRulesPreview === 'function') buildRulesPreview();
  
  // Setup save ruleset button
  setupSaveRuleset();
});

async function loadSavedRulesets() {
  const savedRulesetsListDiv = document.getElementById('savedRulesetsList');
  if (!savedRulesetsListDiv) return;
  
  try {
    const response = await fetch('/api/v1/rulesets/');
    if (!response.ok) throw new Error('Failed to load rulesets');
    
    const rulesets = await response.json(); // API returns array directly
    
    if (rulesets.length === 0) {
      savedRulesetsListDiv.innerHTML = '<div class="no-rulesets">No saved rulesets yet</div>';
      return;
    }
    
    savedRulesetsListDiv.innerHTML = '';
    rulesets.forEach(ruleset => {
      const card = document.createElement('div');
      card.className = 'ruleset-card';
      
      const name = document.createElement('div');
      name.className = 'ruleset-name';
      name.textContent = ruleset.name;
      
      const actions = document.createElement('div');
      actions.className = 'ruleset-actions';
      
      const loadBtn = document.createElement('button');
      loadBtn.type = 'button';
      loadBtn.className = 'btn btn-ghost btn-small';
      loadBtn.textContent = 'Load';
      loadBtn.onclick = () => {
        if (typeof loadRuleset === 'function') loadRuleset(ruleset);
      };
      
      const deleteBtn = document.createElement('button');
      deleteBtn.type = 'button';
      deleteBtn.className = 'btn btn-ghost btn-small';
      deleteBtn.textContent = 'Delete';
      deleteBtn.onclick = () => deleteRuleset(ruleset.id, ruleset.name);
      
      actions.appendChild(loadBtn);
      actions.appendChild(deleteBtn);
      
      card.appendChild(name);
      card.appendChild(actions);
      
      savedRulesetsListDiv.appendChild(card);
    });
  } catch (error) {
    console.error('Error loading rulesets:', error);
    savedRulesetsListDiv.innerHTML = '<div class="error-message">Failed to load rulesets</div>';
  }
}

async function deleteRuleset(id, name) {
  if (!confirm(`Delete ruleset "${name}"?`)) return;
  
  try {
    const response = await fetch(`/api/v1/rulesets/${id}`, {
      method: 'DELETE'
    });
    
    if (!response.ok) throw new Error('Failed to delete ruleset');
    
    // Show success
    showStatus('Ruleset deleted successfully', 'success');
    
    // Reload list
    loadSavedRulesets();
  } catch (error) {
    console.error('Error deleting ruleset:', error);
    showStatus('Failed to delete ruleset', 'error');
  }
}

function setupSaveRuleset() {
  const saveRulesetBtn = document.getElementById('saveRulesetBtn');
  const saveRulesetModal = document.getElementById('saveRulesetModal');
  const saveRulesetModalClose = document.getElementById('saveRulesetModalClose');
  const saveRulesetModalCancel = document.getElementById('saveRulesetModalCancel');
  const saveRulesetModalSave = document.getElementById('saveRulesetModalSave');
  const rulesetNameInput = document.getElementById('rulesetNameInput');
  
  if (saveRulesetBtn) {
    saveRulesetBtn.addEventListener('click', () => {
      rulesetNameInput.value = '';
      saveRulesetModal.style.display = 'flex';
    });
  }
  
  if (saveRulesetModalClose) {
    saveRulesetModalClose.addEventListener('click', () => {
      saveRulesetModal.style.display = 'none';
    });
  }
  
  if (saveRulesetModalCancel) {
    saveRulesetModalCancel.addEventListener('click', () => {
      saveRulesetModal.style.display = 'none';
    });
  }
  
  if (saveRulesetModalSave) {
    saveRulesetModalSave.addEventListener('click', async () => {
      const name = rulesetNameInput.value.trim();
      if (!name) {
        alert('Please enter a name for the ruleset');
        return;
      }
      
      // Build rules object
      const rules = {
        validations: typeof getDocumentValidations === 'function' ? getDocumentValidations() : {},
        fields: typeof getFields === 'function' ? getFields().map(f => ({
          name: f.name,
          lookFor: f.lookFor,
          type: f.type,
          strategy: f.strategy || 'first',
          validations: f.validations || [],
          ...(f.column && { column: f.column })
        })) : [],
        calculations: typeof getCalculations === 'function' ? getCalculations() : []
      };
      
      // Remove empty arrays/objects
      if (Object.keys(rules.validations).length === 0) delete rules.validations;
      if (rules.fields.length === 0) delete rules.fields;
      if (rules.calculations.length === 0) delete rules.calculations;
      
      if (Object.keys(rules).length === 0) {
        alert('Please add some rules before saving');
        return;
      }
      
      try {
        const response = await fetch('/api/v1/rulesets/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, rules })
        });
        
        if (!response.ok) throw new Error('Failed to save ruleset');
        
        saveRulesetModal.style.display = 'none';
        showStatus('Ruleset saved successfully', 'success');
        loadSavedRulesets();
      } catch (error) {
        console.error('Error saving ruleset:', error);
        showStatus('Failed to save ruleset', 'error');
      }
    });
  }
}

function showStatus(message, type = 'info') {
  const statusDiv = document.getElementById('rulesetStatus');
  if (!statusDiv) return;
  
  statusDiv.textContent = message;
  statusDiv.className = `status-message status-${type}`;
  statusDiv.style.display = 'block';
  
  setTimeout(() => {
    statusDiv.style.display = 'none';
  }, 3000);
}

// Helper function for escaping HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
