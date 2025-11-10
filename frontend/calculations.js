// Calculations Module
// Handles calculation builder UI and logic

let calculations = [];

function initCalculations() {
  const addCalculationBtn = document.getElementById('addCalculationBtn');
  const calculationModal = document.getElementById('calculationModal');
  const calculationModalClose = document.getElementById('calculationModalClose');
  const calculationModalCancel = document.getElementById('calculationModalCancel');
  const calculationModalSave = document.getElementById('calculationModalSave');
  const calcNameInput = document.getElementById('calcNameInput');
  const calcFormulaInput = document.getElementById('calcFormulaInput');
  const calculationsList = document.getElementById('calculationsList');
  const availableFieldsList = document.getElementById('availableFieldsList');

  // Open modal
  if (addCalculationBtn) {
    addCalculationBtn.addEventListener('click', () => {
      // Reset inputs
      calcNameInput.value = '';
      calcFormulaInput.value = '';
      
      // Populate available fields
      updateAvailableFields();
      
      // Show modal
      calculationModal.style.display = 'flex';
    });
  }

  // Close modal handlers
  if (calculationModalClose) {
    calculationModalClose.addEventListener('click', () => {
      calculationModal.style.display = 'none';
    });
  }

  if (calculationModalCancel) {
    calculationModalCancel.addEventListener('click', () => {
      calculationModal.style.display = 'none';
    });
  }

  // Save calculation
  if (calculationModalSave) {
    calculationModalSave.addEventListener('click', () => {
      const name = calcNameInput.value.trim();
      const formula = calcFormulaInput.value.trim();

      // Validation
      if (!name) {
        alert('Please enter a calculation name');
        return;
      }
      if (!formula) {
        alert('Please enter a formula');
        return;
      }

      // Check for duplicate names
      const exists = calculations.some(c => c.name === name);
      if (exists) {
        alert('A calculation with this name already exists');
        return;
      }

      // Add calculation
      calculations.push({ name, formula });

      // Close modal and refresh
      calculationModal.style.display = 'none';
      renderCalculations();
      if (typeof buildRulesPreview === 'function') {
        buildRulesPreview();
      } else if (typeof window.buildRulesPreview === 'function') {
        window.buildRulesPreview();
      }
    });
  }
}

function updateAvailableFields() {
  const availableFieldsList = document.getElementById('availableFieldsList');
  const calcFormulaInput = document.getElementById('calcFormulaInput');
  
  if (!availableFieldsList || !calcFormulaInput) return;

  // Get fields from the global fields array (assumed to be available from rules-builder.js)
  if (typeof fields === 'undefined' || !fields || fields.length === 0) {
    availableFieldsList.innerHTML = '<p style="color: #9ca3af; font-size: 14px; margin: 0;">No fields defined yet. Add extraction fields first.</p>';
    return;
  }

  availableFieldsList.innerHTML = '';
  
  fields.forEach(field => {
    const chip = document.createElement('div');
    chip.className = 'field-chip';
    chip.innerHTML = `
      <svg viewBox="0 0 20 20" fill="currentColor">
        <path d="M10 4V16M4 10H16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
      ${field.name}
    `;
    
    chip.addEventListener('click', () => {
      // Insert field name at cursor position
      const start = calcFormulaInput.selectionStart;
      const end = calcFormulaInput.selectionEnd;
      const text = calcFormulaInput.value;
      const before = text.substring(0, start);
      const after = text.substring(end);
      
      calcFormulaInput.value = before + field.name + after;
      calcFormulaInput.focus();
      
      // Set cursor after inserted text
      const newPos = start + field.name.length;
      calcFormulaInput.setSelectionRange(newPos, newPos);
    });
    
    availableFieldsList.appendChild(chip);
  });
}

function renderCalculations() {
  const calculationsList = document.getElementById('calculationsList');
  
  if (!calculationsList) return;

  if (calculations.length === 0) {
    calculationsList.innerHTML = `
      <div class="fields-empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" style="opacity: 0.3; margin-bottom: 12px;">
          <path d="M4 7h16M4 12h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-opacity="0.2"/>
        </svg>
        <p style="color: #9ca3af; font-size: 14px; margin: 0;">No calculations added yet</p>
        <p style="color: #d1d5db; font-size: 13px; margin: 4px 0 0 0;">Calculations are performed after field extraction</p>
      </div>
    `;
    return;
  }

  calculationsList.innerHTML = '';
  
  calculations.forEach((calc, idx) => {
    const calcCard = document.createElement('div');
    calcCard.className = 'field-card';
    calcCard.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
    calcCard.style.color = 'white';
    
    calcCard.innerHTML = `
      <span class="field-type-badge" style="background: rgba(255, 255, 255, 0.3);">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <text x="6" y="18" font-size="18" font-weight="bold">=</text>
        </svg>
      </span>
      <div class="field-info">
        <div class="field-name">${calc.name}</div>
        <div class="field-lookfor" style="font-family: 'Courier New', monospace; font-size: 12px; opacity: 0.9;">${calc.formula}</div>
      </div>
      <button type="button" class="field-remove" onclick="removeCalculation(${idx})" style="color: white;">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </button>
    `;
    
    calculationsList.appendChild(calcCard);
  });
}

function removeCalculation(index) {
  if (confirm('Remove this calculation?')) {
    calculations.splice(index, 1);
    renderCalculations();
    if (typeof buildRulesPreview === 'function') {
      buildRulesPreview();
    } else if (typeof window.buildRulesPreview === 'function') {
      window.buildRulesPreview();
    }
  }
}

function getCalculations() {
  return calculations;
}

function setCalculations(calcs) {
  calculations = calcs || [];
  renderCalculations();
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initCalculations,
    renderCalculations,
    removeCalculation,
    getCalculations,
    setCalculations
  };
}

// Export to window for browser usage
window.getCalculations = getCalculations;
window.setCalculations = setCalculations;
