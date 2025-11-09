// Field Wizard Module
// Handles the field extraction wizard modal

let fields = [];

function initFieldWizard() {
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
  const fieldsList = document.getElementById('fieldsList');
  
  // Get between markers elements
  const betweenMarkersSection = document.getElementById('betweenMarkersSection');
  const startMarkerInput = document.getElementById('startMarkerInput');
  const endMarkerInput = document.getElementById('endMarkerInput');

  // Toggle column section visibility
  if (fieldInTableCheckbox) {
    fieldInTableCheckbox.addEventListener('change', (e) => {
      fieldColumnSection.style.display = e.target.checked ? 'block' : 'none';
      if (!e.target.checked) {
        fieldColumnInput.value = '';
      }
    });
  }

  // Toggle between markers section based on strategy
  if (fieldStrategySelect && betweenMarkersSection) {
    fieldStrategySelect.addEventListener('change', (e) => {
      const isBetween = e.target.value === 'between';
      betweenMarkersSection.style.display = isBetween ? 'block' : 'none';
      fieldStrategySection.querySelector('.wizard-label').textContent = 
        isBetween ? 'Extraction Strategy' : 'If Multiple Matches Found';
      if (!isBetween) {
        startMarkerInput.value = '';
        endMarkerInput.value = '';
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
      validationRulesSection.style.display = 'block';
      textValidations.style.display = type === 'text' ? 'block' : 'none';
      numberValidations.style.display = type === 'number' ? 'block' : 'none';
      dateValidations.style.display = type === 'date' ? 'block' : 'none';
    });
  });

  // Open wizard modal
  if (addFieldWizardBtn) {
    addFieldWizardBtn.addEventListener('click', () => {
      // Reset wizard inputs
      fieldNameInput.value = '';
      fieldLookForInput.value = '';
      fieldInTableCheckbox.checked = false;
      fieldColumnInput.value = '';
      startMarkerInput.value = '';
      endMarkerInput.value = '';
      document.querySelectorAll('input[name="fieldType"]').forEach(radio => {
        radio.checked = radio.value === 'text';
      });
      fieldStrategySelect.value = 'first';
      
      // Reset visibility states
      fieldStrategySection.style.display = 'block';
      fieldColumnSection.style.display = 'none';
      betweenMarkersSection.style.display = 'none';
      validationRulesSection.style.display = 'none';
      
      // Reset validation checkboxes
      document.querySelectorAll('.validation-checkbox input[type="checkbox"]').forEach(cb => cb.checked = false);
      document.querySelectorAll('.inline-number, .inline-text, .inline-date').forEach(input => input.value = '');
      
      // Show modal
      fieldWizardModal.style.display = 'flex';
    });
  }

  // Close modal handlers
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

  // Save field
  if (fieldWizardSave) {
    fieldWizardSave.addEventListener('click', () => {
      const name = fieldNameInput.value.trim();
      const lookFor = fieldLookForInput.value.trim();
      const type = document.querySelector('input[name="fieldType"]:checked')?.value || 'text';
      const strategy = fieldStrategySelect.value;
      const inTable = fieldInTableCheckbox?.checked || false;
      const column = inTable ? fieldColumnInput.value.trim() : null;
      const startMarker = startMarkerInput.value.trim();
      const endMarker = endMarkerInput.value.trim();

      // Validation
      if (!name) {
        alert('Please enter a field name');
        return;
      }
      if (strategy !== 'between' && !lookFor) {
        alert('Please enter text to look for');
        return;
      }
      if (strategy === 'between' && (!startMarker || !endMarker)) {
        alert('Please enter both start and end markers');
        return;
      }
      if (inTable && !column) {
        alert('Please specify which column to extract from');
        return;
      }

      // Check for duplicate field names
      const exists = fields.some(f => f.name === name);
      if (exists) {
        alert('A field with this name already exists');
        return;
      }

      // Collect validations based on type
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
        validations,
        strategy
      };
      
      // Add lookFor or markers based on strategy
      if (strategy === 'between') {
        newField.startMarker = startMarker;
        newField.endMarker = endMarker;
      } else {
        newField.lookFor = lookFor;
      }
      
      // Add column if specified
      if (column) {
        newField.column = column;
      }
      fields.push(newField);

      // Close modal and refresh
      fieldWizardModal.style.display = 'none';
      renderFields();
      if (typeof buildRulesPreview === 'function') buildRulesPreview();
    });
  }
}

function renderFields() {
  const fieldsList = document.getElementById('fieldsList');
  
  if (!fieldsList) return;

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
    if (typeof buildRulesPreview === 'function') buildRulesPreview();
    return;
  }
  
  fieldsList.innerHTML = '';
  
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
    if (f.strategy === 'between') {
      fieldLookFor.textContent = `Between: "${f.startMarker}" and "${f.endMarker}"`;
    } else {
      fieldLookFor.textContent = f.lookFor;
    }
    
    fieldInfo.appendChild(fieldName);
    fieldInfo.appendChild(fieldLookFor);
    
    // Strategy selector
    const strategySelect = document.createElement('select');
    strategySelect.className = 'field-strategy';
    strategySelect.innerHTML = `
      <option value="first" ${f.strategy === 'first' ? 'selected' : ''}>First</option>
      <option value="last" ${f.strategy === 'last' ? 'selected' : ''}>Last</option>
      <option value="all" ${f.strategy === 'all' ? 'selected' : ''}>All</option>
      <option value="between" ${f.strategy === 'between' ? 'selected' : ''}>Between</option>
    `;
    strategySelect.addEventListener('change', (e) => {
      fields[idx].strategy = e.target.value;
      if (typeof buildRulesPreview === 'function') buildRulesPreview();
    });
    
    // Remove button
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'field-remove';
    removeBtn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    `;
    removeBtn.addEventListener('click', () => {
      if (confirm(`Remove field "${f.name}"?`)) {
        fields.splice(idx, 1);
        renderFields();
        if (typeof buildRulesPreview === 'function') buildRulesPreview(); 
      }
    });
    
    fieldCard.appendChild(typeBadge);
    fieldCard.appendChild(fieldInfo);
    fieldCard.appendChild(strategySelect);
    fieldCard.appendChild(removeBtn);
    fieldsList.appendChild(fieldCard);
  });
  if (typeof buildRulesPreview === 'function') buildRulesPreview();
}

function getFields() {
  return fields;
}

function setFields(newFields) {
  fields = newFields || [];
  renderFields();
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { initFieldWizard, renderFields, getFields, setFields };
}
