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

    async loadJobRuns(jobId) {
        console.log('=== loadJobRuns called for jobId:', jobId);
        const container = document.getElementById(`jobRuns_${jobId}`);
        console.log('Container element:', container ? 'FOUND' : 'NOT FOUND');
        if (!container) return;
        
        container.innerHTML = '<div style="text-align: center; color: #999; padding: 1rem;"><small>Loading...</small></div>';
        
        try {
            console.log('Fetching job runs from API...');
            const response = await fetch(`/api/v1/watch-folders/${jobId}/runs`);
            const runs = await response.json();
            console.log('Received runs:', runs.length, 'total');
            
            if (!runs || runs.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #999; padding: 1rem;"><small>No executions yet</small></div>';
                return;
            }
            
            // Show only last 3 executions
            const recentRuns = runs.slice(0, 3);
            console.log('Showing', recentRuns.length, 'recent runs (limited to 3)');
            
            container.innerHTML = recentRuns.map(run => {
                const statusColors = {
                    'running': { bg: '#fff3cd', color: '#856404', icon: '⏳' },
                    'success': { bg: '#d4edda', color: '#155724', icon: '✓' },
                    'failed': { bg: '#f8d7da', color: '#721c24', icon: '✗' },
                    'partial': { bg: '#ffeaa7', color: '#856404', icon: '⚠' }
                };
                const style = statusColors[run.status] || statusColors['running'];
                const duration = run.completed_at ? 
                    Math.round((new Date(run.completed_at) - new Date(run.started_at)) / 1000) + 's' :
                    'In progress...';
                
                return `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; margin-bottom: 0.5rem; background: ${style.bg}; border-left: 3px solid ${style.color}; border-radius: 4px;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                                <span style="font-size: 1.2em;">${style.icon}</span>
                                <span style="font-weight: 600; color: ${style.color};">${run.status.toUpperCase()}</span>
                                <span style="color: #666; font-size: 0.875em;">${new Date(run.started_at).toLocaleString()}</span>
                            </div>
                            <div style="font-size: 0.875em; color: #666; margin-bottom: 0.25rem;">
                                ${run.files_found} files found, ${run.files_succeeded} succeeded, ${run.files_failed} failed
                                ${run.error_message ? `<br><span style="color: ${style.color};">Error: ${run.error_message}</span>` : ''}
                            </div>
                            ${run.pc_name || run.output_path ? `
                                <div style="font-size: 0.75em; color: #888; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid rgba(0,0,0,0.1);">
                                    ${run.pc_name ? `<div><strong>PC:</strong> ${run.pc_name}</div>` : ''}
                                    ${run.output_path ? `<div><strong>Results:</strong> ${run.output_path}</div>` : ''}
                                </div>
                            ` : ''}
                        </div>
                        <div style="text-align: right; color: #666; font-size: 0.875em;">
                            ${duration}
                        </div>
                    </div>
                `;
            }).join('');
        } catch (error) {
            console.error('Failed to load job runs:', error);
            container.innerHTML = '<div style="text-align: center; color: #dc3545; padding: 1rem;"><small>Failed to load execution history</small></div>';
        }
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

// Browse folder function (called by inline onclick in HTML)
async function browseFolder(inputId) {
    console.log('browseFolder called with inputId:', inputId);
    
    // Show helpful message since browser can't return full path
    const input = document.getElementById(inputId);
    if (!input) return;
    
    alert('Browser Security Limitation:\n\n' +
          'For security reasons, browsers cannot provide the full folder path.\n\n' +
          'Please manually type or paste the full path:\n' +
          '• Local: C:\\MyFolder\\Invoices\n' +
          '• Network: \\\\SERVER\\Share\\Invoices\n\n' +
          'Tip: Open File Explorer, navigate to the folder, and copy the path from the address bar.');
    
    // Focus the input so user can paste
    input.focus();
}

// Make browseFolder available globally
window.browseFolder = browseFolder;
console.log('browseFolder function exposed to window:', typeof window.browseFolder);
