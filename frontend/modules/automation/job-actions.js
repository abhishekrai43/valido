/**
 * Job Actions Module
 * Handles job operations (toggle, delete, etc.)
 */

export class JobActionsManager {
    constructor(jobListManager) {
        this.jobListManager = jobListManager;
    }

    /**
     * Toggle job enabled/disabled
     */
    async toggleJob(jobId) {
        const job = this.jobListManager.jobs.find(j => j.id === jobId);
        if (!job) return;

        try {
            const response = await fetch(`/api/v1/watch-folders/${jobId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...job, enabled: !job.enabled })
            });

            if (!response.ok) throw new Error('Failed to toggle job');

            job.enabled = !job.enabled;
            this.jobListManager.render();

        } catch (error) {
            console.error('Failed to toggle job:', error);
            window.toast.error('Failed to toggle job: ' + error.message);
        }
    }

    /**
     * Delete a job
     */
    async deleteJob(jobId) {
        const job = this.jobListManager.jobs.find(j => j.id === jobId);
        if (!job) return;

        window.toast.confirm(`Delete job "${job.name}"?`, async () => {
            try {
                const response = await fetch(`/api/v1/watch-folders/${jobId}`, {
                    method: 'DELETE'
                });

                if (!response.ok) throw new Error('Failed to delete job');

                window.toast.success('Job deleted successfully');
                await this.jobListManager.loadJobs();

            } catch (error) {
                console.error('Failed to delete job:', error);
                window.toast.error('Failed to delete job: ' + error.message);
            }
        });
    }
}
