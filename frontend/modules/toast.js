/**
 * Toast Notification System
 * Replaces browser alerts with styled toast notifications
 */

class ToastManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Create toast container if it doesn't exist
        if (!document.getElementById('toast-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-container');
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Type: 'success', 'error', 'warning', 'info'
     * @param {number} duration - How long to show (ms), 0 = permanent
     */
    show(message, type = 'info', duration = 4000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        // Icon based on type
        const icons = {
            success: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M16 5L7.70504 14.595C7.31534 15.0315 6.68466 15.0315 6.29496 14.595L4 12.1818" 
                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>`,
            error: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="2"/>
                <path d="M10 6V11M10 14H10.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>`,
            warning: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M10 2L18 16H2L10 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                <path d="M10 8V11M10 14H10.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>`,
            info: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="2"/>
                <path d="M10 10V14M10 7H10.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>`
        };

        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-message">${this.escapeHtml(message)}</div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                    <path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </button>
        `;

        this.container.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('toast-show'), 10);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                toast.classList.remove('toast-show');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }

        return toast;
    }

    success(message, duration = 4000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 6000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 5000) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 4000) {
        return this.show(message, 'info', duration);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show confirmation dialog
     * @param {string} message - The confirmation message
     * @param {Function} onConfirm - Callback when confirmed
     */
    confirm(message, onConfirm) {
        const overlay = document.createElement('div');
        overlay.className = 'toast-overlay';
        
        const dialog = document.createElement('div');
        dialog.className = 'toast-confirm-dialog';
        
        dialog.innerHTML = `
            <div class="toast-confirm-icon">
                <svg width="48" height="48" viewBox="0 0 20 20" fill="none">
                    <circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="2"/>
                    <path d="M10 6V11M10 14H10.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </div>
            <div class="toast-confirm-message">${this.escapeHtml(message)}</div>
            <div class="toast-confirm-actions">
                <button class="toast-confirm-btn toast-confirm-cancel">Cancel</button>
                <button class="toast-confirm-btn toast-confirm-ok">OK</button>
            </div>
        `;
        
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        
        // Trigger animation
        setTimeout(() => {
            overlay.classList.add('toast-overlay-show');
            dialog.classList.add('toast-confirm-show');
        }, 10);
        
        // Handle buttons
        const cancelBtn = dialog.querySelector('.toast-confirm-cancel');
        const okBtn = dialog.querySelector('.toast-confirm-ok');
        
        const cleanup = () => {
            overlay.classList.remove('toast-overlay-show');
            dialog.classList.remove('toast-confirm-show');
            setTimeout(() => overlay.remove(), 200);
        };
        
        cancelBtn.addEventListener('click', cleanup);
        okBtn.addEventListener('click', () => {
            cleanup();
            if (onConfirm) onConfirm();
        });
        
        // ESC key to cancel
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                cleanup();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }
}

// Global instance
window.toast = new ToastManager();

// Replace window.alert with toast
window.alert = function(message) {
    window.toast.info(message);
};
