/**
 * API Client for WiseFlow
 * 
 * This module provides a centralized client for making API calls to the backend.
 * It handles common concerns like error handling, authentication, and request formatting.
 */

const ApiClient = (function() {
    // Base API URL - standardized to match ApiService
    const BASE_URL = '/api';
    
    // Default request options
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    };
    
    /**
     * Make a fetch request with error handling
     * @param {string} url - API endpoint URL
     * @param {Object} options - Fetch options
     * @returns {Promise} Promise that resolves to the response data
     */
    async function fetchWithErrorHandling(url, options) {
        try {
            const response = await fetch(url, options);
            
            // Handle HTTP errors
            if (!response.ok) {
                let errorMessage = `HTTP error ${response.status}`;
                
                // Try to parse error message from response
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorData.message || errorMessage;
                } catch (e) {
                    // If parsing fails, use the status text
                    errorMessage = response.statusText || errorMessage;
                }
                
                throw new Error(errorMessage);
            }
            
            // Parse JSON response
            const data = await response.json();
            return data;
        } catch (error) {
            // Log error and show notification
            console.error('API request failed:', error);
            
            // Show error notification if WiseFlowUtils is available
            if (window.WiseFlowUtils) {
                window.WiseFlowUtils.showToast(
                    `API request failed: ${error.message}`,
                    'danger',
                    5000
                );
            }
            
            // Rethrow the error for the caller to handle
            throw error;
        }
    }
    
    /**
     * Make a GET request
     * @param {string} endpoint - API endpoint
     * @param {Object} params - Query parameters
     * @returns {Promise} Promise that resolves to the response data
     */
    async function get(endpoint, params = {}) {
        // Build query string
        const queryString = Object.keys(params)
            .filter(key => params[key] !== undefined && params[key] !== null)
            .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
            .join('&');
        
        const url = `${BASE_URL}${endpoint}${queryString ? '?' + queryString : ''}`;
        
        return fetchWithErrorHandling(url, {
            ...defaultOptions,
            method: 'GET'
        });
    }
    
    /**
     * Make a POST request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request body data
     * @returns {Promise} Promise that resolves to the response data
     */
    async function post(endpoint, data = {}) {
        const url = `${BASE_URL}${endpoint}`;
        
        return fetchWithErrorHandling(url, {
            ...defaultOptions,
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    /**
     * Make a POST request with FormData (for file uploads)
     * @param {string} endpoint - API endpoint
     * @param {FormData} formData - FormData object
     * @returns {Promise} Promise that resolves to the response data
     */
    async function postFormData(endpoint, formData) {
        const url = `${BASE_URL}${endpoint}`;
        
        // Don't set Content-Type header for FormData
        // The browser will set it automatically with the boundary
        const options = {
            ...defaultOptions,
            headers: {},
            method: 'POST',
            body: formData
        };
        
        return fetchWithErrorHandling(url, options);
    }
    
    /**
     * Make a PUT request
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request body data
     * @returns {Promise} Promise that resolves to the response data
     */
    async function put(endpoint, data = {}) {
        const url = `${BASE_URL}${endpoint}`;
        
        return fetchWithErrorHandling(url, {
            ...defaultOptions,
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }
    
    /**
     * Make a DELETE request
     * @param {string} endpoint - API endpoint
     * @returns {Promise} Promise that resolves to the response data
     */
    async function del(endpoint) {
        const url = `${BASE_URL}${endpoint}`;
        
        return fetchWithErrorHandling(url, {
            ...defaultOptions,
            method: 'DELETE'
        });
    }
    
    // Data Mining API endpoints
    const dataMining = {
        // Tasks
        getTasks: (status) => get('/api/data-mining/tasks', { status }),
        getTask: (taskId) => get(`/api/data-mining/tasks/${taskId}`),
        createTask: (formData) => postFormData('/api/data-mining/tasks', formData),
        updateTask: (taskId, data) => put(`/api/data-mining/tasks/${taskId}`, data),
        deleteTask: (taskId) => del(`/api/data-mining/tasks/${taskId}`),
        
        // Templates
        getTemplates: (templateType) => get('/api/data-mining/templates', { template_type: templateType }),
        saveTemplate: (templateData) => post('/api/data-mining/templates', templateData),
        
        // Interconnections
        getInterconnections: () => get('/api/data-mining/interconnections'),
        createInterconnection: (data) => post('/api/data-mining/interconnections', data),
        deleteInterconnection: (id) => del(`/api/data-mining/interconnections/${id}`),
        
        // Preview
        generatePreview: (searchParams) => post('/api/data-mining/preview', searchParams)
    };
    
    // Public API
    return {
        get,
        post,
        postFormData,
        put,
        delete: del,
        dataMining
    };
})();

// Make ApiClient available globally
window.ApiClient = ApiClient;
