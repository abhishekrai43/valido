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

            // Show progress bar IMMEDIATELY with "Starting..." message
            this.jobListManager.activeTaskPollers.set(jobId, {
                taskId: null, // Will be set after API response
                progress: { processed: 0, total: 0, percent: 0, currentFile: 'Starting job...' }
            });
            this.updateJobCard(jobId);

            // Trigger job execution on backend
            const response = await fetch(`/api/v1/watch-folders/${jobId}/run`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorText = await response.text();
                // Remove progress bar on error
                this.jobListManager.activeTaskPollers.delete(jobId);
                this.updateJobCard(jobId);
                throw new Error(errorText || 'Failed to start job');
            }

            const result = await response.json();
            const taskId = result.task_id;
            const filesCount = result.files_count || 0;

            if (!taskId) {
                // Remove progress bar on error
                this.jobListManager.activeTaskPollers.delete(jobId);
                this.updateJobCard(jobId);
                throw new Error('No task ID returned from server');
            }

            console.log(`Job ${jobId} started with task ID: ${taskId}, files: ${filesCount}`);

            // Update progress tracker with actual file count and start polling
            const tracker = this.jobListManager.activeTaskPollers.get(jobId);
            if (tracker) {
                tracker.taskId = taskId;
                tracker.progress = { processed: 0, total: filesCount, percent: 0, currentFile: 'Downloading files from cloud...' };
                this.updateJobCard(jobId);
            }

            // Start polling for progress
            this.startPolling(jobId, taskId, filesCount);

        } catch (error) {
            console.error('Failed to run job:', error);
            window.toast.error('Failed to start job: ' + error.message);
        }
    }

    /**
     * Start polling for task progress
     */
    startPolling(jobId, taskId, filesCount = 0) {
        // Stop any existing polling for this job
        this.stopPolling(jobId);

        console.log(`Starting progress polling for job ${jobId}, task ${taskId}, files: ${filesCount}`);

        // Progress tracker is already set in runNow(), just update it
        const tracker = this.jobListManager.activeTaskPollers.get(jobId);
        if (tracker) {
            tracker.taskId = taskId;
            tracker.progress.total = filesCount;
            tracker.progress.currentFile = 'Processing files...';
        }

        // Poll every 1.5 seconds
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/api/v1/watch-folders/tasks/${taskId}`);
                if (!response.ok) {
                    console.error(`Failed to get task status: ${response.status} ${response.statusText}`);
                    throw new Error('Failed to get task status');
                }

                const taskStatus = await response.json();
                console.log(`Task ${taskId} status:`, taskStatus.status, taskStatus.result);
                

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
                    
                    // Update progress tracker with completion status
                    const tracker = this.jobListManager.activeTaskPollers.get(jobId);
                    if (tracker && taskStatus.status === 'SUCCESS') {
                        const total = taskStatus.result?.total || tracker.progress.total;
                        tracker.progress = {
                            processed: total,
                            total: total,
                            percent: 100,
                            currentFile: `✅ Completed successfully! Processed ${total} files`
                        };
                        
                        // Update just this job card to show completion
                        this.updateJobCard(jobId);
                        
                        // Remove progress tracker after 3 seconds
                        setTimeout(() => {
                            this.jobListManager.activeTaskPollers.delete(jobId);
                            this.updateJobCard(jobId);
                            
                            // Refresh job runs to show new execution
                            if (window.jobManager && window.jobManager.loadJobRuns) {
                                window.jobManager.loadJobRuns(jobId);
                            }
                        }, 3000);
                    } else {
                        // For failures, just remove the progress tracker
                        this.jobListManager.activeTaskPollers.delete(jobId);
                        this.updateJobCard(jobId);
                        
                        // Still refresh job runs
                        if (window.jobManager && window.jobManager.loadJobRuns) {
                            window.jobManager.loadJobRuns(jobId);
                        }
                    }
                }

            } catch (error) {
                console.error('Error polling task:', error);
                this.stopPolling(jobId);
                this.jobListManager.activeTaskPollers.delete(jobId);
                this.updateJobCard(jobId);
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
