/**
 * API Service - Centralized API handling for Wiseflow UI components
 * 
 * This module provides a centralized service for making API calls
 * from different UI components in the Wiseflow application.
 */

const ApiService = (function() {
    // Base API URL - configurable based on environment
    const baseUrl = window.API_BASE_URL || '/api';
    
    // API version
    const apiVersion = window.API_VERSION || 'v1';
    
    // Full API URL with version
    const apiUrl = `${baseUrl}/${apiVersion}`;
    
    // Default request options
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        credentials: 'same-origin' // Include cookies for same-origin requests
    };
    
    // Request queue for rate limiting
    const requestQueue = [];
    let isProcessingQueue = false;
    
    // Maximum number of concurrent requests
    const MAX_CONCURRENT_REQUESTS = 5;
    
    // Current number of active requests
    let activeRequests = 0;
    
    // Process the request queue
    function processQueue() {
        if (isProcessingQueue || requestQueue.length === 0 || activeRequests >= MAX_CONCURRENT_REQUESTS) {
            return;
        }
        
        isProcessingQueue = true;
        
        while (requestQueue.length > 0 && activeRequests < MAX_CONCURRENT_REQUESTS) {
            const { url, options, resolve, reject } = requestQueue.shift();
            
            activeRequests++;
            
            fetch(url, options)
                .then(response => {
                    if (!response.ok) {
                        // Try to parse error response as JSON
                        return response.json()
                            .then(errorData => {
                                throw new Error(errorData.message || `HTTP error ${response.status}: ${response.statusText}`);
                            })
                            .catch(jsonError => {
                                // If JSON parsing fails, use status text
                                throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                            });
                    }
                    return response.json();
                })
                .then(data => {
                    resolve(data);
                    activeRequests--;
                    
                    // Emit event for successful API response
                    if (window.EventBus) {
                        EventBus.emit(EVENTS.DATA_LOADED, { 
                            endpoint: url, 
                            data: data 
                        });
                    }
                })
                .catch(error => {
                    reject(error);
                    activeRequests--;
                    
                    // Emit event for API error
                    if (window.EventBus) {
                        EventBus.emit(EVENTS.DATA_ERROR, { 
                            endpoint: url, 
                            error: error.message 
                        });
                    }
                    
                    // Log error
                    console.error(`API Error (${url}):`, error);
                    
                    // Show error toast if Utils is available
                    if (window.Utils && typeof Utils.showToast === 'function') {
                        Utils.showToast(`API Error: ${error.message}`, 'error');
                    }
                })
                .finally(() => {
                    isProcessingQueue = false;
                    processQueue();
                });
        }
    }
    
    // Add a request to the queue
    function queueRequest(url, options) {
        return new Promise((resolve, reject) => {
            requestQueue.push({ url, options, resolve, reject });
            processQueue();
        });
    }
    
    // Handle API errors
    function handleApiError(error, endpoint) {
        // Log error
        console.error(`API Error (${endpoint}):`, error);
        
        // Emit event for API error
        if (window.EventBus) {
            EventBus.emit(EVENTS.DATA_ERROR, { 
                endpoint: endpoint, 
                error: error.message 
            });
        }
        
        // Show error toast if Utils is available
        if (window.Utils && typeof Utils.showToast === 'function') {
            Utils.showToast(`API Error: ${error.message}`, 'error');
        }
        
        // Rethrow error for caller to handle
        throw error;
    }
    
    // Build full URL with query parameters
    function buildUrl(endpoint, params = {}) {
        const url = new URL(apiUrl + endpoint, window.location.origin);
        
        // Add query parameters
        Object.keys(params).forEach(key => {
            if (params[key] !== undefined && params[key] !== null) {
                url.searchParams.append(key, params[key]);
            }
        });
        
        return url.toString();
    }
    
    return {
        /**
         * Get the base API URL
         * @returns {string} Base API URL
         */
        getBaseUrl: function() {
            return baseUrl;
        },
        
        /**
         * Get the API version
         * @returns {string} API version
         */
        getApiVersion: function() {
            return apiVersion;
        },
        
        /**
         * Get the full API URL with version
         * @returns {string} Full API URL
         */
        getApiUrl: function() {
            return apiUrl;
        },
        
        /**
         * Make a GET request
         * @param {string} endpoint - API endpoint
         * @param {object} params - Query parameters
         * @param {boolean} useQueue - Whether to use the request queue
         * @returns {Promise} Promise that resolves with the response data
         */
        get: function(endpoint, params = {}, useQueue = false) {
            const url = buildUrl(endpoint, params);
            
            const options = {
                ...defaultOptions,
                method: 'GET'
            };
            
            if (useQueue) {
                return queueRequest(url, options);
            }
            
            return fetch(url, options)
                .then(response => {
                    if (!response.ok) {
                        // Try to parse error response as JSON
                        return response.json()
                            .then(errorData => {
                                throw new Error(errorData.message || `HTTP error ${response.status}: ${response.statusText}`);
                            })
                            .catch(jsonError => {
                                // If JSON parsing fails, use status text
                                throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                            });
                    }
                    return response.json();
                })
                .then(data => {
                    // Emit event for successful API response
                    if (window.EventBus) {
                        EventBus.emit(EVENTS.DATA_LOADED, { 
                            endpoint: endpoint, 
                            data: data 
                        });
                    }
                    
                    return data;
                })
                .catch(error => handleApiError(error, endpoint));
        },
        
        /**
         * Make a POST request
         * @param {string} endpoint - API endpoint
         * @param {object} data - Request body data
         * @param {boolean} useQueue - Whether to use the request queue
         * @returns {Promise} Promise that resolves with the response data
         */
        post: function(endpoint, data = {}, useQueue = false) {
            const url = apiUrl + endpoint;
            
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
                        // Try to parse error response as JSON
                        return response.json()
                            .then(errorData => {
                                throw new Error(errorData.message || `HTTP error ${response.status}: ${response.statusText}`);
                            })
                            .catch(jsonError => {
                                // If JSON parsing fails, use status text
                                throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                            });
                    }
                    return response.json();
                })
                .then(data => {
                    // Emit event for successful API response
                    if (window.EventBus) {
                        EventBus.emit(EVENTS.DATA_SAVED, { 
                            endpoint: endpoint, 
                            data: data 
                        });
                    }
                    
                    return data;
                })
                .catch(error => handleApiError(error, endpoint));
        },
        
        /**
         * Make a PUT request
         * @param {string} endpoint - API endpoint
         * @param {object} data - Request body data
         * @param {boolean} useQueue - Whether to use the request queue
         * @returns {Promise} Promise that resolves with the response data
         */
        put: function(endpoint, data = {}, useQueue = false) {
            const url = apiUrl + endpoint;
            
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
                        // Try to parse error response as JSON
                        return response.json()
                            .then(errorData => {
                                throw new Error(errorData.message || `HTTP error ${response.status}: ${response.statusText}`);
                            })
                            .catch(jsonError => {
                                // If JSON parsing fails, use status text
                                throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                            });
                    }
                    return response.json();
                })
                .then(data => {
                    // Emit event for successful API response
                    if (window.EventBus) {
                        EventBus.emit(EVENTS.DATA_SAVED, { 
                            endpoint: endpoint, 
                            data: data 
                        });
                    }
                    
                    return data;
                })
                .catch(error => handleApiError(error, endpoint));
        },
        
        /**
         * Make a DELETE request
         * @param {string} endpoint - API endpoint
         * @param {boolean} useQueue - Whether to use the request queue
         * @returns {Promise} Promise that resolves with the response data
         */
        delete: function(endpoint, useQueue = false) {
            const url = apiUrl + endpoint;
            
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
                        // Try to parse error response as JSON
                        return response.json()
                            .then(errorData => {
                                throw new Error(errorData.message || `HTTP error ${response.status}: ${response.statusText}`);
                            })
                            .catch(jsonError => {
                                // If JSON parsing fails, use status text
                                throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                            });
                    }
                    return response.json();
                })
                .then(data => {
                    // Emit event for successful API response
                    if (window.EventBus) {
                        EventBus.emit(EVENTS.DATA_DELETED, { 
                            endpoint: endpoint, 
                            data: data 
                        });
                    }
                    
                    return data;
                })
                .catch(error => handleApiError(error, endpoint));
        },
        
        /**
         * Upload a file
         * @param {string} endpoint - API endpoint
         * @param {FormData} formData - Form data with files
         * @param {Function} progressCallback - Callback for upload progress
         * @returns {Promise} Promise that resolves with the response data
         */
        upload: function(endpoint, formData, progressCallback = null) {
            const url = apiUrl + endpoint;
            
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                
                xhr.open('POST', url, true);
                
                // Add default headers (except Content-Type, which is set automatically for FormData)
                Object.entries(defaultOptions.headers).forEach(([key, value]) => {
                    if (key !== 'Content-Type') {
                        xhr.setRequestHeader(key, value);
                    }
                });
                
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
                            
                            // Emit event for successful API response
                            if (window.EventBus) {
                                EventBus.emit(EVENTS.DATA_SAVED, { 
                                    endpoint: endpoint, 
                                    data: data 
                                });
                            }
                            
                            resolve(data);
                        } catch (error) {
                            reject(new Error('Invalid JSON response'));
                        }
                    } else {
                        try {
                            const errorData = JSON.parse(xhr.responseText);
                            reject(new Error(errorData.message || `HTTP error ${xhr.status}: ${xhr.statusText}`));
                        } catch (jsonError) {
                            reject(new Error(`HTTP error ${xhr.status}: ${xhr.statusText}`));
                        }
                    }
                };
                
                xhr.onerror = function() {
                    const error = new Error('Network error');
                    handleApiError(error, endpoint);
                    reject(error);
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
