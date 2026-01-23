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
              Your 7-day trial has ended. Thank you for trying Valido!
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
                Activate License
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
                <strong>ℹ️ Internet Required:</strong> License activation needs internet to validate your purchase.
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
      shareBtn.addEventListener('click', async () => {
        const baseUrl = 'https://valido.site';

        const templates = {
          short: `Valido — validate & automate checks on PDFs (Windows). Runs locally (no upload).\n${baseUrl}`,
          business: `Check out Valido — PDF validation and automation for Windows.\n\nWorks on any text-based PDF (selectable text). Build rules to check content, dates, signatures, totals, page metadata, and more — then export results.\n\nLearn more: ${baseUrl}`,
          it: `Valido (Windows) — validate PDFs locally (no cloud upload; no OCR by design for reliability).\n\nWorks on any text-based PDF (selectable text). Website: ${baseUrl}`
        };

        let selectedTemplateKey = 'business';
        const getShareText = () => templates[selectedTemplateKey] || templates.business;
        const emailSubject = encodeURIComponent('Check out Valido — PDF validation tool');

        // NOTE: Valido is a Windows app; avoid Web Share API here.
        // Some embedded browsers/webviews expose navigator.share but behave inconsistently.

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
              <p style="margin-bottom: 14px; color: #666; line-height: 1.6;">
                Copy a ready-to-send message, or share via email/LinkedIn.
              </p>

              <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px;">
                <div style="font-weight:600; margin-bottom:6px;">Message to copy</div>
                <div style="display:flex; gap:8px; margin-bottom: 8px; flex-wrap: wrap;">
                  <button class="btn btn-ghost" type="button" id="btnShareTplShort" style="padding:6px 10px; font-size:12px;">Short</button>
                  <button class="btn btn-ghost" type="button" id="btnShareTplBusiness" style="padding:6px 10px; font-size:12px;">Business</button>
                  <button class="btn btn-ghost" type="button" id="btnShareTplIT" style="padding:6px 10px; font-size:12px;">IT / Security</button>
                </div>
                <textarea id="shareMessage" readonly rows="5" style="width:100%; resize:none; padding:10px; border:1px solid #e5e7eb; border-radius:8px; font-size:13px; color:#111;">${templates.business}</textarea>
                <div style="display:flex; gap:10px; margin-top:10px;">
                  <button class="btn btn-primary" type="button" id="btnCopyShare">Copy message</button>
                  <button class="btn btn-ghost" type="button" id="btnCopyLink">Copy link only</button>
                  <button class="btn btn-ghost" type="button" id="btnShowQr">QR</button>
                </div>

                <div id="qrWrap" style="display:none; margin-top:10px; text-align:center;">
                  <div style="font-size:12px; color:#64748b; margin-bottom:8px;">Scan to open ${baseUrl}</div>
                  <div style="font-size:12px; color:#475569; line-height:1.5; padding:10px; border:1px dashed #cbd5e1; border-radius:10px; background:#fff;">
                    QR rendering is optional. Use <strong>Copy link only</strong> if your environment blocks external resources.
                  </div>
                </div>
              </div>
              
              <div class="share-options" style="margin-top: 14px;">
                <button class="share-option" type="button" id="btnShareEmail">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
                    <path d="M3 7L12 13L21 7" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>Share via Email</span>
                </button>

                <button class="share-option" type="button" id="btnShareLinkedIn">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z" stroke="currentColor" stroke-width="2"/>
                    <circle cx="4" cy="4" r="2" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>Share on LinkedIn</span>
                </button>

                <button class="share-option" type="button" id="btnShareWhatsApp">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M20 12a8 8 0 0 1-11.9 7L4 20l1-4.1A8 8 0 1 1 20 12Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                    <path d="M9.5 9.5c.3-.7-.3-1.6-.7-2C8.4 7 8 7 7.6 7c-.3 0-.7.1-.9.5-.3.5-.6 1.2-.6 2 0 .8.6 1.9 1 2.4 1.3 1.8 3 3.2 5.2 4 .7.3 1.6.5 2.3.3.5-.2 1.5-.7 1.7-1.4.2-.7.2-1.3.1-1.4-.1-.1-.4-.2-.8-.4l-2.1-1c-.3-.1-.6-.2-.9.2-.3.4-.9 1.1-1.1 1.3-.2.2-.4.2-.7.1-.3-.1-1.4-.5-2.6-1.6-1-.9-1.6-2.1-1.8-2.4-.2-.3 0-.5.1-.7.1-.2.3-.4.4-.6.1-.2.2-.4.3-.6Z" fill="currentColor"/>
                  </svg>
                  <span>Share on WhatsApp</span>
                </button>

                <button class="share-option" type="button" id="btnShareX">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M4 4l7.5 8.8L4.5 20H7l5.1-5.8L17 20h3L13.2 12.2 19.5 4H17l-4.6 5.2L8 4H4Z" fill="currentColor"/>
                  </svg>
                  <span>Share on X</span>
                </button>

                <button class="share-option" type="button" id="btnShareReddit">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="13" r="7" stroke="currentColor" stroke-width="2"/>
                    <path d="M16 10c1.5-1 3.5-.5 4 1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    <path d="M8 10c-1.5-1-3.5-.5-4 1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    <path d="M10 13h0M14 13h0" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
                    <path d="M9.5 15.5c.7.7 1.6 1 2.5 1s1.8-.3 2.5-1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    <path d="M13 6l1-3 4 1" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span>Share on Reddit</span>
                </button>
              </div>
            </div>
          </div>
        `;
        document.body.appendChild(modal);

        const copyToClipboard = async (text) => {
          try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
              await navigator.clipboard.writeText(text);
            } else {
              // Fallback for environments without clipboard API.
              const ta = document.createElement('textarea');
              ta.value = text;
              ta.style.position = 'fixed';
              ta.style.left = '-9999px';
              document.body.appendChild(ta);
              ta.focus();
              ta.select();
              document.execCommand('copy');
              ta.remove();
            }
            alert('Copied to clipboard');
          } catch (e) {
            alert('Could not copy automatically. Please select and copy the text manually.');
          }
        };

        const setTemplate = (key) => {
          selectedTemplateKey = key;
          const ta = modal.querySelector('#shareMessage');
          if (ta) ta.value = getShareText();
        };

        // Template buttons
        modal.querySelector('#btnShareTplShort')?.addEventListener('click', () => setTemplate('short'));
        modal.querySelector('#btnShareTplBusiness')?.addEventListener('click', () => setTemplate('business'));
        modal.querySelector('#btnShareTplIT')?.addEventListener('click', () => setTemplate('it'));

        modal.querySelector('#btnCopyShare')?.addEventListener('click', async () => {
          await copyToClipboard(getShareText());
          modal.remove();
        });
        modal.querySelector('#btnCopyLink')?.addEventListener('click', async () => {
          await copyToClipboard(baseUrl);
          modal.remove();
        });

        modal.querySelector('#btnShowQr')?.addEventListener('click', () => {
          const qrWrap = modal.querySelector('#qrWrap');
          if (!qrWrap) return;

          if (qrWrap.style.display === 'none') {
            qrWrap.style.display = 'block';
          } else {
            qrWrap.style.display = 'none';
          }
        });

        modal.querySelector('#btnShareEmail')?.addEventListener('click', () => {
          const body = encodeURIComponent(getShareText());
          window.open(`mailto:?subject=${emailSubject}&body=${body}`, '_blank');
          modal.remove();
        });
        modal.querySelector('#btnShareLinkedIn')?.addEventListener('click', () => {
          // Prefer prefilled text where possible.
          // LinkedIn often restricts arbitrary prefill, but the shareArticle endpoint can include a title/summary.
          // If LinkedIn ignores these params, the fallback still shares the canonical URL.
          const linkedInTitle = encodeURIComponent('Valido — PDF validation & automation');
          const linkedInSummary = encodeURIComponent(getShareText());
          const linkedInSource = encodeURIComponent('valido.site');
          const shareUrl = encodeURIComponent(baseUrl);
          const liUrl = `https://www.linkedin.com/shareArticle?mini=true&url=${shareUrl}&title=${linkedInTitle}&summary=${linkedInSummary}&source=${linkedInSource}`;
          window.open(liUrl, '_blank', 'width=760,height=720');
          modal.remove();
        });

        modal.querySelector('#btnShareWhatsApp')?.addEventListener('click', () => {
          const text = encodeURIComponent(getShareText());
          window.open(`https://wa.me/?text=${text}`, '_blank');
          modal.remove();
        });

        modal.querySelector('#btnShareX')?.addEventListener('click', () => {
          const text = encodeURIComponent(getShareText());
          window.open(`https://twitter.com/intent/tweet?text=${text}`, '_blank');
          modal.remove();
        });

        modal.querySelector('#btnShareReddit')?.addEventListener('click', () => {
          const title = encodeURIComponent('Valido — PDF validation & automation');
          const url = encodeURIComponent(baseUrl);
          window.open(`https://www.reddit.com/submit?url=${url}&title=${title}`, '_blank');
          modal.remove();
        });

        // Close on overlay click (but NOT when clicking inside the modal content)
        modal.querySelector('.share-modal-overlay')?.addEventListener('click', () => {
          modal.remove();
        });

        // Prevent overlay click handler from firing when user clicks inside the modal
        modal.querySelector('.share-modal-content')?.addEventListener('click', (e) => {
          e.stopPropagation();
        });
      });
    }
    
    // Check for updates button
    const checkUpdatesBtn = document.getElementById('checkUpdatesBtn');
    if (checkUpdatesBtn) {
      checkUpdatesBtn.addEventListener('click', () => {
        UpdateChecker.checkForUpdates();
      });
    }
    
    // Feedback button functionality with smart rating system
    const feedbackBtn = document.getElementById('feedbackBtn');
    if (feedbackBtn) {
      feedbackBtn.addEventListener('click', () => {
        // Check if user has completed a validation and hasn't rated yet
        const hasCompletedValidation = localStorage.getItem('validationCompleted') === 'true';
        const hasRated = localStorage.getItem('userHasRated') === 'true';
        const showRatingFirst = hasCompletedValidation && !hasRated;
        
        const modal = document.createElement('div');
        modal.className = 'share-modal';
        
        if (showRatingFirst) {
          // Show rating prompt first
          modal.innerHTML = `
            <div class="share-modal-overlay"></div>
            <div class="share-modal-content">
              <div class="share-modal-header">
                <h3>How's your experience with Valido?</h3>
                <button class="share-modal-close" onclick="this.closest('.share-modal').remove()">×</button>
              </div>
              <div class="share-modal-body">
                <p style="margin-bottom: 25px; color: #666; line-height: 1.6; text-align: center;">
                  You've completed your first validation! We'd love to hear your thoughts.
                </p>
                
                <div id="ratingStep" style="text-align: center;">
                  <div style="margin-bottom: 20px;">
                    <div class="star-rating" style="font-size: 48px; cursor: pointer; user-select: none;">
                      <span class="star" data-rating="1">☆</span>
                      <span class="star" data-rating="2">☆</span>
                      <span class="star" data-rating="3">☆</span>
                      <span class="star" data-rating="4">☆</span>
                      <span class="star" data-rating="5">☆</span>
                    </div>
                  </div>
                  <p style="color: #999; font-size: 14px;">Click to rate your experience</p>
                  <button onclick="this.closest('.share-modal').remove(); localStorage.setItem('userHasRated', 'true');" style="margin-top: 15px; background: #e5e7eb; color: #6b7280; padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">Skip for now</button>
                </div>
                
                <div id="testimonialStep" style="display: none;">
                  <form id="testimonialForm" action="https://formspree.io/f/movyvknd" method="POST" style="display: flex; flex-direction: column; gap: 15px;">
                    <input type="hidden" name="type" value="testimonial">
                    <input type="hidden" name="rating" id="ratingValue">
                    
                    <div style="text-align: center; margin-bottom: 15px;">
                      <div style="font-size: 48px; margin-bottom: 10px;" id="ratingDisplay"></div>
                      <p style="color: #10b981; font-weight: 600; font-size: 18px;">Thank you for the great rating!</p>
                      <p style="color: #666; font-size: 14px;">Would you like to share your experience publicly?</p>
                    </div>
                    
                    <div>
                      <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Your Name *</label>
                      <input type="text" name="name" required placeholder="John Smith" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;">
                    </div>
                    
                    <div>
                      <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Job Title / Company *</label>
                      <input type="text" name="title" required placeholder="Accountant at ABC Corp" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;">
                    </div>
                    
                    <div>
                      <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">LinkedIn Profile (optional)</label>
                      <input type="url" name="linkedin" placeholder="https://linkedin.com/in/yourprofile" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;">
                    </div>
                    
                    <div>
                      <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Your Testimonial *</label>
                      <textarea name="testimonial" required placeholder="What do you like about Valido? How has it helped you?" rows="4" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; resize: vertical;"></textarea>
                    </div>
                    
                    <button type="submit" style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 12px 24px; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 15px;">
                      Submit Testimonial
                    </button>
                    <button type="button" onclick="this.closest('.share-modal').remove(); localStorage.setItem('userHasRated', 'true');" style="background: #e5e7eb; color: #6b7280; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">
                      Skip - Don't share publicly
                    </button>
                  </form>
                </div>
                
                <div id="improvementStep" style="display: none;">
                  <form id="improvementForm" action="https://formspree.io/f/movyvknd" method="POST" style="display: flex; flex-direction: column; gap: 15px;">
                    <input type="hidden" name="type" value="improvement">
                    <input type="hidden" name="rating" id="improvementRatingValue">
                    
                    <div style="text-align: center; margin-bottom: 15px;">
                      <div style="font-size: 48px; margin-bottom: 10px;" id="improvementRatingDisplay"></div>
                      <p style="color: #d97706; font-weight: 600; font-size: 18px;">Thanks for your honest feedback</p>
                      <p style="color: #666; font-size: 14px;">Help us improve! What should we work on?</p>
                    </div>
                    
                    <div>
                      <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">What needs improvement? *</label>
                      <textarea name="improvement" required placeholder="Be specific:
• What features are missing?
• What's confusing or difficult?
• What bugs did you encounter?
• What would make Valido more useful for you?" rows="6" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; resize: vertical;"></textarea>
                    </div>
                    
                    <div>
                      <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Your Email (optional - for follow-up)</label>
                      <input type="email" name="email" placeholder="your@email.com" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;">
                    </div>
                    
                    <button type="submit" style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 12px 24px; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 15px;">
                      Send Feedback
                    </button>
                  </form>
                </div>
                
                <div id="feedbackSuccess" style="display: none; text-align: center; padding: 20px;">
                  <div style="font-size: 48px; margin-bottom: 10px;">✅</div>
                  <h3 style="color: #10b981; margin-bottom: 10px;">Thank you!</h3>
                  <p style="color: #666;">Your feedback has been received.</p>
                </div>
              </div>
            </div>
          `;
        } else {
          // Show normal feedback form
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

              <div style="background:#eff6ff; border-left: 4px solid #3b82f6; padding: 12px; margin-bottom: 14px; border-radius: 6px;">
                <div style="font-weight:600; color:#1e40af; margin-bottom: 4px;">Want a guaranteed response?</div>
                <div style="font-size:13px; color:#1e3a8a; line-height:1.5;">
                  If the in-app send fails (offline / firewall), you can use <strong>Send via Email</strong> below — it includes useful diagnostic details.
                </div>
              </div>
              
              <form id="feedbackForm" action="https://formspree.io/f/movyvknd" method="POST" style="display: flex; flex-direction: column; gap: 15px;">
                <div>
                  <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Your Email (optional)</label>
                  <input type="email" name="email" placeholder="your@email.com" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;">
                </div>

                <!-- Honeypot (helps reduce automated spam) -->
                <div style="position:absolute; left:-9999px; height:0; overflow:hidden;" aria-hidden="true">
                  <label>Website</label>
                  <input type="text" name="website" tabindex="-1" autocomplete="off">
                </div>

                <input type="hidden" name="source" value="valido-app">
                <input type="hidden" name="client_time" value="${new Date().toISOString()}">
                <input type="hidden" name="app_url" value="${(window.location && window.location.href) ? window.location.href : ''}">
                <input type="hidden" name="user_agent" value="${navigator.userAgent}">

                <!-- Helps email deliverability & inbox rules in Formspree -->
                <input type="hidden" name="_subject" value="Valido feedback">
                
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

                <div style="display:flex; gap:10px; align-items:center;">
                  <button type="submit" id="btnSendFeedback" style="flex: 1; background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 12px 24px; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 15px;">
                    Send Feedback
                  </button>
                  <button type="button" id="btnSendFeedbackEmail" style="background: #e5e7eb; color: #111827; padding: 12px 16px; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 14px;">
                    Send via Email
                  </button>
                </div>
              </form>
              
              <div id="feedbackSuccess" style="display: none; text-align: center; padding: 20px;">
                <div style="font-size: 48px; margin-bottom: 10px;">✅</div>
                <h3 style="color: #10b981; margin-bottom: 10px;">Thank you!</h3>
                <p style="color: #666;">Your feedback has been sent successfully.</p>
              </div>

              <div id="feedbackError" style="display:none; margin-top: 10px; padding: 12px; border-radius: 8px; background: #fee2e2; color:#7f1d1d; font-size: 13px; line-height: 1.5;"></div>
            </div>
          </div>
        `;
        }
        
        document.body.appendChild(modal);
        
        // Close on overlay click
        modal.querySelector('.share-modal-overlay').addEventListener('click', () => {
          modal.remove();
        });
        
        // If showing rating modal, add star interaction logic
        if (showRatingFirst) {
          const stars = modal.querySelectorAll('.star');
          const ratingStep = modal.querySelector('#ratingStep');
          const testimonialStep = modal.querySelector('#testimonialStep');
          const improvementStep = modal.querySelector('#improvementStep');
          
          let selectedRating = 0;
          
          // Star hover and click effects
          stars.forEach((star, index) => {
            star.addEventListener('mouseenter', () => {
              stars.forEach((s, i) => {
                s.textContent = i <= index ? '★' : '☆';
              });
            });
            
            star.addEventListener('click', () => {
              selectedRating = index + 1;
              localStorage.setItem('userHasRated', 'true');
              
              // Display selected rating
              const displayStars = '★'.repeat(selectedRating) + '☆'.repeat(5 - selectedRating);
              
              ratingStep.style.display = 'none';
              
              if (selectedRating >= 4) {
                // High rating - ask for testimonial
                modal.querySelector('#ratingValue').value = selectedRating;
                modal.querySelector('#ratingDisplay').textContent = displayStars;
                testimonialStep.style.display = 'block';
              } else {
                // Low rating - ask for improvement suggestions
                modal.querySelector('#improvementRatingValue').value = selectedRating;
                modal.querySelector('#improvementRatingDisplay').textContent = displayStars;
                improvementStep.style.display = 'block';
              }
            });
          });
          
          // Reset stars on mouse leave
          modal.querySelector('.star-rating').addEventListener('mouseleave', () => {
            if (selectedRating === 0) {
              stars.forEach(s => s.textContent = '☆');
            }
          });
          
          // Handle testimonial form submission
          const testimonialForm = modal.querySelector('#testimonialForm');
          if (testimonialForm) {
            testimonialForm.addEventListener('submit', async (e) => {
              e.preventDefault();
              const formData = new FormData(testimonialForm);
              
              try {
                const response = await fetch(testimonialForm.action, {
                  method: 'POST',
                  body: formData,
                  headers: { 'Accept': 'application/json' }
                });
                
                if (response.ok) {
                  testimonialStep.style.display = 'none';
                  modal.querySelector('#feedbackSuccess').style.display = 'block';
                  setTimeout(() => modal.remove(), 3000);
                } else {
                  alert('Failed to submit testimonial. Please try again.');
                }
              } catch (error) {
                alert('Failed to submit. Please check your internet connection.');
              }
            });
          }
          
          // Handle improvement form submission
          const improvementForm = modal.querySelector('#improvementForm');
          if (improvementForm) {
            improvementForm.addEventListener('submit', async (e) => {
              e.preventDefault();
              const formData = new FormData(improvementForm);
              
              try {
                const response = await fetch(improvementForm.action, {
                  method: 'POST',
                  body: formData,
                  headers: { 'Accept': 'application/json' }
                });
                
                if (response.ok) {
                  improvementStep.style.display = 'none';
                  modal.querySelector('#feedbackSuccess').style.display = 'block';
                  setTimeout(() => modal.remove(), 3000);
                } else {
                  alert('Failed to send feedback. Please try again.');
                }
              } catch (error) {
                alert('Failed to send. Please check your internet connection.');
              }
            });
          }
        } else {
          // Normal feedback: submit to Formspree without opening a new tab.
          // We post to a hidden iframe and then show a success message in-app.
          const form = modal.querySelector('#feedbackForm');
          const submitBtn = modal.querySelector('#btnSendFeedback');
          const emailBtn = modal.querySelector('#btnSendFeedbackEmail');
          const bodyEl = modal.querySelector('.share-modal-body');
          const successEl = modal.querySelector('#feedbackSuccess');
          const errorEl = modal.querySelector('#feedbackError');

          if (form) {
            // Create a hidden iframe target for the form.
            const iframeName = `valido_feedback_iframe_${Date.now()}`;
            const iframe = document.createElement('iframe');
            iframe.name = iframeName;
            iframe.style.display = 'none';
            modal.appendChild(iframe);
            form.setAttribute('target', iframeName);

            let submitStartedAt = null;
            let fallbackTimer = null;

            form.addEventListener('submit', (e) => {
              // If honeypot is filled, silently stop (likely bot)
              const hp = form.querySelector('input[name="website"]');
              if (hp && hp.value && hp.value.trim().length > 0) {
                e.preventDefault();
                return;
              }

              submitStartedAt = Date.now();

              if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Sending...';
              }
              if (errorEl) {
                errorEl.style.display = 'none';
                errorEl.textContent = '';
              }

              // If we don't get a load event, still show a soft-success after a short delay.
              // (Some blockers prevent iframe load events even though form submits.)
              fallbackTimer = window.setTimeout(() => {
                if (successEl && form.style.display !== 'none') {
                  form.style.display = 'none';
                  if (successEl) successEl.style.display = 'block';
                  window.setTimeout(() => modal.remove(), 2500);
                }
              }, 1800);
            });

            iframe.addEventListener('load', () => {
              // Ignore the initial empty load.
              if (!submitStartedAt) return;
              // Avoid instant load noise; require a tiny delay after submit.
              if (Date.now() - submitStartedAt < 250) return;

              if (fallbackTimer) {
                window.clearTimeout(fallbackTimer);
                fallbackTimer = null;
              }

              // Success UI
              if (form) form.style.display = 'none';
              if (successEl) successEl.style.display = 'block';
              window.setTimeout(() => modal.remove(), 2500);
            });

            // Mailto fallback (works even when Formspree is blocked)
            if (emailBtn) {
              emailBtn.addEventListener('click', () => {
                const email = form?.querySelector('input[name="email"]')?.value?.trim() || '';
                const type = form?.querySelector('select[name="type"]')?.value || 'feedback';
                const message = form?.querySelector('textarea[name="message"]')?.value?.trim() || '';

                const body = [
                  message,
                  '',
                  '---',
                  `Type: ${type}`,
                  email ? `Reply-to (provided): ${email}` : 'Reply-to: (not provided)',
                  `Time: ${new Date().toISOString()}`,
                  `URL: ${(window.location && window.location.href) ? window.location.href : ''}`,
                  `User-Agent: ${navigator.userAgent}`
                ].join('\n');

                const subject = `Valido feedback (${type})`;
                window.open(`mailto:info@valido.site?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, '_blank');
              });
            }
          }
        }
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

      // FAANG-level UX: if exactly one PDF was uploaded, verify it's actually valid
      // BEFORE letting the user proceed.
      try {
        preflightSinglePdfIfNeeded(selectedFiles);
      } catch (e) {
        // ignore
      }
    }

    async function preflightSinglePdfIfNeeded(filesArr) {
      // Only gate the user when they upload a single PDF (Step 1 messaging).
      if (!Array.isArray(filesArr) || filesArr.length !== 1) {
        return;
      }

      const f = filesArr[0];
      if (!f || !f.name || !f.name.toLowerCase().endsWith('.pdf')) {
        return;
      }

      // Optimistic UI: keep continue enabled while we verify; if invalid we will block.
      const continueBtn = document.getElementById('continueToRules');
      if (continueBtn) {
        continueBtn.dataset.preflight = 'running';
      }

      const fd = new FormData();
      fd.append('file', f);

      try {
        const res = await fetch('/api/v1/upload', { method: 'POST', body: fd });
        if (!res.ok) {
          let payload = null;
          try { payload = await res.json(); } catch (e) { /* ignore */ }

          // Default human-friendly message
          let msg = 'This PDF cannot be processed. Please upload a digitally-generated PDF with selectable text.';
          let reason = null;

          // FastAPI may return { detail: { error, reason, message } }
          if (payload && payload.detail) {
            if (typeof payload.detail === 'string') {
              msg = payload.detail;
            } else if (payload.detail && typeof payload.detail === 'object') {
              reason = payload.detail.reason;
              msg = payload.detail.message || msg;
            }
          }

          // Block progression
          if (continueBtn) {
            continueBtn.disabled = true;
            continueBtn.classList.remove('btn-enabled');
            continueBtn.dataset.preflight = 'failed';
          }

          // Very clear user message
          if (window.toast && window.toast.error) {
            window.toast.error(msg);
          } else {
            alert(msg);
          }

          // Telemetry: invalid upload
          try {
            fetch('/api/v1/telemetry', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ action: 'step1_upload_invalid', details: { session_id: window.__validoSessionId, reason: reason || 'unknown' } })
            }).catch(() => {});
          } catch (e) {}

          return;
        }

        // Valid -> allow progress
        if (continueBtn) {
          continueBtn.disabled = false;
          if (selectedFiles.length > 0) continueBtn.classList.add('btn-enabled');
          continueBtn.dataset.preflight = 'ok';
        }
      } catch (e) {
        // Network/server down: don't block the user, but warn.
        if (continueBtn) {
          continueBtn.dataset.preflight = 'unknown';
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
        // Telemetry: user selected files (intent signal). Best-effort only.
        try {
          fetch('/api/v1/telemetry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              action: 'step1_files_selected',
              details: { session_id: window.__validoSessionId, count: (e.target.files || []).length }
            })
          }).catch(() => {});
        } catch (err) {
          // ignore
        }
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
        // Telemetry: user reached Step 2
        try {
          fetch('/api/v1/telemetry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'step2_enter', details: { session_id: window.__validoSessionId } })
          }).catch(() => {});
        } catch (e) {
          // ignore
        }
        navigateToStep(2);
      }
    });
    
    continueToValidate && continueToValidate.addEventListener('click', () => {
      // Force rules preview update to ensure latest rules are in dataset
      if (window.buildRulesPreview) {
        window.buildRulesPreview();
      }
      updateSummary();

      // Telemetry: user reached Step 3
      try {
        fetch('/api/v1/telemetry', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'step3_enter', details: { session_id: window.__validoSessionId } })
        }).catch(() => {});
      } catch (e) {
        // ignore
      }
      navigateToStep(3);
    });
    
    backToFiles && backToFiles.addEventListener('click', () => {
      navigateToStep(1);
    });
    
    backToRules && backToRules.addEventListener('click', () => {
      navigateToStep(2);
    });

    // Guided onboarding tour is started after the user dismisses the Quick Start modal
    // (see closeFirstRunGuide), so we don't stack UI elements.
    
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

    // --- Telemetry (privacy-first, best-effort) ---
    // This app works offline; telemetry must never block or be required.
    // session_id is per-tab/session and contains no PII.
    if (!window.__validoSessionId) {
      try {
        window.__validoSessionId = `s_${Date.now()}_${Math.random().toString(16).slice(2)}`;
      } catch (e) {
        window.__validoSessionId = null;
      }
    }

    // Step 1 impression: distinguishes "app opened" vs "user actually saw Step 1".
    try {
      fetch('/api/v1/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'step1_enter', details: { session_id: window.__validoSessionId } })
      }).catch(() => {});
    } catch (e) {
      // ignore
    }
    
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

        // If the user just resolved an ambiguity in the PDF viewer but didn't save a ruleset yet,
        // apply that choice to the current one-off run by injecting selectionTarget into rules.
        // (This keeps the behavior deterministic for the immediate validation result.)
        try {
          if (rules) {
            const rulesObj = typeof rules === 'string' ? JSON.parse(rules) : rules;

            // If the user just resolved an ambiguity in the PDF viewer but didn't persist it yet,
            // apply it to this submission.
            if (window.pendingSelectionTarget && rulesObj && Array.isArray(rulesObj.fields) && rulesObj.fields.length > 0) {
              const pending = window.pendingSelectionTarget;

              // Best-effort: apply to the most recently created/edited field (last field).
              const last = rulesObj.fields[rulesObj.fields.length - 1];
              if (last && typeof last === 'object') {
                last.selectionTarget = pending;
              }

              // Clear after consumption to avoid leaking into future submissions
              window.pendingSelectionTarget = null;
            }

            rules = JSON.stringify(rulesObj);
            console.log('📤 Submitting rules JSON (truncated):', rules.slice(0, 500));
          }
        } catch (e) {
          // Never block submission
          console.warn('Could not normalize/apply selectionTarget to rules:', e);
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
      // Mark run complete to prevent accidental resubmits
      if (window._validoSubmissionState) window._validoSubmissionState.completed = true;
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

  // Check for partial processing (limit reached OR invalid files)
  const resultInfo = (taskResult && taskResult.info) || {};
  const status = resultInfo.status || 'completed';
  const message = resultInfo.message;
  const filesSkipped = resultInfo.files_skipped || 0;
  const filesSucceeded = resultInfo.files_succeeded || 0;
  const totalFiles = resultInfo.total || 0;
  const filesFailed = resultInfo.files_failed || 0;
      
      let titleText, messageText, isPartial = false;
      
      if ((status === 'partial' && filesSkipped > 0) || filesFailed > 0) {
        // Partial processing due to limit OR invalid/corrupt files.
        isPartial = true;
        titleText = 'Processing Complete (with warnings)';
        if (filesFailed > 0) {
          messageText = `Processed ${filesSucceeded} of ${totalFiles} documents. ${filesFailed} file(s) were invalid/corrupted or image-only and were skipped.`;
        } else {
          messageText = message || `Processed ${filesSucceeded} of ${totalFiles} files. ${filesSkipped} files skipped due to free tier limit.`;
        }
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
          // Always tell the user where to see the detailed reasons
          successMessageEl.innerHTML += `<br><br><span style="color:#334155;">Download the results to see a detailed list of skipped files and human-friendly reasons.</span>`;
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
              <a href="${zipFromResult}" download class="btn btn-primary btn-large download-btn" onclick="localStorage.setItem('validationCompleted', 'true');">
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
              <a href="${zipFromResult}" download class="btn btn-primary btn-large download-btn" onclick="localStorage.setItem('validationCompleted', 'true');">
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
      // Ensure user can retry without refreshing
      if (window._validoSubmissionState) window._validoSubmissionState.completed = false;
      processingStatus.style.display = 'none';
      errorStatus.style.display = 'flex';

      // Actionable error guidance (reduces "black box" feeling)
      const safeMsg = (message || 'Validation failed. Please try again.').toString();
      errorMessage.innerHTML = `
        <div style="margin-bottom: 10px;">${escapeHtml(safeMsg)}</div>
        <div style="margin-top: 10px; padding: 12px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; color: #7c2d12;">
          <div style="font-weight: 600; margin-bottom: 6px;">Try this next:</div>
          <ul style="margin: 0; padding-left: 18px; line-height: 1.6;">
            <li><strong>Scanned PDF?</strong> Try selecting and copying text in your PDF viewer. If you can't select words, it won't work.</li>
            <li><strong>Field not found?</strong> Copy/paste the label text directly from the PDF (watch for spaces and punctuation).</li>
            <li><strong>Wrong value?</strong> Use a more specific label or change strategy (First/Last/All).</li>
          </ul>
          <div style="margin-top: 10px;">
            <button type="button" class="btn btn-secondary" id="openTroubleshootingBtn" style="padding: 0.6rem 1rem;">
              Open Troubleshooting
            </button>
          </div>
        </div>
      `;

      // Wire the button (safe if missing)
      const openTroubleshootingBtn = document.getElementById('openTroubleshootingBtn');
      if (openTroubleshootingBtn) {
        openTroubleshootingBtn.onclick = () => {
          const navHowTo = document.getElementById('navHowTo');
          const tabBtn = document.querySelector('.howto-tab[data-tab="troubleshooting"]');
          if (navHowTo) navHowTo.click();
          // Switch to troubleshooting tab
          if (tabBtn) tabBtn.click();
        };
      }
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

    // First-run guidance modal (defined in index.html)
    const firstRunGuideModal = document.getElementById('firstRunGuideModal');
    const firstRunGuideClose = document.getElementById('firstRunGuideClose');
    const firstRunGuideGotIt = document.getElementById('firstRunGuideGotIt');
    const firstRunGuideOverlay = document.getElementById('firstRunGuideOverlay');

    function showFirstRunGuideOnce() {
      try {
        if (!firstRunGuideModal) return;
        const key = 'valido:firstRunGuideShown';
        if (localStorage.getItem(key) === '1') return;
        localStorage.setItem(key, '1');
        firstRunGuideModal.style.display = 'flex';
      } catch (e) {
        // If storage is blocked, we still don't want to fail the app.
        if (firstRunGuideModal) firstRunGuideModal.style.display = 'flex';
      }
    }

    function closeFirstRunGuide() {
      if (!firstRunGuideModal) return;
      firstRunGuideModal.style.display = 'none';

      // Start the guided tour - now passive/observational with post-tour CTA
      try {
        if (window.ValidoTour && typeof window.ValidoTour.maybeStart === 'function') {
          window.ValidoTour.maybeStart([
            {
              selector: '#uploadArea',
              title: 'Step 1: Upload 1 PDF',
              body: 'Start with a single PDF so you can see results quickly. Click "Next" when ready.',
              placement: 'bottom'
            },
            {
              selector: '#continueToRules',
              title: 'Step 2: Continue to Rules',
              body: 'After uploading, click this button to choose what to validate/extract.',
              placement: 'top'
            },
            {
              getTarget: () => document.querySelector('[data-step="2"]') || document.querySelector('.step[data-step="2"]'),
              title: 'Step 3: Pick Validation Rules',
              body: 'Choose checks like signature verification, date validation, or text extraction.',
              placement: 'bottom'
            },
            {
              selector: '#continueToValidate',
              title: 'Step 3: Validate',
              body: 'When you’re ready, continue to Step 3 and run the validation.',
              placement: 'top',
              advanceOn: { event: 'click' }
            },
            {
              selector: '#submitBtn',
              title: 'Step 5: Run Validation',
              body: 'Click to validate and generate your report. That\'s it!',
              placement: 'top'
            }
          ], { key: 'valido.tour.upload.validate.v2', startDelayMs: 250, onComplete: showPostTourCTA });
        }
      } catch (e) {
        console.debug('[tour] failed to start after Quick Start modal', e);
      }
    }

    function showPostTourCTA() {
      const uploadArea = document.getElementById('uploadArea');
      if (!uploadArea) return;

      fetch('/api/v1/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'tour_complete_cta_shown', details: { source: 'post_tour_cta' } })
      }).catch(() => {});

      const ctaOverlay = document.createElement('div');
      ctaOverlay.id = 'postTourCTA';
      ctaOverlay.style.cssText = `position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.7); z-index: 9999; display: flex; align-items: center; justify-content: center; animation: fadeIn 0.3s ease-out;`;

      ctaOverlay.innerHTML = `<div style="background: white; border-radius: 16px; padding: 40px; max-width: 500px; text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.3); animation: slideUp 0.4s ease-out;"><div style="font-size: 48px; margin-bottom: 16px;">🎉</div><h2 style="margin: 0 0 16px 0; color: #1a1a1a; font-size: 24px;">Tour Complete!</h2><p style="margin: 0 0 32px 0; color: #666; font-size: 16px; line-height: 1.6;">Ready to validate your first PDF?<br>Click below to upload and get started.</p><button id="postTourCTABtn" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 16px 48px; font-size: 18px; font-weight: 600; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4); transition: transform 0.2s, box-shadow 0.2s;">Upload My First PDF</button></div>`;

      if (!document.getElementById('postTourCTAStyle')) {
        const style = document.createElement('style');
        style.id = 'postTourCTAStyle';
        style.textContent = `@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } } @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } } #postTourCTABtn:hover { transform: translateY(-2px); box-shadow: 0 6px 25px rgba(102, 126, 234, 0.5); }`;
        document.head.appendChild(style);
      }

      document.body.appendChild(ctaOverlay);

      document.getElementById('postTourCTABtn').addEventListener('click', () => {
        fetch('/api/v1/telemetry', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'post_tour_cta_clicked', details: { source: 'post_tour_cta' } }) }).catch(() => {});
        ctaOverlay.remove();
        uploadArea.click();
      });

      ctaOverlay.addEventListener('click', (e) => {
        if (e.target === ctaOverlay) {
          fetch('/api/v1/telemetry', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'post_tour_cta_dismissed', details: { source: 'post_tour_cta' } }) }).catch(() => {});
          ctaOverlay.remove();
        }
      });

      setTimeout(() => { if (document.getElementById('postTourCTA')) ctaOverlay.remove(); }, 15000);
    }

  if (firstRunGuideClose) firstRunGuideClose.addEventListener('click', closeFirstRunGuide);
  if (firstRunGuideGotIt) firstRunGuideGotIt.addEventListener('click', closeFirstRunGuide);
  if (firstRunGuideOverlay) firstRunGuideOverlay.addEventListener('click', closeFirstRunGuide);

    if (navUpload && navAutomation && navHowTo && navFeatures && uploadSection && automationSection && howToSection && featuresSection) {
      // Overview tab (Features)
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
        // Stop automation polling
        if (window.stopAutomationPolling) window.stopAutomationPolling();
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

        // First-run guidance is most useful right here
        showFirstRunGuideOnce();
        // Stop automation polling
        if (window.stopAutomationPolling) window.stopAutomationPolling();
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
        // Load automation jobs using automation.js
        if (typeof loadWatchFolders === 'function') {
          loadWatchFolders();
        }
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
        // Stop automation polling
        if (window.stopAutomationPolling) window.stopAutomationPolling();
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

      // Set default view to Upload & Validate (straight to value)
      featuresSection.style.display = 'none';
      uploadSection.style.display = 'block';
      automationSection.style.display = 'none';
      howToSection.style.display = 'none';
      pricingSection.style.display = 'none';
      navUpload.classList.add('active');
      navFeatures.classList.remove('active');
      navAutomation.classList.remove('active');
      navHowTo.classList.remove('active');

      // Show first-run guide when landing directly in Upload
      showFirstRunGuideOnce();
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
