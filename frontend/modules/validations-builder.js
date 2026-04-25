// Validations Builder Module
// Handles document-level validation checkboxes and inputs

function initValidationsBuilder() {
  // No event listeners needed - just getters/setters
  // The checkboxes are already in the HTML and work directly
}

function getDocumentValidations() {
  const validations = {};
  
  const chkSigned = document.getElementById('chkSigned');
  if (chkSigned && chkSigned.checked) {
    validations.signed = true;
  }
  
  // Must Contain rule
  const chkMustContain = document.getElementById('chkMustContain');
  const mustContainText = document.getElementById('mustContainText');
  const mustContainCaseSensitive = document.getElementById('mustContainCaseSensitive');
  if (chkMustContain && chkMustContain.checked && mustContainText && mustContainText.value.trim()) {
    validations.must_contain = {
      text: mustContainText.value.trim(),
      case_sensitive: !!(mustContainCaseSensitive && mustContainCaseSensitive.checked)
    };
  }
  
  // Must NOT Contain rule
  const chkMustNotContain = document.getElementById('chkMustNotContain');
  const mustNotContainText = document.getElementById('mustNotContainText');
  const mustNotContainCaseSensitive = document.getElementById('mustNotContainCaseSensitive');
  if (chkMustNotContain && chkMustNotContain.checked && mustNotContainText && mustNotContainText.value.trim()) {
    validations.must_not_contain = {
      text: mustNotContainText.value.trim(),
      case_sensitive: !!(mustNotContainCaseSensitive && mustNotContainCaseSensitive.checked)
    };
  }
  
  // Page count validation
  const chkPageCount = document.getElementById('chkPageCount');
  const pageCountOperator = document.getElementById('pageCountOperator');
  const pageCountValue = document.getElementById('pageCountValue');
  if (chkPageCount && chkPageCount.checked && pageCountValue && pageCountValue.value) {
    validations.page_count = {
      operator: pageCountOperator ? pageCountOperator.value : '>=',
      value: parseInt(pageCountValue.value) || 1
    };
  }
  
  return validations;
}

function setDocumentValidations(validations) {
  validations = validations || {};

  const normalizeTextValidation = (value) => {
    if (Array.isArray(value)) {
      return value[0] || null;
    }
    return value || null;
  };
  
  const chkSigned = document.getElementById('chkSigned');
  if (chkSigned) chkSigned.checked = !!validations.signed;
  
  const chkMustContain = document.getElementById('chkMustContain');
  const mustContainText = document.getElementById('mustContainText');
  const mustContainCaseSensitive = document.getElementById('mustContainCaseSensitive');
  const mustContain = normalizeTextValidation(validations.must_contain);
  if (chkMustContain) chkMustContain.checked = !!mustContain;
  if (mustContainText) mustContainText.value = mustContain ? (mustContain.text || '') : '';
  if (mustContainCaseSensitive) mustContainCaseSensitive.checked = !!(mustContain && mustContain.case_sensitive);
  
  const chkMustNotContain = document.getElementById('chkMustNotContain');
  const mustNotContainText = document.getElementById('mustNotContainText');
  const mustNotContainCaseSensitive = document.getElementById('mustNotContainCaseSensitive');
  const mustNotContain = normalizeTextValidation(validations.must_not_contain);
  if (chkMustNotContain) chkMustNotContain.checked = !!mustNotContain;
  if (mustNotContainText) mustNotContainText.value = mustNotContain ? (mustNotContain.text || '') : '';
  if (mustNotContainCaseSensitive) mustNotContainCaseSensitive.checked = !!(mustNotContain && mustNotContain.case_sensitive);
  
  const chkPageCount = document.getElementById('chkPageCount');
  const pageCountOperator = document.getElementById('pageCountOperator');
  const pageCountValue = document.getElementById('pageCountValue');
  if (chkPageCount) chkPageCount.checked = !!validations.page_count;
  if (pageCountOperator) pageCountOperator.value = validations.page_count ? (validations.page_count.operator || '>=') : '>=';
  if (pageCountValue) pageCountValue.value = validations.page_count ? (validations.page_count.value || 1) : '';
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { initValidationsBuilder, getDocumentValidations, setDocumentValidations };
}
