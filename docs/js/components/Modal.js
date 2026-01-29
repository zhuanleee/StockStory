/**
 * Reusable Modal component
 * @module components/Modal
 */

/**
 * Modal component for displaying dialogs and forms
 */
export class Modal {
    constructor(id = 'modal') {
        this.element = document.getElementById(id);
        this.overlay = this.element ? this.element.closest('.modal-overlay') : null;
        this.title = this.element ? this.element.querySelector('.modal-title') : null;
        this.body = this.element ? this.element.querySelector('.modal-body') : null;
        this.previousFocus = null;

        if (this.element && this.overlay) {
            this._setupEventListeners();
        }
    }

    /**
     * Sets up event listeners for modal interactions
     * @private
     */
    _setupEventListeners() {
        // Close on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.overlay.classList.contains('active')) {
                this.hide();
            }
        });

        // Close on overlay click
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.hide();
            }
        });
    }

    /**
     * Shows the modal
     *
     * @example
     * modal.show();
     */
    show() {
        if (!this.overlay) return;

        this.previousFocus = document.activeElement;
        this.overlay.classList.add('active');

        // Focus first focusable element
        const firstFocusable = this.element.querySelector('button, input, textarea, select, a');
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }

        // Trap focus within modal
        this._trapFocus();
    }

    /**
     * Hides the modal
     *
     * @example
     * modal.hide();
     */
    hide() {
        if (!this.overlay) return;

        this.overlay.classList.remove('active');

        // Restore focus to previously focused element
        if (this.previousFocus) {
            this.previousFocus.focus();
        }
    }

    /**
     * Sets the modal title
     *
     * @param {string} title - The title text
     *
     * @example
     * modal.setTitle('Add Trade');
     */
    setTitle(title) {
        if (this.title) {
            this.title.textContent = title;
        }
    }

    /**
     * Sets the modal content
     *
     * @param {string} html - The HTML content
     *
     * @example
     * modal.setContent('<p>Modal content here</p>');
     */
    setContent(html) {
        if (this.body) {
            this.body.innerHTML = html;
        }
    }

    /**
     * Shows a loading state
     *
     * @param {string} [message='Loading...'] - The loading message
     *
     * @example
     * modal.setLoading('Fetching data...');
     */
    setLoading(message = 'Loading...') {
        if (!this.body) return;

        this.body.innerHTML = `
            <div class="loading-spinner" style="text-align: center; padding: 40px;">
                <div class="spinner" style="
                    width: 40px;
                    height: 40px;
                    border: 4px solid var(--bg-secondary);
                    border-top-color: var(--primary);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 16px;
                "></div>
                <div style="color: var(--text-muted);">${message}</div>
            </div>
        `;
    }

    /**
     * Shows an error state
     *
     * @param {string} message - The error message
     * @param {Object} [options={}] - Options object
     * @param {Function} [options.retry] - Retry callback function
     *
     * @example
     * modal.setError('Failed to load data', {
     *     retry: () => fetchData()
     * });
     */
    setError(message, options = {}) {
        if (!this.body) return;

        const retryHTML = options.retry
            ? `<button onclick="(${options.retry})()" style="
                margin-top: 16px;
                padding: 8px 16px;
                background: var(--primary);
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
            ">Retry</button>`
            : '';

        this.body.innerHTML = `
            <div class="error-message" style="text-align: center; padding: 40px;">
                <div class="error-icon" style="font-size: 3rem; margin-bottom: 16px;">❌</div>
                <div style="color: var(--text); margin-bottom: 8px; font-weight: 500;">${message}</div>
                ${retryHTML}
            </div>
        `;
    }

    /**
     * Shows a success state
     *
     * @param {string} message - The success message
     *
     * @example
     * modal.setSuccess('Trade added successfully!');
     */
    setSuccess(message) {
        if (!this.body) return;

        this.body.innerHTML = `
            <div class="success-message" style="text-align: center; padding: 40px;">
                <div class="success-icon" style="font-size: 3rem; margin-bottom: 16px;">✅</div>
                <div style="color: var(--green); font-weight: 500;">${message}</div>
            </div>
        `;
    }

    /**
     * Traps focus within the modal
     * @private
     */
    _trapFocus() {
        if (!this.element) return;

        const focusableElements = this.element.querySelectorAll(
            'button, input, textarea, select, a[href]'
        );

        if (focusableElements.length === 0) return;

        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];

        this.element.addEventListener('keydown', (e) => {
            if (e.key !== 'Tab') return;

            if (e.shiftKey) {
                // Shift + Tab
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            } else {
                // Tab
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        });
    }

    /**
     * Checks if modal is currently visible
     *
     * @returns {boolean} True if modal is visible
     *
     * @example
     * if (modal.isVisible()) {
     *     modal.hide();
     * }
     */
    isVisible() {
        return this.overlay && this.overlay.classList.contains('active');
    }
}

// Export singleton instance (if modal exists)
export const modal = document.getElementById('modal') ? new Modal() : null;
