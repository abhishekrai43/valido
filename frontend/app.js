// Main application logic for Valido - user-friendly step-by-step validation
(() => {
  function init() {
    // Set network URL dynamically
    const networkUrlEl = document.getElementById('networkUrl');
    if (networkUrlEl) {
      // Fetch network info from backend
      fetch('/api/v1/network-info')
        .then(response => response.json())
        .then(data => {
          networkUrlEl.textContent = data.network;
        })
        .catch(error => {
          console.warn('Failed to fetch network info:', error);
          // Fallback to localhost
          const host = window.location.hostname;
          const port = window.location.port || '80';
          networkUrlEl.textContent = `http://${host}:${port}`;
        });
    }

    // Fetch and display usage information
    function updateUsageIndicator() {
      const usageIndicator = document.getElementById('usageIndicator');
      const usageText = document.getElementById('usageText');
      
      if (!usageIndicator || !usageText) return;
      
      fetch('/api/v1/usage')
        .then(response => response.json())
        .then(data => {
          const { count, limit, remaining, exceeded, warning } = data;
          
          // Update text
          usageText.textContent = `${count}/${limit} PDFs`;
          
          // Update styling based on status
          usageIndicator.classList.remove('warning', 'exceeded');
          if (exceeded) {
            usageIndicator.classList.add('exceeded');
            usageIndicator.title = `Free tier limit reached. You've processed ${count} PDFs this month.`;
          } else if (warning) {
            usageIndicator.classList.add('warning');
            usageIndicator.title = `${remaining} PDFs remaining this month`;
          } else {
            usageIndicator.title = `${remaining} PDFs remaining out of ${limit} free PDFs this month`;
          }
        })
        .catch(error => {
          console.warn('Failed to fetch usage info:', error);
          usageText.textContent = '0/300 PDFs';
          usageIndicator.title = 'Usage tracking unavailable';
        });
    }
    
    // Update usage on page load
    updateUsageIndicator();
    
    // Refresh usage every 30 seconds
    setInterval(updateUsageIndicator, 30000);
    
    // Share button functionality
    const shareBtn = document.getElementById('shareBtn');
    if (shareBtn) {
      shareBtn.addEventListener('click', () => {
        const modal = document.createElement('div');
        modal.className = 'share-modal';
        modal.innerHTML = `
          <div class="share-modal-overlay"></div>
          <div class="share-modal-content">
            <div class="share-modal-header">
              <h3>Share Valido</h3>
              <button class="share-modal-close" onclick="this.closest('.share-modal').remove()">×</button>
            </div>
            <div class="share-modal-body">
              <p style="margin-bottom: 20px; color: #666; line-height: 1.6;">
                Love Valido? Share it with your colleagues and help them streamline their document validation workflow!
              </p>
              
              <div class="share-options">
                <button class="share-option" onclick="window.open('mailto:?subject=Check out Valido - PDF Validation Tool&body=I found this amazing PDF validation tool that runs locally on your computer. No cloud upload, fully private!%0A%0ACheck it out: ${window.location.origin}', '_blank')">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
                    <path d="M3 7L12 13L21 7" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>Share via Email</span>
                </button>
                
                <button class="share-option" onclick="navigator.clipboard.writeText('${window.location.origin}').then(() => { alert('Link copied to clipboard!'); this.closest('.share-modal').remove(); })">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M8 5H6C4.89543 5 4 5.89543 4 7V19C4 20.1046 4.89543 21 6 21H16C17.1046 21 18 20.1046 18 19V18" stroke="currentColor" stroke-width="2"/>
                    <rect x="8" y="3" width="12" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>Copy Link</span>
                </button>
                
                <button class="share-option" onclick="window.open('https://twitter.com/intent/tweet?text=Check out Valido - a privacy-first PDF validation tool that runs locally on your computer!&url=${encodeURIComponent(window.location.origin)}', '_blank', 'width=550,height=420')">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M23 3a10.9 10.9 0 01-3.14 1.53 4.48 4.48 0 00-7.86 3v1A10.66 10.66 0 013 4s-4 9 5 13a11.64 11.64 0 01-7 2c9 5 20 0 20-11.5a4.5 4.5 0 00-.08-.83A7.72 7.72 0 0023 3z" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>Share on Twitter</span>
                </button>
                
                <button class="share-option" onclick="window.open('https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(window.location.origin)}', '_blank', 'width=550,height=420')">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z" stroke="currentColor" stroke-width="2"/>
                    <circle cx="4" cy="4" r="2" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>Share on LinkedIn</span>
                </button>
              </div>
            </div>
          </div>
        `;
        document.body.appendChild(modal);
        
        // Close on overlay click
        modal.querySelector('.share-modal-overlay').addEventListener('click', () => {
          modal.remove();
        });
      });
    }

    // Elements
    const form = document.getElementById('uploadForm');
  const navUpload = document.getElementById('navUpload');
  const uploadSection = document.getElementById('uploadSection');
    
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
  const submitBtnText = document.getElementById('submitBtnText');
  const successTitleEl = document.getElementById('successTitle');
  const successMessageEl = document.getElementById('successMessage');
  const resultsOutput = document.getElementById('resultsOutput');
    
    let currentStep = 1;
    let selectedFiles = [];
    
    // Navigation
    function navigateToStep(stepNum, forceReset = false) {
      // Prevent going backwards - one-way flow only (unless forcing reset)
      if (stepNum < currentStep && !forceReset) {
        return; // Ignore backward navigation
      }
      
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
      
      // Refresh rules preview when entering step 2
      if (stepNum === 2 && typeof window.buildRulesPreview === 'function') {
        window.buildRulesPreview();
      }
      
      // Reset validation status when entering step 3
      if (stepNum === 3) {
        // Hide all status displays
        if (processingStatus) processingStatus.style.display = 'none';
        if (successStatus) successStatus.style.display = 'none';
        if (errorStatus) errorStatus.style.display = 'none';
        // Show submit button and ensure it's enabled
        if (submitBtn) {
          submitBtn.style.display = 'block';
          submitBtn.disabled = false;  // CRITICAL: Enable submit button
        }
        // Clear any previous results
        if (resultsOutput) resultsOutput.innerHTML = '';
        // Reset submission flag
        isSubmitting = false;
      }
      
      // Scroll to top
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    // File Upload Handling
    function handleFiles(files) {
      selectedFiles = Array.from(files);
      renderFilesList();
      const continueBtn = document.getElementById('continueToRules');
      if (continueBtn) {
        continueBtn.disabled = selectedFiles.length === 0;
        // Add visual feedback
        if (selectedFiles.length > 0) {
          continueBtn.classList.add('btn-enabled');
        } else {
          continueBtn.classList.remove('btn-enabled');
        }
      }
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
          const continueBtn = document.getElementById('continueToRules');
          if (continueBtn) {
            continueBtn.disabled = selectedFiles.length === 0;
            if (selectedFiles.length > 0) {
              continueBtn.classList.add('btn-enabled');
            } else {
              continueBtn.classList.remove('btn-enabled');
            }
          }
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
      uploadArea.addEventListener('click', (e) => {
        // Only trigger file input if we didn't click the input itself
        if (e.target !== filesInput) {
          filesInput.click();
        }
      });
      
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
      // Force rules preview update to ensure latest rules are in dataset
      if (window.buildRulesPreview) {
        window.buildRulesPreview();
      }
      updateSummary();
      navigateToStep(3);
    });
    
    backToFiles && backToFiles.addEventListener('click', () => {
      navigateToStep(1);
    });
    
    backToRules && backToRules.addEventListener('click', () => {
      navigateToStep(2);
    });
    
    // Listen for rules updates
    document.addEventListener('rulesUpdated', () => {
      console.log('Rules updated event received, calling updateSummary');
      updateSummary();
    });
    
    function updateSummary() {
      // Update file summary
      const fileCount = selectedFiles.length;
      summaryFiles.textContent = `${fileCount} ${fileCount === 1 ? 'document' : 'documents'}`;
      
      // Update rules summary - get actual rules from the rules textarea dataset
      let rulesText = 'No rules selected yet. Choose some checks above to get started.';
      try {
        const rulesEl = document.getElementById('rules');
        console.log('updateSummary - rulesEl:', rulesEl);
        console.log('updateSummary - rulesEl.dataset.json:', rulesEl?.dataset?.json);
        
        if (rulesEl && rulesEl.dataset && rulesEl.dataset.json) {
          const rules = JSON.parse(rulesEl.dataset.json);
          console.log('updateSummary - parsed rules:', rules);
          const parts = [];
          
          // Check validations
          if (rules.validations) {
            if (rules.validations.signed) parts.push('Check for Signature');
            if (rules.validations.dated) parts.push('Check for Date');
            if (rules.validations.signed_and_dated) parts.push('Check for Signature & Date');
            if (rules.validations.must_contain) parts.push(`Must contain "${rules.validations.must_contain.text}"`);
            if (rules.validations.must_not_contain) parts.push(`Must NOT contain "${rules.validations.must_not_contain.text}"`);
            if (rules.validations.page_count) parts.push(`Page count ${rules.validations.page_count.operator} ${rules.validations.page_count.value}`);
          }
          
          // Check fields
          if (rules.fields && rules.fields.length > 0) {
            parts.push(`Extract ${rules.fields.length} field${rules.fields.length > 1 ? 's' : ''}`);
          }
          
          if (parts.length > 0) {
            rulesText = parts.join(', ');
          }
        }
      } catch (e) {
        console.error('Error reading rules for summary:', e);
      }
      
      summaryRules.textContent = rulesText;
      // Update submit button label based on whether user requested extraction fields
      updateSubmitButtonLabel();
    }

    // Update the submit button label depending on whether extraction fields were selected
    function updateSubmitButtonLabel() {
      try {
        const rulesEl = document.getElementById('rules');
        let hasFields = false;
        if (rulesEl && rulesEl.dataset && rulesEl.dataset.json) {
          try {
            const parsed = JSON.parse(rulesEl.dataset.json);
            if (parsed && Array.isArray(parsed.fields) && parsed.fields.length > 0) hasFields = true;
          } catch (e) {
            // ignore parse
          }
        }
        if (submitBtnText) submitBtnText.textContent = hasFields ? 'Start Extraction' : 'Start Validation';
      } catch (e) {
        // non-fatal
      }
    }

    // Listen for rules updates from the rules builder
    document.addEventListener('rulesUpdated', () => updateSubmitButtonLabel());
  // Run once at startup to ensure correct label
  updateSubmitButtonLabel();
    
    // Form submission with user-friendly status
    let isSubmitting = false;  // Prevent duplicate submissions
    
    form && form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      
      // Prevent duplicate submissions
      if (isSubmitting) {
        console.log('Submission already in progress, ignoring duplicate');
        return;
      }
      
      isSubmitting = true;
      
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
      
      // Debug: log what rules are being sent
      console.log('Submitting with rules:', rules);
      
      if (!files || files.length === 0) {
        isSubmitting = false;  // Reset flag
        showError('Please select at least one file to validate.');
        navigateToStep(1);
        return;
      }

      // Limit to 500 files per batch
      if (files.length > 500) {
        isSubmitting = false;  // Reset flag
        showError('Maximum 500 files allowed per batch. Please split your files into smaller batches.');
        navigateToStep(1);
        return;
      }
      
      // Hide submit button, show processing status
      submitBtn.style.display = 'none';
      submitBtn.disabled = true;  // Disable button as extra safety
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
        // If the user uploaded only non-ZIP files we can show an immediate "Processing 1 of N" count.
        // If there are ZIPs, show a clear expanding message and rely on the immediate poll to update the true total.
        try {
          const fileList = Array.from(files || []);
          const hasZip = fileList.some(f => f.name && f.name.toLowerCase().endsWith('.zip'));
          if (!hasZip && fileList.length > 0) {
            const totalCount = fileList.length;
            statusTitle.textContent = `Processing 1 of ${totalCount} documents...`;
            statusMessage.textContent = `Current: ${escapeHtml(fileList[0].name)}`;
            progressFill.style.width = '35%';
          } else {
            statusTitle.textContent = 'Processing documents...';
            statusMessage.textContent = 'Expanding ZIP(s) and preparing files for validation';
            progressFill.style.width = '35%';
          }
        } catch (e) {
          // Fallback to generic message on any error
          statusTitle.textContent = 'Processing documents...';
          statusMessage.textContent = 'Preparing files for validation';
          progressFill.style.width = '35%';
        }

        const result = await pollTask(taskId);
        
        // Debug: log the task result to see what we received
        console.log('Task completed with result:', result);

        if (result.state === 'SUCCESS') {
          showSuccess(taskId, result);
        } else if (result.state === 'LIMIT_EXCEEDED') {
          // Handle limit exceeded before any processing
          const info = result.info || {};
          const usageInfo = info.limit_info || info.usage_info || {};
          showError(`Free tier limit reached (${usageInfo.count || 300}/${usageInfo.limit || 300} PDFs). Cannot process any more files. Upgrade to continue.`);
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
        const poll = async () => {
          attempts++;
          
          try {
            const res = await fetch(`/api/v1/tasks/${taskId}`);
            if (!res.ok) {
              clearInterval(timer);
              resolve({ state: 'FAILURE', info: { error: 'Failed to check status' } });
              return;
            }
            
            const json = await res.json();
            
            // Update progress with detailed info
            if (json.state === 'PROGRESS' && json.info) {
              const processed = json.info.processed || 0;
              const total = json.info.total || 0;
              const currentFile = json.info.current_file || '';
              
              if (total > 0) {
                // Show "Processing X of Y" starting from 1
                const displayProcessed = Math.max(1, processed + 1);
                const percent = Math.min(95, 30 + (processed / total * 65));
                progressFill.style.width = `${percent}%`;
                statusTitle.textContent = `Processing ${displayProcessed} of ${total} documents...`;
                if (currentFile) {
                  statusMessage.textContent = `Current: ${currentFile.substring(0, 40)}${currentFile.length > 40 ? '...' : ''}`;
                } else {
                  statusMessage.textContent = `${Math.round(percent)}% complete`;
                }
              } else {
                // Show initial processing state
                progressFill.style.width = '35%';
                statusTitle.textContent = 'Processing documents...';
                statusMessage.textContent = 'Preparing files for validation';
              }
            }
            
            if (json.state === 'SUCCESS' || json.state === 'FAILURE' || json.state === 'REVOKED' || json.state === 'LIMIT_EXCEEDED') {
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
        };
        
        // Poll immediately
        poll();
        
        const timer = setInterval(poll, interval);
      });
    }
    
    function showSuccess(taskId, taskResult) {
      isSubmitting = false;  // Reset submission flag
      processingStatus.style.display = 'none';
      successStatus.style.display = 'flex';
      startNewBtn.style.display = 'inline-flex';
      
      // Update usage indicator after successful validation
      updateUsageIndicator();
      
      // Change Step 3 indicator to green (completed)
      steps.forEach(step => {
        const num = parseInt(step.dataset.step);
        if (num === 3) {
          step.classList.add('completed');
          step.classList.remove('active');
        }
      });
      
      // Clear previous results
      if (resultsOutput) resultsOutput.innerHTML = '';

      // Determine if the user's rules requested extraction fields
      let hasFields = false;
      try {
        const rulesEl = document.getElementById('rules');
        if (rulesEl && rulesEl.dataset && rulesEl.dataset.json) {
          const parsed = JSON.parse(rulesEl.dataset.json || '{}');
          if (parsed && Array.isArray(parsed.fields) && parsed.fields.length > 0) hasFields = true;
        }
      } catch (e) { /* ignore */ }

      // Check for partial processing (limit reached)
      const resultInfo = (taskResult && taskResult.info) || {};
      const status = resultInfo.status || 'completed';
      const message = resultInfo.message;
      const filesSkipped = resultInfo.files_skipped || 0;
      const filesSucceeded = resultInfo.files_succeeded || 0;
      const totalFiles = resultInfo.total || 0;
      
      let titleText, messageText, isPartial = false;
      
      if (status === 'partial' && filesSkipped > 0) {
        // Partial processing due to limit
        isPartial = true;
        titleText = '⚠️ Partial Processing';
        messageText = message || `Processed ${filesSucceeded} of ${totalFiles} files. ${filesSkipped} files skipped due to free tier limit.`;
      } else {
        // Normal completion
        titleText = hasFields ? 'Extraction Complete!' : 'Validation Complete!';
        messageText = hasFields ? 'Your documents have been processed and extracted successfully.' : 'Your documents have been validated successfully.';
      }

      // Update success title/message
      if (successTitleEl) successTitleEl.textContent = titleText;
      if (successMessageEl) {
        successMessageEl.innerHTML = messageText;
        
        // Add upgrade CTA if partial
        if (isPartial) {
          successMessageEl.innerHTML += `<br><br><strong style="color: #d97706;">📈 Upgrade to process unlimited PDFs!</strong>`;
          successMessageEl.style.color = '#92400e';
        } else {
          successMessageEl.style.color = '';
        }
      }

      // The API returns task result in 'info' field when state is SUCCESS
      // Worker may return progress/result either directly as top-level keys
      // or nested under a `result` key — handle both shapes.
      const taskResultInfo = (taskResult && taskResult.info) || {};

      // Normalize to find result_files.zip regardless of nesting
      let zipFromResult = null;
      if (taskResultInfo.result_files && taskResultInfo.result_files.zip) {
        zipFromResult = taskResultInfo.result_files.zip;
      } else if (taskResultInfo.result && taskResultInfo.result.result_files && taskResultInfo.result.result_files.zip) {
        zipFromResult = taskResultInfo.result.result_files.zip;
      } else if (taskResultInfo.zip) {
        zipFromResult = taskResultInfo.zip;
      }
      if (!zipFromResult) zipFromResult = `/api/v1/tasks/${taskId}/results.zip`;

      // Show download button for ZIP only
      if (zipFromResult) {
        // Fetch results path to show local directory
        // Check if user is accessing locally or over network
        const isLocalAccess = window.location.hostname === 'localhost' || 
                             window.location.hostname === '127.0.0.1' ||
                             window.location.hostname === '';
        
        fetch('/api/v1/results-path')
          .then(response => {
            console.log('Results path response status:', response.status);
            return response.json();
          })
          .then(pathData => {
            console.log('Results path data:', pathData);
            const resultsPath = pathData.results_directory;
            
            // Show path only for local users
            const locationInfo = isLocalAccess ? `
              <div class="results-location" style="margin-top: 1rem; padding: 1rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;">
                <p style="margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 0.9em; color: #475569;">
                  <strong>📁 Results Location:</strong><br>
                  <code style="background: rgba(0,0,0,0.05); padding: 0.2rem 0.4rem; border-radius: 3px; font-family: 'Courier New', monospace;">${resultsPath}</code>
                </p>
              </div>
            ` : '';
            
            downloadLink.innerHTML = `
              <a href="${zipFromResult}" download class="btn btn-primary btn-large download-btn">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 2V14M10 14L6 10M10 14L14 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2 14V16C2 17.1046 18 4 18H16C17.1046 18 18 17.1046 18 16V14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                Download Results
              </a>
              ${locationInfo}
            `;
          })
          .catch(error => {
            console.warn('Failed to fetch results path:', error);
            console.log('Falling back to download link without results path');
            downloadLink.innerHTML = `
              <a href="${zipFromResult}" download class="btn btn-primary btn-large download-btn">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 2V14M10 14L6 10M10 14L14 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2 14V16C2 17.1046 18 4 18H16C17.1046 18 18 17.1046 18 16V14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                Download Results
              </a>
            `;
          });
      } else {
        downloadLink.innerHTML = '<p class="helper">Results are ready but download link is not available.</p>';
      }

      // Show simple completion message (no table rendering)
      if (resultsOutput) {
        const reportUrl = `/api/v1/tasks/${taskId}/report.json`;
        fetch(reportUrl)
          .then(r => r.ok ? r.json() : Promise.reject('no report'))
          .then(j => {
            const infoHtml = `<div class="report-summary">Successfully processed ${j.processed || j.total || '-'} of ${j.total || '-'} documents. Download the ZIP file to view results.</div>`;
            resultsOutput.innerHTML = infoHtml;
          })
          .catch(() => {
            resultsOutput.innerHTML = '<div class="helper">Processing complete. Download the results to view details.</div>';
          });
      }
    }
    
    function showError(message) {
      isSubmitting = false;  // Reset submission flag
      processingStatus.style.display = 'none';
      errorStatus.style.display = 'flex';
      errorMessage.textContent = message;
      submitBtn.style.display = 'inline-flex';
      submitBtn.disabled = false;  // Re-enable button
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
  // Recent/history feature removed — do not store history entries.
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
      submitBtn.disabled = false;  // CRITICAL: Re-enable submit button
      startNewBtn.style.display = 'none';
      downloadLink.innerHTML = '';
      isSubmitting = false;  // Reset submission flag
      
      // Reset rules
      if (window.resetBuilder) window.resetBuilder();
      
      // Go back to step 1 (force reset)
      navigateToStep(1, true);
    });
    
    // Navigation between sections
    const navAutomation = document.getElementById('navAutomation');
    const navHowTo = document.getElementById('navHowTo');
    const navFeatures = document.getElementById('navFeatures');
    const navPricing = document.getElementById('navPricing');
    const automationSection = document.getElementById('automationSection');
    const howToSection = document.getElementById('howToSection');
    const featuresSection = document.getElementById('featuresSection');
    const pricingSection = document.getElementById('pricingSection');
    const networkInfo = document.getElementById('networkInfo');

    if (navUpload && navAutomation && navHowTo && navFeatures && navPricing && uploadSection && automationSection && howToSection && featuresSection && pricingSection) {
      // Features tab (default view)
      navFeatures.addEventListener('click', () => {
        uploadSection.style.display = 'none';
        automationSection.style.display = 'none';
        howToSection.style.display = 'none';
        featuresSection.style.display = 'block';
        pricingSection.style.display = 'none';
        networkInfo.style.display = 'none';
        navFeatures.classList.add('active');
        navUpload.classList.remove('active');
        navPricing.classList.remove('active');
        navAutomation.classList.remove('active');
        navHowTo.classList.remove('active');
        featuresSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });

      // Pricing tab
      navPricing.addEventListener('click', () => {
        uploadSection.style.display = 'none';
        automationSection.style.display = 'none';
        howToSection.style.display = 'none';
        featuresSection.style.display = 'none';
        pricingSection.style.display = 'block';
        networkInfo.style.display = 'none';
        navPricing.classList.add('active');
        navFeatures.classList.remove('active');
        navUpload.classList.remove('active');
        navAutomation.classList.remove('active');
        navHowTo.classList.remove('active');
        pricingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });

      // Try It Now tab (upload section)
      navUpload.addEventListener('click', () => {
        uploadSection.style.display = 'block';
        automationSection.style.display = 'none';
        howToSection.style.display = 'none';
        featuresSection.style.display = 'none';
        pricingSection.style.display = 'none';
        networkInfo.style.display = 'block';
        navUpload.classList.add('active');
        navFeatures.classList.remove('active');
        navPricing.classList.remove('active');
        navAutomation.classList.remove('active');
        navHowTo.classList.remove('active');
        
        // Reset to Step 1 (force reset)
        navigateToStep(1, true);
      });

      // Automation tab
      navAutomation.addEventListener('click', () => {
        uploadSection.style.display = 'none';
        automationSection.style.display = 'block';
        howToSection.style.display = 'none';
        featuresSection.style.display = 'none';
        pricingSection.style.display = 'none';
        networkInfo.style.display = 'none';
        navAutomation.classList.add('active');
        navFeatures.classList.remove('active');
        navPricing.classList.remove('active');
        navUpload.classList.remove('active');
        navHowTo.classList.remove('active');
        window.initAutomation && window.initAutomation();
      });

      // How To tab
      navHowTo.addEventListener('click', () => {
        uploadSection.style.display = 'none';
        automationSection.style.display = 'none';
        howToSection.style.display = 'block';
        featuresSection.style.display = 'none';
        pricingSection.style.display = 'none';
        networkInfo.style.display = 'none';
        howToSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        navHowTo.classList.add('active');
        navFeatures.classList.remove('active');
        navPricing.classList.remove('active');
        navUpload.classList.remove('active');
        navAutomation.classList.remove('active');
      });

      // How To section tabs
      const howtoTabs = document.querySelectorAll('.howto-tab');
      const howtoTabContents = document.querySelectorAll('.howto-tab-content');
      
      howtoTabs.forEach(tab => {
        tab.addEventListener('click', () => {
          const tabName = tab.dataset.tab;
          
          // Remove active class from all tabs and contents
          howtoTabs.forEach(t => t.classList.remove('active'));
          howtoTabContents.forEach(content => {
            content.classList.remove('active');
            content.style.display = 'none'; // Explicitly hide
          });
          
          // Add active class to clicked tab and corresponding content
          tab.classList.add('active');
          const targetContent = document.getElementById(tabName + 'Tab');
          if (targetContent) {
            targetContent.classList.add('active');
            targetContent.style.display = 'block'; // Explicitly show
          }
        });
      });

      // Set default view to Features (landing page)
      featuresSection.style.display = 'block';
      uploadSection.style.display = 'none';
      automationSection.style.display = 'none';
      howToSection.style.display = 'none';
      pricingSection.style.display = 'none';
      networkInfo.style.display = 'none';
      navFeatures.classList.add('active');
    }

    
    // Initialize on step 1
    navigateToStep(1);
    
    // Ensure status displays are hidden on page load
    if (processingStatus) processingStatus.style.display = 'none';
    if (successStatus) successStatus.style.display = 'none';
    if (errorStatus) errorStatus.style.display = 'none';
    if (submitBtn) submitBtn.style.display = 'block';
  }
  
  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
