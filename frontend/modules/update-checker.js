// Update Checker Module
const UpdateChecker = {
  GITHUB_API: 'https://api.github.com/repos/abhishekrai43/valido/releases/latest',
  CURRENT_VERSION: '1.0.8',
  
  async checkForUpdates() {
    try {
      const response = await fetch(this.GITHUB_API);
      if (!response.ok) {
        throw new Error('Failed to fetch release info');
      }
      
      const release = await response.json();
      const latestVersion = release.tag_name.replace('v', '');
      
      if (this.isNewerVersion(latestVersion, this.CURRENT_VERSION)) {
        this.showUpdateModal(latestVersion, release.body, release.html_url);
      } else {
        this.showNoUpdateModal();
      }
    } catch (error) {
      console.error('Update check failed:', error);
      Toast.show('Failed to check for updates', 'error');
    }
  },
  
  isNewerVersion(latest, current) {
    const latestParts = latest.split('.').map(Number);
    const currentParts = current.split('.').map(Number);
    
    for (let i = 0; i < 3; i++) {
      if (latestParts[i] > currentParts[i]) return true;
      if (latestParts[i] < currentParts[i]) return false;
    }
    return false;
  },
  
  showUpdateModal(version, changelog, downloadUrl) {
    const modal = document.createElement('div');
    modal.className = 'update-modal';
    modal.innerHTML = `
      <div class="modal-overlay" onclick="this.closest('.update-modal').remove()"></div>
      <div class="modal-content" style="max-width: 600px;">
        <div class="modal-header">
          <h3>New Version Available</h3>
          <button class="modal-close" onclick="this.closest('.update-modal').remove()">×</button>
        </div>
        <div class="modal-body">
          <div style="background: linear-gradient(135deg, #0066ff 0%, #0052cc 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center;">
            <div style="font-size: 0.875rem; opacity: 0.9; margin-bottom: 8px;">Current: v${this.CURRENT_VERSION}</div>
            <div style="font-size: 2rem; font-weight: 700;">v${version}</div>
            <div style="font-size: 0.875rem; opacity: 0.9; margin-top: 8px;">Latest Release</div>
          </div>
          
          <h4 style="margin: 20px 0 10px; color: #1f2937;">What's New</h4>
          <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; max-height: 200px; overflow-y: auto;">
            <pre style="white-space: pre-wrap; margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 0.875rem; line-height: 1.6;">${changelog}</pre>
          </div>
          
          <button class="btn btn-primary" style="width: 100%;" onclick="window.open('${downloadUrl}', '_blank'); this.closest('.update-modal').remove();">
            Download v${version}
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  },
  
  showNoUpdateModal() {
    const modal = document.createElement('div');
    modal.className = 'update-modal';
    modal.innerHTML = `
      <div class="modal-overlay" onclick="this.closest('.update-modal').remove()"></div>
      <div class="modal-content" style="max-width: 400px;">
        <div class="modal-header">
          <h3>You're Up to Date</h3>
          <button class="modal-close" onclick="this.closest('.update-modal').remove()">×</button>
        </div>
        <div class="modal-body">
          <div style="text-align: center; padding: 20px;">
            <div style="font-size: 3rem; margin-bottom: 15px;">✓</div>
            <div style="font-size: 1.125rem; font-weight: 600; color: #1f2937; margin-bottom: 8px;">
              You have the latest version
            </div>
            <div style="color: #6b7280;">
              v${this.CURRENT_VERSION}
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }
};
