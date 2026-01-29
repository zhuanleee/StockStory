/**
 * API Request Queue
 * Limits concurrent API requests to prevent overwhelming the server
 * @module api/queue
 */

/**
 * APIQueue class for managing concurrent API requests
 */
export class APIQueue {
    constructor(maxConcurrent = 3) {
        this.maxConcurrent = maxConcurrent;
        this.queue = [];
        this.running = 0;
        this.completed = 0;
        this.failed = 0;
    }

    /**
     * Adds a task to the queue
     *
     * @param {Function} fn - Async function to execute
     * @param {number} [priority=0] - Priority (higher = execute first)
     * @returns {Promise} Promise that resolves with the task result
     *
     * @example
     * const result = await apiQueue.add(() => fetchScan(), 10);
     */
    async add(fn, priority = 0) {
        return new Promise((resolve, reject) => {
            this.queue.push({
                fn,
                resolve,
                reject,
                priority,
                addedAt: Date.now()
            });

            // Sort by priority (higher priority first)
            this.queue.sort((a, b) => b.priority - a.priority);

            // Start processing
            this._processQueue();
        });
    }

    /**
     * Processes the queue
     * @private
     */
    async _processQueue() {
        while (this.running < this.maxConcurrent && this.queue.length > 0) {
            const task = this.queue.shift();
            this.running++;

            try {
                const result = await task.fn();
                task.resolve(result);
                this.completed++;
            } catch (error) {
                task.reject(error);
                this.failed++;
            } finally {
                this.running--;
                // Continue processing queue
                this._processQueue();
            }
        }
    }

    /**
     * Adds multiple tasks with priority
     *
     * @param {Array<{fn: Function, priority: number}>} tasks - Array of tasks
     * @returns {Promise<Array>} Promise that resolves with all results
     *
     * @example
     * const results = await apiQueue.addBatch([
     *     { fn: () => fetchScan(), priority: 10 },
     *     { fn: () => fetchTrades(), priority: 9 }
     * ]);
     */
    async addBatch(tasks) {
        return Promise.all(
            tasks.map(task => this.add(task.fn, task.priority || 0))
        );
    }

    /**
     * Adds multiple tasks and waits for all to settle
     * Returns results with status (fulfilled/rejected)
     *
     * @param {Array<{fn: Function, priority: number}>} tasks - Array of tasks
     * @returns {Promise<Array>} Promise that resolves with all results
     *
     * @example
     * const results = await apiQueue.addBatchSettled([
     *     { fn: () => fetchScan(), priority: 10 },
     *     { fn: () => fetchTrades(), priority: 9 }
     * ]);
     */
    async addBatchSettled(tasks) {
        return Promise.allSettled(
            tasks.map(task => this.add(task.fn, task.priority || 0))
        );
    }

    /**
     * Gets queue statistics
     *
     * @returns {Object} Queue statistics
     *
     * @example
     * const stats = apiQueue.stats();
     * console.log(`Running: ${stats.running}, Queued: ${stats.queued}`);
     */
    stats() {
        return {
            running: this.running,
            queued: this.queue.length,
            completed: this.completed,
            failed: this.failed,
            maxConcurrent: this.maxConcurrent
        };
    }

    /**
     * Clears the queue (does not cancel running tasks)
     *
     * @example
     * apiQueue.clear();
     */
    clear() {
        this.queue.forEach(task => {
            task.reject(new Error('Queue cleared'));
        });
        this.queue = [];
    }

    /**
     * Checks if queue is empty and no tasks are running
     *
     * @returns {boolean} True if idle
     *
     * @example
     * if (apiQueue.isIdle()) {
     *     console.log('All tasks completed');
     * }
     */
    isIdle() {
        return this.running === 0 && this.queue.length === 0;
    }

    /**
     * Waits for all tasks to complete
     *
     * @returns {Promise} Promise that resolves when queue is idle
     *
     * @example
     * await apiQueue.drain();
     * console.log('All tasks completed');
     */
    async drain() {
        return new Promise((resolve) => {
            const check = () => {
                if (this.isIdle()) {
                    resolve();
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    }

    /**
     * Sets max concurrent tasks
     *
     * @param {number} max - Maximum concurrent tasks
     *
     * @example
     * apiQueue.setMaxConcurrent(5);
     */
    setMaxConcurrent(max) {
        this.maxConcurrent = max;
        this._processQueue(); // Process any queued tasks with new limit
    }

    /**
     * Gets current max concurrent tasks
     *
     * @returns {number} Maximum concurrent tasks
     *
     * @example
     * const max = apiQueue.getMaxConcurrent();
     */
    getMaxConcurrent() {
        return this.maxConcurrent;
    }

    /**
     * Resets statistics
     *
     * @example
     * apiQueue.resetStats();
     */
    resetStats() {
        this.completed = 0;
        this.failed = 0;
    }

    /**
     * Gets queue length
     *
     * @returns {number} Number of queued tasks
     *
     * @example
     * console.log(`${apiQueue.length()} tasks in queue`);
     */
    length() {
        return this.queue.length;
    }

    /**
     * Gets number of running tasks
     *
     * @returns {number} Number of running tasks
     *
     * @example
     * console.log(`${apiQueue.runningCount()} tasks running`);
     */
    runningCount() {
        return this.running;
    }
}

// Export singleton instance with default max concurrent = 3
export const apiQueue = new APIQueue(3);

/**
 * Helper function to wrap fetch calls in the queue
 *
 * @param {Function} fetchFn - Fetch function to execute
 * @param {number} [priority=0] - Priority level
 * @returns {Promise} Promise that resolves with fetch result
 *
 * @example
 * const data = await queuedFetch(() => api.get('scan/top-picks'), 10);
 */
export async function queuedFetch(fetchFn, priority = 0) {
    return apiQueue.add(fetchFn, priority);
}
