/**
 * Automation Manager - Main Orchestrator
 * Coordinates all automation modules
 */

import { JobListManager } from './job-list.js';
import { JobRunner } from './job-runner.js';
import { JobFormManager } from './job-form.js';
import { JobActionsManager } from './job-actions.js';

export class AutomationManager {
    constructor() {
        this.jobList = new JobListManager();
        this.jobRunner = new JobRunner(this.jobList);
        this.jobForm = new JobFormManager(this.jobList);
        this.jobActions = new JobActionsManager(this.jobList);
    }

    /**
     * Initialize automation page
     */
    async init() {
        console.log('Initializing automation manager...');
        
        await Promise.all([
            this.jobList.loadJobs(),
            this.jobForm.loadRulesets()
        ]);

        this.setupEventListeners();
        this.jobForm.clearForm();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Save job button
        const saveBtn = document.getElementById('btnSaveWatchFolder');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.jobForm.saveJob());
        }

        // Cancel button
        const cancelBtn = document.getElementById('btnCancelWatchFolder');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.jobForm.clearForm());
        }
    }

    /**
     * Public API methods - exposed to window for onclick handlers
     */
    runNow(jobId) {
        this.jobRunner.runNow(jobId);
    }

    stopJob(jobId) {
        this.jobRunner.stopJob(jobId);
    }

    toggleJob(jobId) {
        this.jobActions.toggleJob(jobId);
    }

    editJob(jobId) {
        this.jobForm.loadJobIntoForm(jobId);
    }

    deleteJob(jobId) {
        this.jobActions.deleteJob(jobId);
    }
}

// Global instance
window.jobManager = null;

// Initialize when automation section is shown
export function initAutomation() {
    if (!window.jobManager) {
        window.jobManager = new AutomationManager();
    }
    window.jobManager.init();
}

// Export for use in HTML
window.initAutomation = initAutomation;
