/**
 * Job Runner Module
 * Handles running jobs and tracking progress
 */

export class JobRunner {
    constructor(jobListManager) {
        this.jobListManager = jobListManager;
        this.pollingIntervals = new Map();
    }

    /**
     * Run a job immediately
     */
    async runNow(jobId) {
        try {
            // Get job details
            const job = this.jobListManager.jobs.find(j => j.id === jobId);
            if (!job) throw new Error('Job not found');

            console.log(`Running job ${jobId}: ${job.name}`);

            // Trigger job execution on backend
            const response = await fetch(`/api/v1/watch-folders/${jobId}/run`, {
                method: 'POST'
            });

            if (!response.ok) throw new Error('Failed to start job');

            const result = await response.json();
            const taskId = result.task_id;

            console.log(`Job started, task ID: ${taskId}`);

            // Start polling for progress
            this.startPolling(jobId, taskId);

        } catch (error) {
            console.error('Failed to run job:', error);
            window.toast.error('Failed to start job: ' + error.message);
        }
    }

    /**
     * Start polling for task progress
     */
    startPolling(jobId, taskId) {
        // Stop any existing polling for this job
        this.stopPolling(jobId);

        // Initialize progress tracker
        this.jobListManager.activeTaskPollers.set(jobId, {
            taskId: taskId,
            progress: { processed: 0, total: 0, percent: 0, currentFile: '' }
        });

        // Re-render to show progress UI
        this.jobListManager.render();

        // Poll every 1.5 seconds
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/api/v1/watch-folders/tasks/${taskId}`);
                if (!response.ok) throw new Error('Failed to get task status');

                const taskStatus = await response.json();
                
                console.log('Task status:', taskStatus); // Debug log

                // Update progress
                if (taskStatus.status === 'PROGRESS' && taskStatus.result) {
                    const tracker = this.jobListManager.activeTaskPollers.get(jobId);
                    if (tracker) {
                        tracker.progress = {
                            processed: taskStatus.result.processed || 0,
                            total: taskStatus.result.total || 0,
                            percent: Math.min(95, ((taskStatus.result.processed || 0) / (taskStatus.result.total || 1)) * 100),
                            currentFile: taskStatus.result.current_file || ''
                        };
                        
                        // Re-render just this job card
                        this.updateJobCard(jobId);
                    }
                }

                // Task completed
                if (taskStatus.status === 'SUCCESS' || taskStatus.status === 'FAILURE' || taskStatus.status === 'REVOKED') {
                    console.log(`Task ${taskId} completed with status: ${taskStatus.status}`);
                    this.stopPolling(jobId);
                    
                    // Show completion message
                    if (taskStatus.status === 'SUCCESS') {
                        const total = taskStatus.result?.total || taskStatus.result?.reports?.length || 0;
                        window.toast.success(`Job completed successfully! Processed ${total} files.`);
                    } else if (taskStatus.status === 'FAILURE') {
                        window.toast.error(`Job failed: ${taskStatus.error || 'Check logs for details'}`);
                    } else {
                        window.toast.warning('Job was cancelled');
                    }

                    // Re-render to remove progress UI
                    this.jobListManager.render();
                    
                    // Auto-refresh job runs after completion
                    setTimeout(() => {
                        if (window.jobManager && window.jobManager.loadJobRuns) {
                            window.jobManager.loadJobRuns(jobId);
                        }
                    }, 1000);
                }

            } catch (error) {
                console.error('Error polling task:', error);
                this.stopPolling(jobId);
                this.jobListManager.render();
            }
        }, 1500);

        this.pollingIntervals.set(jobId, intervalId);
    }

    /**
     * Stop polling for a job
     */
    stopPolling(jobId) {
        const intervalId = this.pollingIntervals.get(jobId);
        if (intervalId) {
            clearInterval(intervalId);
            this.pollingIntervals.delete(jobId);
        }

        this.jobListManager.activeTaskPollers.delete(jobId);
    }

    /**
     * Stop a running job
     */
    async stopJob(jobId) {
        const tracker = this.jobListManager.activeTaskPollers.get(jobId);
        if (!tracker) return;

        window.toast.confirm('Are you sure you want to stop this job?', async () => {
            try {
                // Cancel the task on backend
                const response = await fetch(`/api/v1/watch-folders/tasks/${tracker.taskId}/cancel`, {
                    method: 'POST'
                });

                if (!response.ok) throw new Error('Failed to cancel task');

                this.stopPolling(jobId);
                this.jobListManager.render();
                
                window.toast.success('Job stopped successfully');

            } catch (error) {
                console.error('Failed to stop job:', error);
                window.toast.error('Failed to stop job: ' + error.message);
            }
        });
    }

    /**
     * Update a single job card without full re-render
     */
    updateJobCard(jobId) {
        const job = this.jobListManager.jobs.find(j => j.id === jobId);
        if (!job) return;

        const cardEl = document.querySelector(`.job-card[data-job-id="${jobId}"]`);
        if (!cardEl) return;

        const newHtml = this.jobListManager.renderJobCard(job);
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = newHtml;
        const newCard = tempDiv.firstChild;

        cardEl.replaceWith(newCard);
    }
}
