/**
 * Job Form Module
 * Handles the watch folder configuration form
 */

export class JobFormManager {
    constructor(jobListManager) {
        this.jobListManager = jobListManager;
        this.editingJobId = null;
        this.rulesets = [];
    }

    /**
     * Load rulesets for dropdown
     */
    async loadRulesets() {
        try {
            const response = await fetch('/api/v1/rulesets/');
            if (!response.ok) throw new Error('Failed to load rulesets');
            this.rulesets = await response.json();
            this.renderRulesetsDropdown();
        } catch (error) {
            console.error('Failed to load rulesets:', error);
        }
    }

    /**
     * Render rulesets dropdown
     */
    renderRulesetsDropdown() {
        const select = document.getElementById('watchFolderRuleset');
        if (!select) return;

        select.innerHTML = '<option value="">Select a ruleset...</option>';
        this.rulesets.forEach(ruleset => {
            const option = document.createElement('option');
            option.value = ruleset.id;
            option.textContent = ruleset.name;
            select.appendChild(option);
        });
    }

    /**
     * Clear and reset form
     */
    clearForm() {
        this.editingJobId = null;
        
        const fields = [
            'watchFolderName',
            'watchFolderInput',
            'watchFolderOutput',
            'watchFolderRuleset'
        ];

        fields.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.value = '';
                // Clear cloud config data attributes
                if (id === 'watchFolderInput') {
                    if (el.dataset.cloudConfig) delete el.dataset.cloudConfig;
                    if (el.dataset.cloudPath) delete el.dataset.cloudPath;
                }
            }
        });
        
        // Leave output path empty - user will specify their own path
        const outputEl = document.getElementById('watchFolderOutput');
        if (outputEl) {
            outputEl.value = '';
        }

        const titleEl = document.getElementById('watchFolderFormTitle');
        if (titleEl) titleEl.textContent = 'Create New Automation Job';
    }

    /**
     * Load job data into form for editing
     */
    loadJobIntoForm(jobId) {
        const job = this.jobListManager.jobs.find(j => j.id === jobId);
        if (!job) return;

        this.editingJobId = jobId;

        const fields = {
            'watchFolderName': job.name,
            'watchFolderInput': job.input_path,
            'watchFolderOutput': job.output_path,
            'watchFolderRuleset': job.ruleset_id || ''
        };

        Object.entries(fields).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) el.value = value;
        });

        const titleEl = document.getElementById('watchFolderFormTitle');
        if (titleEl) titleEl.textContent = 'Edit Automation Job';

        // Scroll to form
        const formEl = document.querySelector('.watch-folder-form');
        if (formEl) formEl.scrollIntoView({ behavior: 'smooth' });
    }

    /**
     * Save job (create or update)
     */
    async saveJob() {
        // Collect schedule times from inputs
        const scheduleInputs = document.querySelectorAll('.schedule-time-input');
        const scheduleTimes = Array.from(scheduleInputs)
            .map(input => input.value.trim())
            .filter(time => time);
        
        const inputField = document.getElementById('watchFolderInput');
        let inputPath = inputField?.value.trim();
        
        // Check if cloud configuration is set
        let cloudConfig = null;
        if (inputField?.dataset.cloudConfig) {
            try {
                cloudConfig = JSON.parse(inputField.dataset.cloudConfig);
                // Use the actual cloud path for backend, not the display name
                inputPath = inputField.dataset.cloudPath || inputPath;
            } catch (e) {
                console.error('Failed to parse cloud config:', e);
            }
        }
        
        const formData = {
            name: document.getElementById('watchFolderName')?.value.trim(),
            input_path: inputPath,
            output_path: document.getElementById('watchFolderOutput')?.value.trim(),
            ruleset_id: parseInt(document.getElementById('watchFolderRuleset')?.value) || null,
            enabled: true,
            schedule_times: scheduleTimes.length > 0 ? scheduleTimes.join(',') : "18:00",
            move_processed: false,
            processed_path: null,
            delete_after: false,
            // Add cloud configuration if present
            cloud_config: cloudConfig
        };

        // Validation
        if (!formData.name) {
            window.toast.warning('Please enter a configuration name');
            return;
        }
        if (!formData.input_path) {
            window.toast.warning('Please enter an input folder path or configure cloud storage');
            return;
        }
        if (!formData.output_path) {
            window.toast.warning('Please enter an output folder path');
            return;
        }
        if (!formData.ruleset_id) {
            window.toast.warning('Please select a ruleset');
            return;
        }

        try {
            const url = this.editingJobId 
                ? `/api/v1/watch-folders/${this.editingJobId}`
                : '/api/v1/watch-folders/';
            
            const method = this.editingJobId ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                const error = await response.text();
                throw new Error(error);
            }

            window.toast.success(this.editingJobId ? 'Job updated successfully!' : 'Job created successfully!');
            
            this.clearForm();
            await this.jobListManager.loadJobs();

        } catch (error) {
            console.error('Failed to save job:', error);
            window.toast.error('Failed to save job: ' + error.message);
        }
    }
}
