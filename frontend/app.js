// Main application logic for Valido - user-friendly step-by-step validation
(() => {
  // Trial and License Management
  const TrialManager = {
    async getStatus() {
      try {
        const response = await fetch('/api/v1/users/trial-status');
        if (response.ok) {
          return await response.json();
        }
      } catch (error) {
        console.error('Failed to fetch trial status:', error);
      }
      return null;
    },
    
    async updateUI() {
      const status = await this.getStatus();
      if (!status) return;
      
      const trialStatusEl = document.getElementById('trialStatus');
      const trialTextEl = document.getElementById('trialText');
      const activateBtnEl = document.getElementById('activateLicenseBtn');
      
      if (!trialStatusEl || !trialTextEl) return;
      
      const { trial, access, license_active, license_type } = status;
      
      // Update UI based on status
      if (license_active) {
        // Licensed user
        trialTextEl.textContent = `Licensed (${license_type})`;
        trialStatusEl.classList.remove('warning', 'expired');
        trialStatusEl.classList.add('licensed');
        trialStatusEl.title = 'Thank you for your support!';
        if (activateBtnEl) activateBtnEl.style.display = 'none';
        this.enableApp();
      } else if (trial.expired) {
        // Trial expired
        trialTextEl.textContent = 'Trial Expired';
        trialStatusEl.classList.remove('warning', 'licensed');
        trialStatusEl.classList.add('expired');
        trialStatusEl.title = 'Purchase a license to continue';
        if (activateBtnEl) activateBtnEl.style.display = 'inline-flex';
        
        // ENFORCE: Disable app functionality
        this.disableApp();
        
        // Show purchase prompt
        this.showTrialExpiredModal();
      } else {
        // Trial active
        const days = trial.days_remaining;
        trialTextEl.textContent = `Trial: ${days} day${days !== 1 ? 's' : ''} left`;
        trialStatusEl.classList.remove('expired', 'licensed');
        if (days <= 3) {
          trialStatusEl.classList.add('warning');
          trialStatusEl.title = `${days} days remaining - consider purchasing`;
        } else {
          trialStatusEl.classList.remove('warning');
          trialStatusEl.title = `${days} days remaining in trial`;
        }
        if (activateBtnEl) activateBtnEl.style.display = 'inline-flex';
        this.enableApp();
      }
    },
    
    disableApp() {
      // Disable all buttons and inputs except activation
      document.querySelectorAll('button, input[type="file"], input[type="submit"]').forEach(el => {
        if (!el.closest('.trial-expired-modal') && 
            el.id !== 'activateLicenseBtn' && 
            !el.classList.contains('modal-close')) {
          el.disabled = true;
          el.style.opacity = '0.5';
          el.style.cursor = 'not-allowed';
        }
      });
      
      // Disable navigation tabs
      document.querySelectorAll('.btn-nav').forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = '0.5';
      });
      
      // Add overlay to content
      const container = document.querySelector('.container');
      if (container && !document.getElementById('trial-expired-overlay')) {
        const overlay = document.createElement('div');
        overlay.id = 'trial-expired-overlay';
        overlay.style.cssText = `
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(255, 255, 255, 0.8);
          backdrop-filter: blur(3px);
          z-index: 999;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
          color: #666;
          pointer-events: none;
        `;
        container.appendChild(overlay);
      }
    },
    
    enableApp() {
      // Re-enable all buttons and inputs
      document.querySelectorAll('button, input[type="file"], input[type="submit"]').forEach(el => {
        el.disabled = false;
        el.style.opacity = '';
        el.style.cursor = '';
      });
      
      // Remove overlay
      const overlay = document.getElementById('trial-expired-overlay');
      if (overlay) overlay.remove();
    },
    
    showTrialExpiredModal() {
      // Only show once per session
      if (sessionStorage.getItem('expiredModalShown')) return;
      sessionStorage.setItem('expiredModalShown', 'true');
      
      const modal = document.createElement('div');
      modal.className = 'trial-expired-modal';
      modal.innerHTML = `
        <div class="modal-overlay" style="pointer-events: all;"></div>
        <div class="modal-content" style="max-width: 500px; z-index: 10001;">
          <div class="modal-header">
            <h3>⏰ Trial Period Ended</h3>
          </div>
          <div class="modal-body">
            <p style="margin-bottom: 20px; color: #666; line-height: 1.6;">
              Your 14-day trial has ended. Thank you for trying Valido!
            </p>
            <p style="margin-bottom: 20px; color: #666; line-height: 1.6;">
              To continue using Valido, please purchase a license:
            </p>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
              <div style="margin-bottom: 10px;">
                <strong>💳 Monthly:</strong> $14.99/month
              </div>
              <div>
                <strong>🎁 Annual:</strong> $150/year <span style="color: #10b981;">(Save 17%!)</span>
              </div>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
              <button class="btn btn-primary" style="flex: 1;" onclick="window.open('https://rai89.gumroad.com/l/bdspjn', '_blank');">
                Purchase License
              </button>
              <button class="btn btn-secondary" onclick="document.getElementById('activateLicenseBtn').click();">
                I Have a Key
              </button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
      
      // Make modal non-dismissible (no click to close)
    },
    
    showActivationModal() {
      const modal = document.createElement('div');
      modal.className = 'license-activation-modal';
      modal.innerHTML = `
        <div class="modal-overlay"></div>
        <div class="modal-content" style="max-width: 500px;">
          <div class="modal-header">
            <h3>🔑 Activate License</h3>
            <button class="modal-close" onclick="this.closest('.license-activation-modal').remove()">×</button>
          </div>
          <div class="modal-body">
            <p style="margin-bottom: 20px; color: #666;">
              Enter the email address you used to purchase on Gumroad:
            </p>
            
            <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px; margin-bottom: 20px; border-radius: 4px;">
              <p style="margin: 0; font-size: 13px; color: #1e40af; line-height: 1.5;">
                <strong>ℹ️ Internet Required:</strong> License activation requires internet connection to validate with our server. 
                Your PDF files are processed 100% offline and never uploaded.
              </p>
            </div>
            
            <form id="licenseActivationForm">
              <div style="margin-bottom: 15px;">
                <label for="licenseKey" style="display: block; margin-bottom: 5px; font-weight: 500;">Purchase Email:</label>
                <input 
                  type="email" 
                  id="licenseKey" 
                  name="licenseKey" 
                  placeholder="your@email.com"
                  style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;"
                  required
                />
                <small style="color: #666; font-size: 12px;">The email address used when purchasing on Gumroad</small>
              </div>
              <div style="margin-bottom: 20px;">
                <label for="licenseType" style="display: block; margin-bottom: 5px; font-weight: 500;">License Type:</label>
                <select 
                  id="licenseType" 
                  name="licenseType"
                  style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px;"
                  required
                >
                  <option value="monthly">Monthly ($14.99/month)</option>
                  <option value="annual">Annual ($150/year)</option>
                </select>
              </div>
              <div id="activationError" style="display: none; color: #dc2626; margin-bottom: 15px; padding: 10px; background: #fee2e2; border-radius: 4px;"></div>
              <div id="activationSuccess" style="display: none; color: #059669; margin-bottom: 15px; padding: 10px; background: #d1fae5; border-radius: 4px;"></div>
              <div style="display: flex; gap: 10px;">
                <button type="submit" class="btn btn-primary" style="flex: 1;">Activate</button>
                <button type="button" class="btn btn-ghost" onclick="this.closest('.license-activation-modal').remove();">Cancel</button>
              </div>
            </form>
            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
              <p style="font-size: 13px; color: #999;">
                Don't have a license yet? <a href="https://rai89.gumroad.com/l/bdspjn" target="_blank" style="color: #3b82f6;">Monthly ($14.99)</a> or <a href="https://rai89.gumroad.com/l/eyuiy" target="_blank" style="color: #3b82f6;">Annual ($150)</a>
              </p>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
      
      // Handle form submission
      const form = document.getElementById('licenseActivationForm');
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const purchaseEmail = document.getElementById('licenseKey').value.trim();
        const licenseType = document.getElementById('licenseType').value;
        const errorEl = document.getElementById('activationError');
        const successEl = document.getElementById('activationSuccess');
        const submitBtn = form.querySelector('button[type="submit"]');
        
        // Reset messages
        errorEl.style.display = 'none';
        successEl.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.textContent = 'Validating...';
        
        try {
          // Use NEW email-based endpoint
          const response = await fetch('/api/v1/users/activate-license-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ purchase_email: purchaseEmail, license_type: licenseType })
          });
          
          const data = await response.json();
          
          if (response.ok) {
            successEl.textContent = data.message || 'License activated successfully! Reloading...';
            successEl.style.display = 'block';
            setTimeout(() => {
              window.location.reload();
            }, 1500);
          } else {
            errorEl.textContent = data.detail || 'Could not validate purchase';
            errorEl.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Activate';
          }
        } catch (error) {
          errorEl.textContent = 'Connection error. Please check your internet and try again.';
          errorEl.style.display = 'block';
          submitBtn.disabled = false;
          submitBtn.textContent = 'Activate';
        }
      });
      
      modal.querySelector('.modal-overlay').addEventListener('click', () => {
        modal.remove();
      });
    }
  };
  
  window.TrialManager = TrialManager;
  
  function init() {
    // Update trial status on load
    TrialManager.updateUI();
    
    // Refresh trial status every minute
    setInterval(() => TrialManager.updateUI(), 60000);
    
    // Fetch and display beta banner (now trial/license banner)
    function updateBetaBanner() {
      const betaBanner = document.getElementById('betaBanner');
      
      if (!betaBanner) return;
      
      fetch('/api/v1/banner')
        .then(response => response.json())
        .then(data => {
          if (data.type === 'beta' || data.type === 'trial') {
            // Show banner
            betaBanner.style.display = 'block';
            
            // Update content
            const message = betaBanner.querySelector('.beta-banner-message');
            const details = betaBanner.querySelector('.beta-banner-details');
            const link = betaBanner.querySelector('#betaBannerLink');
            
            if (message) message.textContent = data.message || '';
            if (details) details.textContent = data.details || '';
            
            if (link && data.link) {
              link.href = data.link;
              link.textContent = data.linkText || 'Learn More';
              link.style.display = 'inline-block';
            } else if (link) {
              link.style.display = 'none';
            }
          } else {
            // Hide banner
            betaBanner.style.display = 'none';
          }
        })
        .catch(error => {
          console.warn('Failed to fetch banner info:', error);
          // Hide banner on error
          betaBanner.style.display = 'none';
        });
    }
    
    // Update banner on page load
    updateBetaBanner();
    
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

    // Usage tracking removed - will be replaced with trial/license status
    
    // License activation button
    const activateLicenseBtn = document.getElementById('activateLicenseBtn');
    if (activateLicenseBtn) {
      activateLicenseBtn.addEventListener('click', () => {
        TrialManager.showActivationModal();
      });
    }
    
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
                <button class="share-option" onclick="window.open('mailto:?subject=Check out Valido - PDF Validation Tool&body=I found this amazing PDF validation tool that runs locally on your computer. No cloud upload, fully private!%0A%0ACheck it out: https://valido-app.github.io/', '_blank')">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
                    <path d="M3 7L12 13L21 7" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>Share via Email</span>
                </button>
                
                <button class="share-option" onclick="navigator.clipboard.writeText('https://valido-app.github.io/').then(() => { alert('Link copied to clipboard!'); this.closest('.share-modal').remove(); })">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M8 5H6C4.89543 5 4 5.89543 4 7V19C4 20.1046 4.89543 21 6 21H16C17.1046 21 18 20.1046 18 19V18" stroke="currentColor" stroke-width="2"/>
                    <rect x="8" y="3" width="12" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>Copy Link</span>
                </button>
                
                <button class="share-option" onclick="window.open('https://twitter.com/intent/tweet?text=Check out Valido - a privacy-first PDF validation tool that runs locally on your computer!&url=https://valido-app.github.io/', '_blank', 'width=550,height=420')">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M23 3a10.9 10.9 0 01-3.14 1.53 4.48 4.48 0 00-7.86 3v1A10.66 10.66 0 013 4s-4 9 5 13a11.64 11.64 0 01-7 2c9 5 20 0 20-11.5a4.5 4.5 0 00-.08-.83A7.72 7.72 0 0023 3z" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>Share on Twitter</span>
                </button>
                
                <button class="share-option" onclick="window.open('https://www.linkedin.com/sharing/share-offsite/?url=https://valido-app.github.io/', '_blank', 'width=550,height=420')">
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
    
    // Feedback button functionality
    const feedbackBtn = document.getElementById('feedbackBtn');
    if (feedbackBtn) {
      feedbackBtn.addEventListener('click', () => {
        const modal = document.createElement('div');
        modal.className = 'share-modal';
        modal.innerHTML = `
          <div class="share-modal-overlay"></div>
          <div class="share-modal-content">
            <div class="share-modal-header">
              <h3>Report Issues / Request Features</h3>
              <button class="share-modal-close" onclick="this.closest('.share-modal').remove()">×</button>
            </div>
            <div class="share-modal-body">
              <p style="margin-bottom: 20px; color: #666; line-height: 1.6;">
                Found a bug? Have a feature request? We'd love to hear from you!<br>
                <strong style="color: #764ba2;">💡 Tip:</strong> For common issues and solutions, check the <strong>Troubleshooting</strong> section in the "How To Use" tab first.
              </p>
              
              <form id="feedbackForm" action="https://formspree.io/f/movyvknd" method="POST" style="display: flex; flex-direction: column; gap: 15px;">
                <div>
                  <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Your Email (optional)</label>
                  <input type="email" name="email" placeholder="your@email.com" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;">
                </div>
                
                <div>
                  <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Type</label>
                  <select name="type" required style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;">
                    <option value="">Select...</option>
                    <option value="bug">🐛 Bug Report</option>
                    <option value="feature">✨ Feature Request</option>
                    <option value="question">❓ Question</option>
                    <option value="other">💬 Other</option>
                  </select>
                </div>
                
                <div>
                  <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Message *</label>
                  <textarea name="message" required placeholder="Be specific! Instead of 'Does not work', tell us:
• What were you trying to do?
• What did you expect to happen?
• What actually happened?
• Any error messages?
• Copy/paste relevant logs from data/logs/ folder if available" rows="6" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; resize: vertical;"></textarea>
                </div>
                
                <button type="submit" style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 12px 24px; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 15px;">
                  Send Feedback
                </button>
              </form>
              
              <div id="feedbackSuccess" style="display: none; text-align: center; padding: 20px;">
                <div style="font-size: 48px; margin-bottom: 10px;">✅</div>
                <h3 style="color: #10b981; margin-bottom: 10px;">Thank you!</h3>
                <p style="color: #666;">Your feedback has been sent successfully.</p>
              </div>
            </div>
          </div>
        `;
        document.body.appendChild(modal);
        
        // Close on overlay click
        modal.querySelector('.share-modal-overlay').addEventListener('click', () => {
          modal.remove();
        });
        
        // Handle form submission
        const form = modal.querySelector('#feedbackForm');
        form.addEventListener('submit', async (e) => {
          e.preventDefault();
          
          const formData = new FormData(form);
          
          try {
            const response = await fetch(form.action, {
              method: 'POST',
              body: formData,
              headers: {
                'Accept': 'application/json'
              }
            });
            
            if (response.ok) {
              form.style.display = 'none';
              modal.querySelector('#feedbackSuccess').style.display = 'block';
              setTimeout(() => modal.remove(), 3000);
            } else {
              alert('Failed to send feedback. Please try again.');
            }
          } catch (error) {
            alert('Failed to send feedback. Please check your internet connection.');
          }
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
          submitBtn.disabled = false;
          submitBtn.style.pointerEvents = 'auto';
        }
        // Hide "Validate More Documents" button until processing is complete
        if (startNewBtn) startNewBtn.style.display = 'none';
        // Clear any previous results
        if (resultsOutput) resultsOutput.innerHTML = '';
        if (window._validoSubmissionState) {
          window._validoSubmissionState.isSubmitting = false;  // Reset submission flag
          window._validoSubmissionState.completed = false;     // New run starting
        }
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
      
      // Dispatch event for extraction preview
      window.dispatchEvent(new CustomEvent('filesUploaded', {
        detail: { files: selectedFiles }
      }));
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
    
    // Table Wizard Modal handlers
    const openTableWizardBtn = document.getElementById('openTableWizardBtn');
    const tableWizardModal = document.getElementById('tableWizardModal');
    const tableWizardClose = document.getElementById('tableWizardClose');
    const tableWizardCancel = document.getElementById('tableWizardCancel');
    
    if (openTableWizardBtn && tableWizardModal) {
      openTableWizardBtn.addEventListener('click', async () => {
        if (selectedFiles.length === 0) {
          window.toast && window.toast.error('Please upload a PDF file first');
          return;
        }
        
        // For now, use the first file (could be enhanced to support multiple files)
        const file = selectedFiles[0];
        if (!file.name.toLowerCase().endsWith('.pdf')) {
          window.toast && window.toast.error('Table extraction only works with PDF files');
          return;
        }
        
        // Show modal
        tableWizardModal.style.display = 'flex';
        
        // Initialize table wizard with the file
        if (window.tableWizard) {
          await window.tableWizard.init(file);
        } else {
          console.error('Table wizard not loaded');
        }
      });
      
      // Close modal handlers
      if (tableWizardClose) {
        tableWizardClose.addEventListener('click', () => {
          tableWizardModal.style.display = 'none';
        });
      }
      
      if (tableWizardCancel) {
        tableWizardCancel.addEventListener('click', () => {
          tableWizardModal.style.display = 'none';
        });
      }
      
      // Close on overlay click
      tableWizardModal.addEventListener('click', (e) => {
        if (e.target === tableWizardModal) {
          tableWizardModal.style.display = 'none';
        }
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
        
        if (rulesEl && rulesEl.dataset && rulesEl.dataset.json) {
          const rules = JSON.parse(rulesEl.dataset.json);
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
    // Use window-level flag to prevent duplicates AND to ensure we only attach
    // the submit listener once, even if this init block runs multiple times.
    if (!window._validoSubmissionState) {
      window._validoSubmissionState = {
        isSubmitting: false,
        lastSubmitTime: 0,
        completed: false,
        _listenerAttached: false,
      };
    }

    // Prevent Enter key from accidentally submitting the form on Step 3.
    if (form) {
      form.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
        }
      });
    }

    if (form && !window._validoSubmissionState._listenerAttached) {
      window._validoSubmissionState._listenerAttached = true;

      const listenerId = Math.random().toString(36).substr(2, 9);

      form.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        
        const now = Date.now();
        console.log(`🔍 [${listenerId}] Submit event fired at ${new Date().toISOString()}. isSubmitting: ${window._validoSubmissionState.isSubmitting}, lastSubmit: ${now - window._validoSubmissionState.lastSubmitTime}ms ago`);
        console.trace('Submit event call stack:');

        // Hard lock: don't allow another submission once a run has completed
        // until the user explicitly starts a new run.
        if (window._validoSubmissionState.completed) {
          console.warn(`⚠️ [${listenerId}] Submission blocked - previous run already completed. Click "Validate More Documents" to start a new run.`);
          return;
        }
      
      // Prevent duplicate submissions
      if (window._validoSubmissionState.isSubmitting) {
        console.warn(`⚠️ [${listenerId}] Duplicate submission blocked - already submitting`);
        return;
      }
      
      // Also block if submitted within last 3 seconds
      if (now - window._validoSubmissionState.lastSubmitTime < 3000) {
        console.warn(`⚠️ [${listenerId}] Duplicate submission blocked - too soon (${now - window._validoSubmissionState.lastSubmitTime}ms)`);
        return;
      }
      
        console.log(`✅ [${listenerId}] Submission allowed, setting isSubmitting = true`);
        window._validoSubmissionState.isSubmitting = true;
        window._validoSubmissionState.lastSubmitTime = now;
      
      // Disable button immediately to prevent double-click
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.style.pointerEvents = 'none';
      }
      
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
      
        if (!files || files.length === 0) {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.style.pointerEvents = 'auto';
        }
        window._validoSubmissionState.isSubmitting = false;
        showError('Please select at least one file to validate.');
        navigateToStep(1);
        return;
      }

      // Limit to 500 files per batch
        if (files.length > 500) {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.style.pointerEvents = 'auto';
        }
        window._validoSubmissionState.isSubmitting = false;
        showError('Maximum 500 files allowed per batch. Please split your files into smaller batches.');
        navigateToStep(1);
        return;
      }
      
      
        const fd = new FormData();
      for (let i = 0; i < files.length; i++) {
        fd.append('files', files[i]);
      }
      if (rules) fd.append('rules', rules);
      
      // Show processing UI BEFORE fetch
        submitBtn.style.display = 'none';
      startNewBtn.style.display = 'none';
      processingStatus.style.display = 'flex';
      successStatus.style.display = 'none';
      errorStatus.style.display = 'none';
      statusTitle.textContent = 'Uploading your documents...';
      statusMessage.textContent = 'Please wait while we process your files';
      progressFill.style.width = '10%';
      
        try {
          const res = await fetch('/api/v1/submit', { method: 'POST', body: fd });
        
        if (!res.ok) {
          if (res.status === 429) {
            // Duplicate submission blocked by server
            const errorData = await res.json().catch(() => ({ detail: 'Duplicate submission detected' }));
            console.warn('⚠️ Server blocked duplicate submission:', errorData);
            // Hide processing UI and show submit button again
            processingStatus.style.display = 'none';
            submitBtn.style.display = 'inline-flex';
            submitBtn.disabled = false;
            submitBtn.style.pointerEvents = 'auto';
            window._validoSubmissionState.isSubmitting = false;
            return;
          }
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

          if (result.state === 'SUCCESS') {
          showSuccess(taskId, result);
        } else if (result.state === 'FAILURE') {
          showError(result.info?.error || 'Validation failed. Please try again.');
        } else {
          showError('Validation timed out. Please try again or contact support.');
        }
          
        } catch (err) {
          showError(err.message || 'An unexpected error occurred. Please try again.');
        } finally {
          // Re-enable button after processing completes (success or failure)
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.pointerEvents = 'auto';
          }
          window._validoSubmissionState.isSubmitting = false;  // Reset flag
        }
      });
    }
    
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
            return response.json();
          })
          .then(pathData => {
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
                  <path d="M2 14V16C2 17.1046 2.89543 18 4 18H16C17.1046 18 18 17.1046 18 16V14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                Download Results
              </a>
              ${locationInfo}
            `;
          })
          .catch(error => {
            console.warn('Failed to fetch results path:', error);
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
        // We no longer fetch /report.json because the backend does not create it.
        // Instead, we rely on the task status, which already includes results_path
        // and progress info populated by the worker.
        fetch(`/api/v1/tasks/${taskId}`)
          .then(r => r.ok ? r.json() : Promise.reject('no status'))
          .then(statusData => {
            const info = statusData?.info || {};
            const processed = info.processed ?? info.total ?? 0;
            const total = info.total ?? info.total_files ?? processed;
            const resultsPath = info.results_path || `results\\${taskId}`;

            const infoHtml = `
              <div class="report-summary">
                <p style="margin-bottom: 12px;">✅ Successfully processed <strong>${processed}</strong> of <strong>${total}</strong> documents.</p>
                <p style="font-size: 13px; color: #666; margin: 0;">📁 Results saved to: <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-size: 12px;">${resultsPath}</code></p>
              </div>`;
            resultsOutput.innerHTML = infoHtml;
          })
          .catch(() => {
            const resultsPath = `results\\${taskId}`;
            const infoHtml = `
              <div class="report-summary">
                <p style="margin-bottom: 12px;">✅ Processing complete.</p>
                <p style="font-size: 13px; color: #666; margin: 0;">📁 Results saved to: <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-size: 12px;">${resultsPath}</code></p>
              </div>`;
            resultsOutput.innerHTML = infoHtml;
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
      submitBtn.disabled = false;
      submitBtn.style.pointerEvents = 'auto';
      startNewBtn.style.display = 'none';
      downloadLink.innerHTML = '';
      window._validoSubmissionState.isSubmitting = false;  // Reset submission flag
      
      // Reset rules
      if (window.resetBuilder) window.resetBuilder();
      
      // Go back to step 1 (force reset)
      navigateToStep(1, true);
    });
    
    // Navigation between sections
    const navAutomation = document.getElementById('navAutomation');
    const navHowTo = document.getElementById('navHowTo');
    const navFeatures = document.getElementById('navFeatures');
    const automationSection = document.getElementById('automationSection');
    const howToSection = document.getElementById('howToSection');
    const featuresSection = document.getElementById('featuresSection');

    if (navUpload && navAutomation && navHowTo && navFeatures && uploadSection && automationSection && howToSection && featuresSection) {
      // Features tab (default view)
      navFeatures.addEventListener('click', () => {
        uploadSection.style.display = 'none';
        automationSection.style.display = 'none';
        howToSection.style.display = 'none';
        featuresSection.style.display = 'block';
        navFeatures.classList.add('active');
        navUpload.classList.remove('active');
        navAutomation.classList.remove('active');
        navHowTo.classList.remove('active');
        featuresSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });

      // Try It Now tab (upload section)
      navUpload.addEventListener('click', () => {
        uploadSection.style.display = 'block';
        automationSection.style.display = 'none';
        howToSection.style.display = 'none';
        featuresSection.style.display = 'none';
        navUpload.classList.add('active');
        navFeatures.classList.remove('active');
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
        navAutomation.classList.add('active');
        navFeatures.classList.remove('active');
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
        howToSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        navHowTo.classList.add('active');
        navFeatures.classList.remove('active');
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
