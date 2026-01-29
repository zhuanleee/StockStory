/**
 * Toast notification system
 * @module components/Toast
 */

/**
 * Toast notification manager
 */
export class ToastManager {
    constructor() {
        this.container = this._createContainer();
        this.toasts = new Map();
    }

    /**
     * Creates the toast container element
     * @private
     */
    _createContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
                max-width: 400px;
            `;
            document.body.appendChild(container);
        }
        return container;
    }

    /**
     * Shows a toast notification
     *
     * @param {string} message - The message to display
     * @param {string} [type='info'] - Toast type: 'info', 'success', 'warning', 'error'
     * @param {number} [duration=5000] - Duration in ms (0 = no auto-dismiss)
     * @returns {HTMLElement} The toast element
     *
     * @example
     * toast.show('Operation successful!', 'success');
     */
    show(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        const id = Date.now() + Math.random();
        toast.className = `toast toast-${type}`;
        toast.dataset.toastId = id;

        const colors = {
            info: '#3b82f6',
            success: '#10b981',
            warning: '#f59e0b',
            error: '#ef4444'
        };

        const icons = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌'
        };

        toast.style.cssText = `
            min-width: 300px;
            background: var(--bg-secondary);
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            display: flex;
            align-items: center;
            gap: 12px;
            animation: slideIn 0.3s ease;
            border-left: 4px solid ${colors[type]};
        `;

        toast.innerHTML = `
            <div class="toast-icon" style="font-size: 1.25rem;">${icons[type]}</div>
            <div class="toast-message" style="flex: 1; color: var(--text);">${message}</div>
            <button class="toast-close" style="
                background: none;
                border: none;
                color: var(--text-muted);
                cursor: pointer;
                font-size: 1.5rem;
                padding: 0;
                line-height: 1;
            ">×</button>
        `;

        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.onclick = () => this.remove(id);

        this.container.appendChild(toast);
        this.toasts.set(id, toast);

        // Auto-dismiss after duration
        if (duration > 0) {
            setTimeout(() => this.remove(id), duration);
        }

        return toast;
    }

    /**
     * Shows a success toast
     *
     * @param {string} message - The success message
     * @param {number} [duration=5000] - Duration in ms
     * @returns {HTMLElement} The toast element
     *
     * @example
     * toast.success('Trade added successfully!');
     */
    success(message, duration = 5000) {
        return this.show(message, 'success', duration);
    }

    /**
     * Shows an error toast
     *
     * @param {string} message - The error message
     * @param {Object} [options={}] - Options object
     * @param {number} [options.duration=10000] - Duration in ms
     * @param {Function} [options.retry] - Retry callback function
     * @returns {HTMLElement} The toast element
     *
     * @example
     * toast.error('Failed to load data', {
     *     retry: () => fetchData()
     * });
     */
    error(message, options = {}) {
        const toast = this.show(message, 'error', options.duration || 10000);

        if (options.retry) {
            const retryBtn = document.createElement('button');
            retryBtn.className = 'toast-retry';
            retryBtn.textContent = 'Retry';
            retryBtn.style.cssText = `
                background: var(--primary);
                border: none;
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.875rem;
                margin-left: 8px;
            `;
            retryBtn.onclick = () => {
                const id = toast.dataset.toastId;
                this.remove(id);
                options.retry();
            };
            toast.querySelector('.toast-message').appendChild(retryBtn);
        }

        return toast;
    }

    /**
     * Shows a warning toast
     *
     * @param {string} message - The warning message
     * @param {number} [duration=7000] - Duration in ms
     * @returns {HTMLElement} The toast element
     *
     * @example
     * toast.warning('Connection unstable');
     */
    warning(message, duration = 7000) {
        return this.show(message, 'warning', duration);
    }

    /**
     * Shows an info toast
     *
     * @param {string} message - The info message
     * @param {number} [duration=5000] - Duration in ms
     * @returns {HTMLElement} The toast element
     *
     * @example
     * toast.info('Data refreshed');
     */
    info(message, duration = 5000) {
        return this.show(message, 'info', duration);
    }

    /**
     * Removes a toast by ID
     *
     * @param {number} id - The toast ID
     *
     * @example
     * toast.remove(toastId);
     */
    remove(id) {
        const toast = this.toasts.get(id);
        if (toast) {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                toast.remove();
                this.toasts.delete(id);
            }, 300);
        }
    }

    /**
     * Clears all toasts
     *
     * @example
     * toast.clearAll();
     */
    clearAll() {
        this.toasts.forEach((toast, id) => this.remove(id));
    }
}

// Add CSS animations if not already present
if (!document.getElementById('toast-animations')) {
    const style = document.createElement('style');
    style.id = 'toast-animations';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

// Export singleton instance
export const toast = new ToastManager();
