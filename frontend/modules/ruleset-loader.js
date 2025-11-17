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
      const field = {
        name: f.name || '',
        type: f.type || 'text',
        strategy: f.strategy || 'first',
        validations: f.validations || []
      };
      
      // Handle table extraction fields
      if (f.strategy === 'table_extraction') {
        field.extractionType = f.extractionType;
        if (f.page !== undefined) field.page = f.page;
        if (f.tableIndex !== undefined) field.tableIndex = f.tableIndex;
      }
      // Preserve startMarker and endMarker for 'between' strategy
      else if (f.strategy === 'between') {
        field.startMarker = f.startMarker || '';
        field.endMarker = f.endMarker || '';
        if (f.occurrence) field.occurrence = f.occurrence;
      }
      // Regular fields with lookFor
      else {
        field.lookFor = f.lookFor || '';
      }
      
      // Add column if present
      if (f.column) {
        field.column = f.column;
      }
      
      return field;
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
