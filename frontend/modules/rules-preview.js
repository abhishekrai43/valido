// Rules Preview Module
// Builds and displays the human-readable rules summary

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function buildRulesPreview() {
  const rulesPreview = document.getElementById('rulesPreview');
  if (!rulesPreview) return;

  let rules = { fields: [], validations: {}, calculations: [] };
  
  // Get validations
  if (typeof getDocumentValidations === 'function') {
    rules.validations = getDocumentValidations();
  }
  
  // Convert fields array to object format
  if (typeof getFields === 'function') {
    const fields = getFields();
    rules.fields = fields.map(f => {
      const fieldObj = {
        name: f.name,
        type: f.type,
        strategy: f.strategy || 'first',
        validations: f.validations || []
      };
      
      // Add lookFor or markers based on strategy
      if (f.strategy === 'between') {
        fieldObj.startMarker = f.startMarker;
        fieldObj.endMarker = f.endMarker;
      } else {
        fieldObj.lookFor = f.lookFor;
      }
      
      // Add column if present
      if (f.column) {
        fieldObj.column = f.column;
      }
      
      return fieldObj;
    });
  }
  
  // Add calculations if available
  if (typeof getCalculations === 'function') {
    rules.calculations = getCalculations();
  }
  
  // remove empty objects
  if (Object.keys(rules.validations).length === 0) delete rules.validations;
  if (!rules.fields || rules.fields.length === 0) delete rules.fields;
  if (!rules.calculations || rules.calculations.length === 0) delete rules.calculations;
  
  // Build human-readable summary with HTML formatting
  let summaryHtml = '';
  
  if (Object.keys(rules).length === 0) {
    rulesPreview.innerHTML = 'No rules selected yet. Choose some checks above to get started.';
    // Update hidden textarea
    const rulesTextarea = document.getElementById('rules');
    if (rulesTextarea) rulesTextarea.value = '';
    return;
  }
  
  summaryHtml += '<div class="preview-container">';
  
  // Document validations section
  if (rules.validations && Object.keys(rules.validations).length > 0) {
    summaryHtml += '<div class="preview-section">';
    summaryHtml += '<div class="preview-label">Document Requirements:</div>';
    summaryHtml += '<ul class="preview-list">';
    
    if (rules.validations.signed) {
      summaryHtml += '<li class="preview-item"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" style="margin-right: 8px;"><path d="M16 6L8 14L4 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>Document must be digitally signed</li>';
    }
    
    if (rules.validations.must_contain) {
      const text = escapeHtml(rules.validations.must_contain.text);
      const caseSensitive = rules.validations.must_contain.case_sensitive ? ' (case-sensitive)' : '';
      summaryHtml += `<li class="preview-item"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" style="margin-right: 8px;"><path d="M16 6L8 14L4 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>Must contain text: "${text}"${caseSensitive}</li>`;
    }
    
    if (rules.validations.must_not_contain) {
      const text = escapeHtml(rules.validations.must_not_contain.text);
      const caseSensitive = rules.validations.must_not_contain.case_sensitive ? ' (case-sensitive)' : '';
      summaryHtml += `<li class="preview-item"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" style="margin-right: 8px;"><path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>Must NOT contain text: "${text}"${caseSensitive}</li>`;
    }
    
    if (rules.validations.page_count) {
      const op = rules.validations.page_count.operator;
      const val = rules.validations.page_count.value;
      let opText = op === '>=' ? 'at least' : op === '<=' ? 'at most' : op === '=' ? 'exactly' : op;
      summaryHtml += `<li class="preview-item"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" style="margin-right: 8px;"><path d="M6 4h8M6 8h8M6 12h8M6 16h4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>Page count must be ${opText} ${val}</li>`;
    }
    
    summaryHtml += '</ul>';
    summaryHtml += '</div>';
  }
  
  // Fields section
  if (rules.fields && rules.fields.length > 0) {
    summaryHtml += '<div class="preview-section">';
    summaryHtml += '<div class="preview-label">Information to Extract:</div>';
    summaryHtml += '<div class="preview-field-list">';
    rules.fields.forEach(field => {
      const strategyLabel = field.strategy === 'first' ? 'first' : 
                           field.strategy === 'last' ? 'last' :
                           field.strategy === 'between' ? 'between markers' : 'all';
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
      
      // Build lookup/marker description
      let lookupDesc = '';
      if (field.strategy === 'between') {
        lookupDesc = `Between: "${escapeHtml(field.startMarker)}" and "${escapeHtml(field.endMarker)}"`;
      } else {
        lookupDesc = `Look for: "${escapeHtml(field.lookFor)}"`;
      }
      
      summaryHtml += `<div class="preview-field-item">
        <strong>${escapeHtml(field.name)}</strong> 
        <span class="preview-field-meta">(${typeLabel}, ${strategyLabel})</span>${validationsDesc}
        <div class="preview-field-lookfor">${lookupDesc}</div>
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
  
  rulesPreview.innerHTML = summaryHtml;
  
  // Update hidden textarea with JSON
  const rulesTextarea = document.getElementById('rules');
  if (rulesTextarea) {
    rulesTextarea.value = JSON.stringify(rules, null, 2);
  }
}

// Export function
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { buildRulesPreview };
}
