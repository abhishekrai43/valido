// Main application logic for Valido - user-friendly step-by-step validation
(() => {
  function init() {
    // Elements
    const form = document.getElementById('uploadForm');
    const navUpload = document.getElementById('navUpload');
    const navHistory = document.getElementById('navHistory');
    const uploadSection = document.getElementById('uploadSection');
    const historySection = document.getElementById('historySection');
    
    const filesInput = document.getElementById('files');
    const uploadArea = document.getElementById('uploadArea');
    const filesList = document.getElementById('filesList');
    const continueToRules = document.getElementById('continueToRules');
    const continueToValidate = document.getElementById('continueToValidate');
    const backToFiles = document.getElementById('backToFiles');
    const backToRules = document.getElementById('backToRules');
    const submitBtn = document.getElementById('submitBtn');
    const startNewBtn = document.getElementById('startNewBtn');
    
    const steps = document.querySelectorAll('.step');
    const stepCards = document.querySelectorAll('.step-card');
    
    const summaryFiles = document.getElementById('summaryFiles');
    const summaryRules = document.getElementById('summaryRules');
    const rulesPreview = document.getElementById('rulesPreview');
    
    const processingStatus = document.getElementById('processingStatus');
    const successStatus = document.getElementById('successStatus');
    const errorStatus = document.getElementById('errorStatus');
    const statusTitle = document.getElementById('statusTitle');
    const statusMessage = document.getElementById('statusMessage');
    const errorMessage = document.getElementById('errorMessage');
    const progressFill = document.getElementById('progressFill');
    const downloadLink = document.getElementById('downloadLink');
    
    let currentStep = 1;
    let selectedFiles = [];
    
    // Navigation
    function navigateToStep(stepNum) {
      currentStep = stepNum;
      
      // Update step indicator
      steps.forEach(step => {
        const num = parseInt(step.dataset.step);
        if (num < currentStep) {
          step.classList.remove('active');
          step.classList.add('completed');
        } else if (num === currentStep) {
          step.classList.add('active');
          step.classList.remove('completed');
        } else {
          step.classList.remove('active', 'completed');
        }
      });
      
      // Show appropriate card
      stepCards.forEach(card => {
        const cardStep = parseInt(card.dataset.stepContent);
        card.style.display = cardStep === currentStep ? 'block' : 'none';
      });
      
      // Scroll to top
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    // File Upload Handling
    function handleFiles(files) {
      selectedFiles = Array.from(files);
      renderFilesList();
      continueToRules.disabled = selectedFiles.length === 0;
    }
    
    function renderFilesList() {
      if (selectedFiles.length === 0) {
        filesList.innerHTML = '';
        return;
      }
      
      let html = '<div class="files-preview">';
      selectedFiles.forEach((file, idx) => {
        const size = (file.size / 1024).toFixed(1);
        const icon = file.name.endsWith('.zip') ? '📦' : '📄';
        html += `
          <div class="file-item">
            <div class="file-icon">${icon}</div>
            <div class="file-info">
              <div class="file-name">${escapeHtml(file.name)}</div>
              <div class="file-size">${size} KB</div>
            </div>
            <button type="button" class="file-remove" data-index="${idx}" aria-label="Remove file">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M5 5L15 15M5 15L15 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
        `;
      });
      html += '</div>';
      filesList.innerHTML = html;
      
      // Wire remove buttons
      filesList.querySelectorAll('.file-remove').forEach(btn => {
        btn.addEventListener('click', () => {
          const idx = parseInt(btn.dataset.index);
          selectedFiles.splice(idx, 1);
          
          // Update input files (create new FileList)
          const dt = new DataTransfer();
          selectedFiles.forEach(f => dt.items.add(f));
          filesInput.files = dt.files;
          
          renderFilesList();
          continueToRules.disabled = selectedFiles.length === 0;
        });
      });
    }
    
    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
    
    // Upload area interactions
    if (uploadArea && filesInput) {
      uploadArea.addEventListener('click', () => filesInput.click());
      
      uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
      });
      
      uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
      });
      
      uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
          filesInput.files = e.dataTransfer.files;
          handleFiles(e.dataTransfer.files);
        }
      });
      
      filesInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
      });
    }
    
    // Step navigation buttons
    continueToRules && continueToRules.addEventListener('click', () => {
      if (selectedFiles.length > 0) {
        navigateToStep(2);
      }
    });
    
    continueToValidate && continueToValidate.addEventListener('click', () => {
      updateSummary();
      navigateToStep(3);
    });
    
    backToFiles && backToFiles.addEventListener('click', () => {
      navigateToStep(1);
    });
    
    backToRules && backToRules.addEventListener('click', () => {
      navigateToStep(2);
    });
    
    function updateSummary() {
      // Update file summary
      const fileCount = selectedFiles.length;
      summaryFiles.textContent = `${fileCount} ${fileCount === 1 ? 'document' : 'documents'}`;
      
      // Update rules summary
      const rulesText = rulesPreview ? rulesPreview.textContent : 'No rules';
      summaryRules.textContent = rulesText || 'No rules selected';
    }
    
    // Form submission with user-friendly status
    form && form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      
      const files = filesInput.files;
      const rulesEl = document.getElementById('rules');
      
      let rules = '';
      try {
        rules = (rulesEl && rulesEl.dataset && rulesEl.dataset.json) 
          ? rulesEl.dataset.json 
          : (rulesEl?.value || '').trim();
      } catch(e) {
        rules = (rulesEl?.value || '').trim();
      }
      
      if (!files || files.length === 0) {
        showError('Please select at least one file to validate.');
        navigateToStep(1);
        return;
      }
      
      // Hide submit button, show processing status
      submitBtn.style.display = 'none';
      processingStatus.style.display = 'flex';
      successStatus.style.display = 'none';
      errorStatus.style.display = 'none';
      
      const fd = new FormData();
      for (let i = 0; i < files.length; i++) {
        fd.append('files', files[i]);
      }
      if (rules) fd.append('rules', rules);
      
      try {
        statusTitle.textContent = 'Uploading your documents...';
        statusMessage.textContent = 'Please wait while we process your files';
        progressFill.style.width = '10%';
        
        const res = await fetch('/api/v1/submit', { method: 'POST', body: fd });
        
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`Upload failed: ${text}`);
        }
        
        const j = await res.json();
        const taskId = j.task_id;
        
        // Record to history
        recordHistory(taskId);
        
        // Poll for completion
        statusTitle.textContent = 'Validating your documents...';
        statusMessage.textContent = 'This may take a few moments';
        progressFill.style.width = '30%';
        
        const result = await pollTask(taskId);
        
        if (result.state === 'SUCCESS') {
          showSuccess(taskId);
        } else if (result.state === 'FAILURE') {
          showError(result.info?.error || 'Validation failed. Please try again.');
        } else {
          showError('Validation timed out. Please try again or contact support.');
        }
        
      } catch (err) {
        showError(err.message || 'An unexpected error occurred. Please try again.');
      }
    });
    
    async function pollTask(taskId) {
      const maxAttempts = 200;
      let attempts = 0;
      const interval = 1500;
      
      return new Promise((resolve) => {
        const timer = setInterval(async () => {
          attempts++;
          
          try {
            const res = await fetch(`/api/v1/tasks/${taskId}`);
            if (!res.ok) {
              clearInterval(timer);
              resolve({ state: 'FAILURE', info: { error: 'Failed to check status' } });
              return;
            }
            
            const json = await res.json();
            
            // Update progress
            if (json.info && json.info.processed && json.info.total) {
              const percent = Math.min(95, 30 + (json.info.processed / json.info.total * 65));
              progressFill.style.width = `${percent}%`;
              statusMessage.textContent = `Processing document ${json.info.processed} of ${json.info.total}`;
            }
            
            if (json.state === 'SUCCESS' || json.state === 'FAILURE' || json.state === 'REVOKED') {
              clearInterval(timer);
              progressFill.style.width = '100%';
              resolve(json);
            }
            
            if (attempts >= maxAttempts) {
              clearInterval(timer);
              resolve({ state: 'TIMEOUT' });
            }
          } catch (err) {
            clearInterval(timer);
            resolve({ state: 'FAILURE', info: { error: err.message } });
          }
        }, interval);
      });
    }
    
    function showSuccess(taskId) {
      processingStatus.style.display = 'none';
      successStatus.style.display = 'flex';
      startNewBtn.style.display = 'inline-flex';
      
      // Check for download link
      const csvUrl = `/api/v1/tasks/${taskId}/result.csv`;
      fetch(csvUrl, { method: 'HEAD' })
        .then(res => {
          if (res.ok) {
            downloadLink.innerHTML = `
              <a href="${csvUrl}" download class="btn btn-primary btn-large download-btn">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 2V14M10 14L6 10M10 14L14 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2 14V16C2 17.1046 2.89543 18 4 18H16C17.1046 18 18 17.1046 18 16V14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                Download Results
              </a>
            `;
          }
        })
        .catch(() => {
          downloadLink.innerHTML = '<p class="helper">Results are ready but download link is not available.</p>';
        });
    }
    
    function showError(message) {
      processingStatus.style.display = 'none';
      errorStatus.style.display = 'flex';
      errorMessage.textContent = message;
      submitBtn.style.display = 'inline-flex';
    }
    
    function recordHistory(taskId) {
      try {
        const historyEntry = {
          timestamp: Date.now(),
          files: selectedFiles.map(f => f.name),
          mode: document.querySelector('.tabs button.active')?.dataset.tab || 'simple',
          prompt: document.getElementById('aiPrompt')?.value || null,
          fields: (window.getHistoryFields && window.getHistoryFields()) || null,
          validations: {
            signed: !!document.getElementById('chk_validate_signed')?.checked,
            dated: !!document.getElementById('chk_validate_dated')?.checked,
            signed_and_dated: !!document.getElementById('chk_validate_signed_and_dated')?.checked,
          },
          rulesSummary: document.getElementById('rulesPreview')?.textContent || '',
          task_id: taskId
        };
        window.pushHistory && window.pushHistory(historyEntry);
      } catch(e) {
        console.warn('Failed to record history:', e);
      }
    }
    
    // Start new validation
    startNewBtn && startNewBtn.addEventListener('click', () => {
      // Reset form
      selectedFiles = [];
      filesInput.value = '';
      renderFilesList();
      
      // Reset status displays
      processingStatus.style.display = 'none';
      successStatus.style.display = 'none';
      errorStatus.style.display = 'none';
      submitBtn.style.display = 'inline-flex';
      startNewBtn.style.display = 'none';
      downloadLink.innerHTML = '';
      
      // Reset rules
      if (window.resetBuilder) window.resetBuilder();
      
      // Go back to step 1
      navigateToStep(1);
    });
    
    // Navigation between Upload and History
    if (navUpload && navHistory && uploadSection && historySection) {
      navUpload.addEventListener('click', () => {
        uploadSection.style.display = 'block';
        historySection.style.display = 'none';
        navUpload.classList.add('active');
        navHistory.classList.remove('active');
      });
      
      navHistory.addEventListener('click', () => {
        uploadSection.style.display = 'none';
        historySection.style.display = 'block';
        navHistory.classList.remove('active');
        navHistory.classList.add('active');
        navUpload.classList.remove('active');
        window.renderHistory && window.renderHistory();
      });
    }
    
    // Initialize on step 1
    navigateToStep(1);
  }
  
  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
