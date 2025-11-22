/**
 * Cloud Storage Modal Module
 * Modular component for selecting and configuring cloud storage providers
 * Handles Azure Blob Storage, AWS S3, and Google Cloud Storage
 */

class CloudStorageModal {
    constructor() {
        this.modal = null;
        this.providers = [];
        this.selectedProvider = null;
        this.onConfirm = null;
        this.init();
    }

    async init() {
        // Fetch supported providers from API
        try {
            const response = await fetch('/api/v1/cloud/providers');
            const data = await response.json();
            this.providers = data.providers || [];
        } catch (error) {
            console.error('Failed to fetch cloud providers:', error);
            this.providers = this.getDefaultProviders();
        }
    }

    getDefaultProviders() {
        // Fallback if API call fails
        return [
            {
                id: 'azure',
                name: 'Azure Blob Storage',
                icon: '/enterprise-icons/azure-icon.png',
                fields: [
                    { name: 'account_name', label: 'Account Name', type: 'text', required: true },
                    { name: 'account_key', label: 'Account Key / SAS Token', type: 'password', required: true },
                    { name: 'container_name', label: 'Container Name', type: 'text', required: true }
                ]
            },
            {
                id: 'aws',
                name: 'AWS S3',
                icon: '/enterprise-icons/aws-icon.png',
                fields: [
                    { name: 'access_key_id', label: 'Access Key ID', type: 'text', required: true },
                    { name: 'secret_access_key', label: 'Secret Access Key', type: 'password', required: true },
                    { name: 'bucket_name', label: 'Bucket Name', type: 'text', required: true },
                    { name: 'region', label: 'Region', type: 'text', required: false, default: 'us-east-1' }
                ]
            },
            {
                id: 'gcp',
                name: 'Google Cloud Storage',
                icon: '/enterprise-icons/gcp-icon.png',
                fields: [
                    { name: 'service_account_json', label: 'Service Account JSON', type: 'textarea', required: true },
                    { name: 'bucket_name', label: 'Bucket Name', type: 'text', required: true }
                ]
            }
        ];
    }

    show(callback) {
        this.onConfirm = callback;
        this.createModal();
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    hide() {
        if (this.modal) {
            this.modal.style.display = 'none';
            document.body.style.overflow = '';
            this.modal.remove();
            this.modal = null;
        }
    }

    createModal() {
        // Create modal container
        this.modal = document.createElement('div');
        this.modal.className = 'cloud-storage-modal-overlay';
        this.modal.innerHTML = `
            <div class="cloud-storage-modal-container">
                <div class="cloud-storage-modal-header">
                    <h2>☁️ Configure Cloud Storage</h2>
                    <button class="cloud-storage-close-btn" onclick="cloudStorageModal.hide()">×</button>
                </div>
                <div class="cloud-storage-modal-body">
                    <div class="cloud-provider-selection">
                        <h3>Select Cloud Provider</h3>
                        <div class="cloud-provider-grid" id="cloudProviderGrid"></div>
                    </div>
                    <div class="cloud-provider-config" id="cloudProviderConfig" style="display: none;">
                        <h3 id="configTitle">Configure Provider</h3>
                        <div id="configFields"></div>
                        <div class="cloud-actions">
                            <button class="btn-secondary" onclick="cloudStorageModal.showProviderSelection()">
                                ← Back to Providers
                            </button>
                            <button class="btn-test" id="testConnectionBtn" onclick="cloudStorageModal.testConnection()">
                                🔍 Test Connection
                            </button>
                            <button class="btn-primary" id="confirmCloudBtn" onclick="cloudStorageModal.confirmSelection()">
                                ✓ Use This Configuration
                            </button>
                        </div>
                        <div id="testResult" class="test-result" style="display: none;"></div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(this.modal);
        this.renderProviders();

        // Close on overlay click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
    }

    renderProviders() {
        const grid = document.getElementById('cloudProviderGrid');
        grid.innerHTML = this.providers.map(provider => `
            <div class="cloud-provider-card" onclick="cloudStorageModal.selectProvider('${provider.id}')">
                <img src="${provider.icon}" alt="${provider.name}" class="provider-icon">
                <h4>${provider.name}</h4>
            </div>
        `).join('');
    }

    selectProvider(providerId) {
        this.selectedProvider = this.providers.find(p => p.id === providerId);
        if (!this.selectedProvider) return;

        // Hide provider selection, show config form
        document.querySelector('.cloud-provider-selection').style.display = 'none';
        document.getElementById('cloudProviderConfig').style.display = 'block';
        document.getElementById('configTitle').textContent = `Configure ${this.selectedProvider.name}`;
        document.getElementById('testResult').style.display = 'none';

        // Render config fields
        this.renderConfigFields();
    }

    renderConfigFields() {
        const container = document.getElementById('configFields');
        container.innerHTML = this.selectedProvider.fields.map(field => {
            const required = field.required ? 'required' : '';
            const defaultValue = field.default || '';

            if (field.type === 'textarea') {
                return `
                    <div class="form-group">
                        <label for="cloud_${field.name}">
                            ${field.label}
                            ${field.required ? '<span class="required">*</span>' : ''}
                        </label>
                        <textarea 
                            id="cloud_${field.name}" 
                            name="${field.name}"
                            ${required}
                            placeholder="Paste your ${field.label} here"
                            rows="6"
                        ></textarea>
                    </div>
                `;
            } else {
                return `
                    <div class="form-group">
                        <label for="cloud_${field.name}">
                            ${field.label}
                            ${field.required ? '<span class="required">*</span>' : ''}
                        </label>
                        <input 
                            type="${field.type}" 
                            id="cloud_${field.name}" 
                            name="${field.name}"
                            value="${defaultValue}"
                            ${required}
                            placeholder="Enter ${field.label}"
                        />
                    </div>
                `;
            }
        }).join('');
    }

    showProviderSelection() {
        document.querySelector('.cloud-provider-selection').style.display = 'block';
        document.getElementById('cloudProviderConfig').style.display = 'none';
        this.selectedProvider = null;
    }

    getConfigValues() {
        const config = {};
        this.selectedProvider.fields.forEach(field => {
            const input = document.getElementById(`cloud_${field.name}`);
            config[field.name] = input.value.trim();
        });
        return config;
    }

    async testConnection() {
        const config = this.getConfigValues();
        const testBtn = document.getElementById('testConnectionBtn');
        const resultDiv = document.getElementById('testResult');

        // Validate required fields
        const missingFields = this.selectedProvider.fields
            .filter(f => f.required && !config[f.name])
            .map(f => f.label);

        if (missingFields.length > 0) {
            resultDiv.innerHTML = `<div class="test-error">❌ Missing required fields: ${missingFields.join(', ')}</div>`;
            resultDiv.style.display = 'block';
            return;
        }

        // Test connection
        testBtn.disabled = true;
        testBtn.textContent = '⏳ Testing...';
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '<div class="test-loading">Testing connection...</div>';

        try {
            const response = await fetch('/api/v1/cloud/test-connection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider: this.selectedProvider.id,
                    config: config
                })
            });

            const result = await response.json();

            if (result.success) {
                resultDiv.innerHTML = `<div class="test-success">✅ ${result.message}</div>`;
            } else {
                resultDiv.innerHTML = `<div class="test-error">❌ ${result.message}</div>`;
            }
        } catch (error) {
            resultDiv.innerHTML = `<div class="test-error">❌ Connection test failed: ${error.message}</div>`;
        } finally {
            testBtn.disabled = false;
            testBtn.textContent = '🔍 Test Connection';
        }
    }

    confirmSelection() {
        const config = this.getConfigValues();

        // Validate required fields
        const missingFields = this.selectedProvider.fields
            .filter(f => f.required && !config[f.name])
            .map(f => f.label);

        if (missingFields.length > 0) {
            alert(`Please fill in all required fields: ${missingFields.join(', ')}`);
            return;
        }

        // Call callback with provider and config
        if (this.onConfirm) {
            this.onConfirm({
                provider: this.selectedProvider.id,
                providerName: this.selectedProvider.name,
                config: config
            });
        }

        this.hide();
    }
}

// Initialize global instance
window.cloudStorageModal = new CloudStorageModal();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CloudStorageModal;
}
