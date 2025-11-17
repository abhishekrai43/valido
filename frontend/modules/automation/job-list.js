/**
 * Job List Module
 * Handles rendering and managing the list of automation jobs
 */

export class JobListManager {
    constructor() {
        this.jobs = [];
        this.activeTaskPollers = new Map(); // Track active polling for each job
    }

    /**
     * Load jobs from API
     */
    async loadJobs() {
        try {
            const response = await fetch('/api/v1/watch-folders/');
            if (!response.ok) throw new Error('Failed to load jobs');
            this.jobs = await response.json();
            this.render();
        } catch (error) {
            console.error('Failed to load jobs:', error);
            this.showError('Failed to load automation jobs');
        }
    }

    /**
     * Render jobs list
     */
    render() {
        const loadingEl = document.getElementById('jobsListLoading');
        const emptyEl = document.getElementById('jobsListEmpty');
        const listEl = document.getElementById('jobsList');
        
        if (loadingEl) loadingEl.style.display = 'none';
        
        if (this.jobs.length === 0) {
            if (emptyEl) emptyEl.style.display = 'block';
            if (listEl) listEl.style.display = 'none';
            return;
        }
        
        if (emptyEl) emptyEl.style.display = 'none';
        if (listEl) {
            listEl.style.display = 'block';
            listEl.innerHTML = this.jobs.map(job => this.renderJobCard(job)).join('');
            
            // Auto-load job runs AFTER HTML is rendered
            setTimeout(() => {
                this.jobs.forEach(job => {
                    if (window.jobManager && window.jobManager.loadJobRuns) {
                        window.jobManager.loadJobRuns(job.id);
                    } else {
                        console.error('jobManager or loadJobRuns not available!');
                    }
                });
            }, 100);
        }
    }

    /**
     * Render a single job card with progress tracking
     */
    renderJobCard(job) {
        const isRunning = this.activeTaskPollers.has(job.id);
        const progress = isRunning ? this.activeTaskPollers.get(job.id).progress : null;

        return `
            <div class="job-card" data-job-id="${job.id}">
                <div class="job-header">
                    <div class="job-info">
                        <h4>${this.escapeHtml(job.name)}</h4>
                        <span class="job-status ${job.enabled ? 'active' : 'inactive'}">
                            <span class="status-dot"></span>
                            ${job.enabled ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div class="job-actions">
                        ${isRunning ? 
                            `<button class="btn-icon btn-danger" onclick="window.jobManager.stopJob(${job.id})" title="Stop">
                                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                    <rect x="5" y="5" width="10" height="10" fill="currentColor"/>
                                </svg>
                            </button>` :
                            `<button class="btn-icon" onclick="window.jobManager.runNow(${job.id})" title="Run Now">
                                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                    <path d="M6 4L16 10L6 16V4Z" fill="currentColor"/>
                                </svg>
                            </button>`
                        }
                        <button class="btn-icon" onclick="window.jobManager.toggleJob(${job.id})" title="${job.enabled ? 'Disable' : 'Enable'}">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                ${job.enabled ? 
                                    '<path d="M4 10L8 14L16 6" stroke="currentColor" stroke-width="2"/>' :
                                    '<circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="2"/>'}
                            </svg>
                        </button>
                        <button class="btn-icon" onclick="window.jobManager.editJob(${job.id})" title="Edit">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                <path d="M14 2L18 6L7 17H3V13L14 2Z" stroke="currentColor" stroke-width="2"/>
                            </svg>
                        </button>
                        <button class="btn-icon btn-danger" onclick="window.jobManager.deleteJob(${job.id})" title="Delete">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                <path d="M3 5H17M8 9V15M12 9V15M4 5L5 17C5 18 6 19 7 19H13C14 19 15 18 15 17L16 5" stroke="currentColor" stroke-width="2"/>
                            </svg>
                        </button>
                    </div>
                </div>

                <div class="job-details">
                    <div class="job-detail-item">
                        <span class="label">Input:</span>
                        <span class="value">${this.escapeHtml(job.input_path)}</span>
                    </div>
                    <div class="job-detail-item">
                        <span class="label">Output:</span>
                        <span class="value">${this.escapeHtml(job.output_path)}</span>
                    </div>
                    <div class="job-detail-item">
                        <span class="label">Schedule:</span>
                        <span class="value">${this.formatSchedule(job.schedule_times)}</span>
                    </div>
                </div>

                ${isRunning && progress ? `
                    <div class="job-progress">
                        <div class="progress-header">
                            <span>Processing ${progress.processed} of ${progress.total} files...</span>
                            <span>${Math.round(progress.percent)}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progress.percent}%"></div>
                        </div>
                        ${progress.currentFile ? `
                            <div class="current-file">
                                Current: ${this.escapeHtml(progress.currentFile)}
                            </div>
                        ` : ''}
                    </div>
                ` : ''}

                <!-- Execution History Section -->
                <div class="execution-history" style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                        <h5 style="margin: 0; font-size: 1em; color: #666;">Recent Executions</h5>
                        <button onclick="window.jobManager.loadJobRuns(${job.id})" style="padding: 0.25rem 0.75rem; font-size: 0.875em; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; color: #0066cc;">
                            Refresh
                        </button>
                    </div>
                    <div id="jobRuns_${job.id}" style="min-height: 50px;">
                        <div style="text-align: center; color: #999; padding: 1rem;">
                            <small>Loading execution history...</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Format schedule to human-readable
     */
    formatSchedule(times) {
        if (!times) return 'Not scheduled';
        // times is a comma-separated list like "18:00,12:00"
        if (typeof times === 'string') {
            const timeList = times.split(',').map(t => t.trim()).filter(t => t);
            if (timeList.length === 0) return 'Not scheduled';
            if (timeList.length === 1) return `Daily at ${timeList[0]}`;
            return `Daily at ${timeList.join(', ')}`;
        }
        return times;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error(message);
        // TODO: Show toast notification
    }
}
