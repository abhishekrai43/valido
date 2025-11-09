// Ruleset Loader Module
// Handles loading saved rulesets and populating the UI

function loadRuleset(ruleset) {
  const rules = ruleset.rules || {};
  
  // Load document validations
  if (typeof setDocumentValidations === 'function') {
    setDocumentValidations(rules.validations);
  }
  
  // Load fields - preserve all properties
  if (typeof setFields === 'function') {
    const fields = (rules.fields || []).map(f => {
      if (typeof f === 'string') {
        return {name: f, lookFor: '', type: 'text', strategy: 'first', validations: []};
      }
      return {
        name: f.name || '',
        lookFor: f.lookFor || '',
        type: f.type || 'text',
        strategy: f.strategy || 'first',
        validations: f.validations || [],
        ...(f.column && { column: f.column })
      };
    });
    setFields(fields);
  }
  
  // Load calculations if present
  if (rules.calculations && typeof setCalculations === 'function') {
    setCalculations(rules.calculations);
  }
  
  // Refresh preview
  if (typeof buildRulesPreview === 'function') {
    buildRulesPreview();
  }
  
  // Show success message
  const statusDiv = document.getElementById('rulesetStatus');
  if (statusDiv) {
    statusDiv.textContent = `Loaded ruleset: ${ruleset.name}`;
    statusDiv.style.display = 'block';
    statusDiv.className = 'status-message status-success';
    setTimeout(() => {
      statusDiv.style.display = 'none';
    }, 3000);
  }
}

function clearRuleset() {
  // Clear all validations
  if (typeof setDocumentValidations === 'function') {
    setDocumentValidations({});
  }
  
  // Clear fields
  if (typeof setFields === 'function') {
    setFields([]);
  }
  
  // Clear calculations
  if (typeof setCalculations === 'function') {
    setCalculations([]);
  }
  
  // Refresh preview
  if (typeof buildRulesPreview === 'function') {
    buildRulesPreview();
  }
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { loadRuleset, clearRuleset };
}
