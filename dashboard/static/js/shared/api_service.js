/**
 * API Service - Centralized API handling for Wiseflow UI components
 * 
 * This module provides a centralized service for making API calls
 * from different UI components in the Wiseflow application.
 */

const ApiService = (function() {
    // Base API URL
    const baseUrl = '/api';
    
    // Default request options
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    // Request queue for rate limiting
    const requestQueue = [];
    let isProcessingQueue = false;
    
    // Process the request queue
    function processQueue() {
        if (isProcessingQueue || requestQueue.length === 0) {
            return;
        }
        
        isProcessingQueue = true;
        
        const { url, options, resolve, reject } = requestQueue.shift();
        
        fetch(url, options)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                resolve(data);
                isProcessingQueue = false;
                processQueue();
            })
            .catch(error => {
                reject(error);
                isProcessingQueue = false;
                processQueue();
            });
    }
    
    // Add a request to the queue
    function queueRequest(url, options) {
        return new Promise((resolve, reject) => {
            requestQueue.push({ url, options, resolve, reject });
            processQueue();
        });
    }
    
    return {
        /**
         * Make a GET request
         * @param {string} endpoint - API endpoint
         * @param {object} params - Query parameters
         * @param {boolean} useQueue - Whether to use the request queue
         * @returns {Promise} Promise that resolves with the response data
         */
        get: function(endpoint, params = {}, useQueue = false) {
            const url = new URL(baseUrl + endpoint, window.location.origin);
            
            // Add query parameters
            Object.keys(params).forEach(key => {
                if (params[key] !== undefined && params[key] !== null) {
                    url.searchParams.append(key, params[key]);
                }
            });
            
            const options = {
                ...defaultOptions,
                method: 'GET'
            };
            
            if (useQueue) {
                return queueRequest(url.toString(), options);
            }
            
            return fetch(url.toString(), options)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                });
        },
        
        /**
         * Make a POST request
         * @param {string} endpoint - API endpoint
         * @param {object} data - Request body data
         * @param {boolean} useQueue - Whether to use the request queue
         * @returns {Promise} Promise that resolves with the response data
         */
        post: function(endpoint, data = {}, useQueue = false) {
            const url = baseUrl + endpoint;
            
            const options = {
                ...defaultOptions,
                method: 'POST',
                body: JSON.stringify(data)
            };
            
            if (useQueue) {
                return queueRequest(url, options);
            }
            
            return fetch(url, options)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                });
        },
        
        /**
         * Make a PUT request
         * @param {string} endpoint - API endpoint
         * @param {object} data - Request body data
         * @param {boolean} useQueue - Whether to use the request queue
         * @returns {Promise} Promise that resolves with the response data
         */
        put: function(endpoint, data = {}, useQueue = false) {
            const url = baseUrl + endpoint;
            
            const options = {
                ...defaultOptions,
                method: 'PUT',
                body: JSON.stringify(data)
            };
            
            if (useQueue) {
                return queueRequest(url, options);
            }
            
            return fetch(url, options)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                });
        },
        
        /**
         * Make a DELETE request
         * @param {string} endpoint - API endpoint
         * @param {boolean} useQueue - Whether to use the request queue
         * @returns {Promise} Promise that resolves with the response data
         */
        delete: function(endpoint, useQueue = false) {
            const url = baseUrl + endpoint;
            
            const options = {
                ...defaultOptions,
                method: 'DELETE'
            };
            
            if (useQueue) {
                return queueRequest(url, options);
            }
            
            return fetch(url, options)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                });
        },
        
        /**
         * Upload a file
         * @param {string} endpoint - API endpoint
         * @param {FormData} formData - Form data with files
         * @param {Function} progressCallback - Callback for upload progress
         * @returns {Promise} Promise that resolves with the response data
         */
        upload: function(endpoint, formData, progressCallback = null) {
            const url = baseUrl + endpoint;
            
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                
                xhr.open('POST', url, true);
                
                // Set up progress event
                if (progressCallback && typeof progressCallback === 'function') {
                    xhr.upload.onprogress = function(event) {
                        if (event.lengthComputable) {
                            const percentComplete = (event.loaded / event.total) * 100;
                            progressCallback(percentComplete);
                        }
                    };
                }
                
                xhr.onload = function() {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const data = JSON.parse(xhr.responseText);
                            resolve(data);
                        } catch (error) {
                            reject(new Error('Invalid JSON response'));
                        }
                    } else {
                        reject(new Error(`HTTP error ${xhr.status}: ${xhr.statusText}`));
                    }
                };
                
                xhr.onerror = function() {
                    reject(new Error('Network error'));
                };
                
                xhr.send(formData);
            });
        },
        
        /**
         * API endpoints for data mining
         */
        dataMining: {
            /**
             * Get all data mining tasks
             * @returns {Promise} Promise that resolves with the tasks
             */
            getTasks: function() {
                return ApiService.get('/data-mining/tasks');
            },
            
            /**
             * Get a data mining task by ID
             * @param {string} taskId - Task ID
             * @returns {Promise} Promise that resolves with the task
             */
            getTask: function(taskId) {
                return ApiService.get(`/data-mining/tasks/${taskId}`);
            },
            
            /**
             * Create a new data mining task
             * @param {object} taskData - Task data
             * @returns {Promise} Promise that resolves with the created task
             */
            createTask: function(taskData) {
                return ApiService.post('/data-mining/tasks', taskData);
            },
            
            /**
             * Update a data mining task
             * @param {string} taskId - Task ID
             * @param {object} taskData - Task data
             * @returns {Promise} Promise that resolves with the updated task
             */
            updateTask: function(taskId, taskData) {
                return ApiService.put(`/data-mining/tasks/${taskId}`, taskData);
            },
            
            /**
             * Delete a data mining task
             * @param {string} taskId - Task ID
             * @returns {Promise} Promise that resolves with the result
             */
            deleteTask: function(taskId) {
                return ApiService.delete(`/data-mining/tasks/${taskId}`);
            },
            
            /**
             * Start a data mining task
             * @param {string} taskId - Task ID
             * @returns {Promise} Promise that resolves with the result
             */
            startTask: function(taskId) {
                return ApiService.post(`/data-mining/tasks/${taskId}/start`);
            },
            
            /**
             * Pause a data mining task
             * @param {string} taskId - Task ID
             * @returns {Promise} Promise that resolves with the result
             */
            pauseTask: function(taskId) {
                return ApiService.post(`/data-mining/tasks/${taskId}/pause`);
            },
            
            /**
             * Resume a data mining task
             * @param {string} taskId - Task ID
             * @returns {Promise} Promise that resolves with the result
             */
            resumeTask: function(taskId) {
                return ApiService.post(`/data-mining/tasks/${taskId}/resume`);
            },
            
            /**
             * Stop a data mining task
             * @param {string} taskId - Task ID
             * @returns {Promise} Promise that resolves with the result
             */
            stopTask: function(taskId) {
                return ApiService.post(`/data-mining/tasks/${taskId}/stop`);
            },
            
            /**
             * Get task findings
             * @param {string} taskId - Task ID
             * @returns {Promise} Promise that resolves with the findings
             */
            getFindings: function(taskId) {
                return ApiService.get(`/data-mining/tasks/${taskId}/findings`);
            },
            
            /**
             * Export task findings
             * @param {string} taskId - Task ID
             * @param {string} format - Export format (json, csv, etc.)
             * @returns {Promise} Promise that resolves with the export URL
             */
            exportFindings: function(taskId, format = 'json') {
                return ApiService.get(`/data-mining/tasks/${taskId}/export`, { format });
            }
        },
        
        /**
         * API endpoints for templates
         */
        templates: {
            /**
             * Get all templates
             * @param {string} type - Optional template type filter
             * @returns {Promise} Promise that resolves with the templates
             */
            getTemplates: function(type = null) {
                return ApiService.get('/data-mining/templates', { type });
            },
            
            /**
             * Get a template by ID
             * @param {string} templateId - Template ID
             * @returns {Promise} Promise that resolves with the template
             */
            getTemplate: function(templateId) {
                return ApiService.get(`/data-mining/templates/${templateId}`);
            },
            
            /**
             * Create a new template
             * @param {object} templateData - Template data
             * @returns {Promise} Promise that resolves with the created template
             */
            createTemplate: function(templateData) {
                return ApiService.post('/data-mining/templates', templateData);
            },
            
            /**
             * Update a template
             * @param {string} templateId - Template ID
             * @param {object} templateData - Template data
             * @returns {Promise} Promise that resolves with the updated template
             */
            updateTemplate: function(templateId, templateData) {
                return ApiService.put(`/data-mining/templates/${templateId}`, templateData);
            },
            
            /**
             * Delete a template
             * @param {string} templateId - Template ID
             * @returns {Promise} Promise that resolves with the result
             */
            deleteTemplate: function(templateId) {
                return ApiService.delete(`/data-mining/templates/${templateId}`);
            },
            
            /**
             * Export templates
             * @param {string[]} templateIds - Template IDs to export
             * @returns {Promise} Promise that resolves with the export data
             */
            exportTemplates: function(templateIds = []) {
                return ApiService.post('/data-mining/templates/export', { templateIds });
            },
            
            /**
             * Import templates
             * @param {object} templatesData - Templates data to import
             * @returns {Promise} Promise that resolves with the import result
             */
            importTemplates: function(templatesData) {
                return ApiService.post('/data-mining/templates/import', templatesData);
            }
        }
    };
})();

// Export ApiService for use in other modules
window.ApiService = ApiService;

