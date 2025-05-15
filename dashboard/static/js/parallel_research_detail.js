/**
 * Parallel Research Flow Detail View
 * Handles the detailed view of a specific research flow, including real-time updates
 * and interactive controls for managing the flow.
 */

// Flow ID from the URL
const flowId = window.location.pathname.split('/').pop();
let flowData = null;
let updateInterval = null;
const UPDATE_INTERVAL_MS = 3000; // Update every 3 seconds

// DOM elements
const flowTitleElement = document.getElementById('flow-title');
const flowStatusElement = document.getElementById('flow-status');
const flowProgressElement = document.getElementById('flow-progress');
const flowControlsElement = document.getElementById('flow-controls');
const taskListElement = document.getElementById('task-list');
const flowResultsElement = document.getElementById('flow-results');
const flowLogsElement = document.getElementById('flow-logs');
const errorMessageElement = document.getElementById('error-message');

/**
 * Initialize the detail view
 */
function initDetailView() {
    // Fetch initial flow data
    fetchFlowData();
    
    // Set up real-time updates
    updateInterval = setInterval(fetchFlowData, UPDATE_INTERVAL_MS);
    
    // Set up control buttons
    setupControlButtons();
    
    // Set up WebSocket connection if available
    setupWebSocketConnection();
}

/**
 * Fetch flow data from the API
 */
async function fetchFlowData() {
    try {
        const response = await fetch(`/api/research-flows/${flowId}`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch flow data: ${response.statusText}`);
        }
        
        const data = await response.json();
        flowData = data;
        
        // Update the UI with the new data
        updateFlowDetails();
        updateTaskList();
        updateFlowResults();
        updateFlowLogs();
        
        // Hide any previous error messages
        hideErrorMessage();
        
        // If the flow is in a terminal state, stop polling
        if (['completed', 'failed', 'cancelled'].includes(flowData.status)) {
            clearInterval(updateInterval);
        }
    } catch (error) {
        showErrorMessage(`Error: ${error.message}`);
        console.error('Error fetching flow data:', error);
    }
}

/**
 * Update the flow details section
 */
function updateFlowDetails() {
    if (!flowData) return;
    
    // Update flow title
    flowTitleElement.textContent = flowData.name;
    
    // Update flow status
    flowStatusElement.textContent = flowData.status.toUpperCase();
    flowStatusElement.className = `status-badge status-${flowData.status}`;
    
    // Update progress bar
    const progressPercent = Math.round(flowData.progress * 100);
    flowProgressElement.querySelector('.progress-bar').style.width = `${progressPercent}%`;
    flowProgressElement.querySelector('.progress-text').textContent = `${progressPercent}%`;
    
    // Update control buttons based on current status
    updateControlButtons();
}

/**
 * Update the task list section
 */
function updateTaskList() {
    if (!flowData || !flowData.tasks) return;
    
    // Clear existing tasks
    taskListElement.innerHTML = '';
    
    // Add each task to the list
    flowData.tasks.forEach(task => {
        const taskElement = document.createElement('div');
        taskElement.className = `task-card status-${task.status}`;
        taskElement.innerHTML = `
            <div class="task-header">
                <h4 class="task-name">${task.name}</h4>
                <span class="task-status status-badge status-${task.status}">${task.status.toUpperCase()}</span>
            </div>
            <div class="task-details">
                <p class="task-description">${task.description || 'No description'}</p>
                <div class="task-source">Source: ${task.source}</div>
                <div class="task-progress">
                    <div class="progress">
                        <div class="progress-bar" style="width: ${Math.round(task.progress * 100)}%"></div>
                    </div>
                    <span class="progress-text">${Math.round(task.progress * 100)}%</span>
                </div>
            </div>
        `;
        
        // Add click handler to expand/collapse task details
        taskElement.querySelector('.task-header').addEventListener('click', () => {
            taskElement.classList.toggle('expanded');
        });
        
        taskListElement.appendChild(taskElement);
    });
}

/**
 * Update the flow results section
 */
function updateFlowResults() {
    if (!flowData || !flowData.results) return;
    
    // Clear existing results
    flowResultsElement.innerHTML = '';
    
    if (flowData.results.length === 0) {
        flowResultsElement.innerHTML = '<p class="no-results">No results available yet.</p>';
        return;
    }
    
    // Create results list
    const resultsList = document.createElement('ul');
    resultsList.className = 'results-list';
    
    flowData.results.forEach(result => {
        const resultItem = document.createElement('li');
        resultItem.className = 'result-item';
        resultItem.innerHTML = `
            <h4 class="result-title">${result.title}</h4>
            <p class="result-summary">${result.summary}</p>
            <div class="result-source">Source: ${result.source}</div>
            <div class="result-actions">
                <button class="btn btn-sm btn-outline-primary view-details-btn" data-result-id="${result.id}">
                    View Details
                </button>
                <button class="btn btn-sm btn-outline-secondary export-btn" data-result-id="${result.id}">
                    Export
                </button>
            </div>
        `;
        
        resultsList.appendChild(resultItem);
    });
    
    flowResultsElement.appendChild(resultsList);
    
    // Add event listeners for result actions
    setupResultActions();
}

/**
 * Update the flow logs section
 */
function updateFlowLogs() {
    if (!flowData || !flowData.logs) return;
    
    // Clear existing logs
    flowLogsElement.innerHTML = '';
    
    if (flowData.logs.length === 0) {
        flowLogsElement.innerHTML = '<p class="no-logs">No logs available.</p>';
        return;
    }
    
    // Create logs list
    const logsList = document.createElement('ul');
    logsList.className = 'logs-list';
    
    flowData.logs.forEach(log => {
        const logItem = document.createElement('li');
        logItem.className = `log-item log-level-${log.level.toLowerCase()}`;
        logItem.innerHTML = `
            <span class="log-timestamp">${new Date(log.timestamp).toLocaleString()}</span>
            <span class="log-level">${log.level}</span>
            <span class="log-message">${log.message}</span>
        `;
        
        logsList.appendChild(logItem);
    });
    
    flowLogsElement.appendChild(logsList);
    
    // Auto-scroll to the bottom of the logs
    flowLogsElement.scrollTop = flowLogsElement.scrollHeight;
}

/**
 * Set up control buttons for the flow
 */
function setupControlButtons() {
    // Clear existing buttons
    flowControlsElement.innerHTML = '';
    
    // Create control buttons based on available actions
    const startButton = document.createElement('button');
    startButton.className = 'btn btn-success control-btn start-btn';
    startButton.textContent = 'Start';
    startButton.addEventListener('click', () => controlFlow('start'));
    
    const pauseButton = document.createElement('button');
    pauseButton.className = 'btn btn-warning control-btn pause-btn';
    pauseButton.textContent = 'Pause';
    pauseButton.addEventListener('click', () => controlFlow('pause'));
    
    const resumeButton = document.createElement('button');
    resumeButton.className = 'btn btn-info control-btn resume-btn';
    resumeButton.textContent = 'Resume';
    resumeButton.addEventListener('click', () => controlFlow('resume'));
    
    const cancelButton = document.createElement('button');
    cancelButton.className = 'btn btn-danger control-btn cancel-btn';
    cancelButton.textContent = 'Cancel';
    cancelButton.addEventListener('click', () => controlFlow('cancel'));
    
    // Add buttons to the controls element
    flowControlsElement.appendChild(startButton);
    flowControlsElement.appendChild(pauseButton);
    flowControlsElement.appendChild(resumeButton);
    flowControlsElement.appendChild(cancelButton);
    
    // Update button states based on current flow status
    updateControlButtons();
}

/**
 * Update control button states based on current flow status
 */
function updateControlButtons() {
    if (!flowData) return;
    
    const startButton = flowControlsElement.querySelector('.start-btn');
    const pauseButton = flowControlsElement.querySelector('.pause-btn');
    const resumeButton = flowControlsElement.querySelector('.resume-btn');
    const cancelButton = flowControlsElement.querySelector('.cancel-btn');
    
    // Disable all buttons by default
    [startButton, pauseButton, resumeButton, cancelButton].forEach(btn => {
        if (btn) btn.disabled = true;
    });
    
    // Enable buttons based on current status
    switch (flowData.status) {
        case 'pending':
            if (startButton) startButton.disabled = false;
            if (cancelButton) cancelButton.disabled = false;
            break;
        case 'running':
            if (pauseButton) pauseButton.disabled = false;
            if (cancelButton) cancelButton.disabled = false;
            break;
        case 'paused':
            if (resumeButton) resumeButton.disabled = false;
            if (cancelButton) cancelButton.disabled = false;
            break;
        case 'completed':
        case 'failed':
        case 'cancelled':
            // All buttons remain disabled for terminal states
            break;
    }
}

/**
 * Send a control command to the flow
 * @param {string} action - The action to perform (start, pause, resume, cancel)
 */
async function controlFlow(action) {
    try {
        const response = await fetch(`/api/research-flows/${flowId}/${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to ${action} flow: ${response.statusText}`);
        }
        
        // Fetch updated flow data immediately
        fetchFlowData();
        
        // Show success message
        showSuccessMessage(`Flow ${action}ed successfully`);
    } catch (error) {
        showErrorMessage(`Error: ${error.message}`);
        console.error(`Error ${action}ing flow:`, error);
    }
}

/**
 * Set up event listeners for result actions
 */
function setupResultActions() {
    // View details buttons
    document.querySelectorAll('.view-details-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const resultId = event.target.dataset.resultId;
            viewResultDetails(resultId);
        });
    });
    
    // Export buttons
    document.querySelectorAll('.export-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const resultId = event.target.dataset.resultId;
            exportResult(resultId);
        });
    });
}

/**
 * View details for a specific result
 * @param {string} resultId - The ID of the result to view
 */
function viewResultDetails(resultId) {
    // Find the result in the flow data
    const result = flowData.results.find(r => r.id === resultId);
    
    if (!result) {
        showErrorMessage('Result not found');
        return;
    }
    
    // Create modal for result details
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'result-details-modal';
    modal.setAttribute('tabindex', '-1');
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-labelledby', 'result-details-title');
    modal.setAttribute('aria-hidden', 'true');
    
    modal.innerHTML = `
        <div class="modal-dialog modal-lg" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="result-details-title">${result.title}</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="result-metadata">
                        <div><strong>Source:</strong> ${result.source}</div>
                        <div><strong>Retrieved:</strong> ${new Date(result.timestamp).toLocaleString()}</div>
                    </div>
                    <div class="result-content">
                        ${result.content || result.summary}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary export-result-btn" data-result-id="${result.id}">
                        Export
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to the page
    document.body.appendChild(modal);
    
    // Initialize the modal
    $(modal).modal('show');
    
    // Add event listener for export button in modal
    modal.querySelector('.export-result-btn').addEventListener('click', () => {
        exportResult(resultId);
    });
    
    // Remove modal from DOM when hidden
    $(modal).on('hidden.bs.modal', () => {
        document.body.removeChild(modal);
    });
}

/**
 * Export a result to a file
 * @param {string} resultId - The ID of the result to export
 */
async function exportResult(resultId) {
    try {
        const response = await fetch(`/api/research-flows/${flowId}/results/${resultId}/export`);
        
        if (!response.ok) {
            throw new Error(`Failed to export result: ${response.statusText}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        // Create a temporary link and trigger download
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `result-${resultId}.json`;
        document.body.appendChild(a);
        a.click();
        
        // Clean up
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showSuccessMessage('Result exported successfully');
    } catch (error) {
        showErrorMessage(`Error: ${error.message}`);
        console.error('Error exporting result:', error);
    }
}

/**
 * Set up WebSocket connection for real-time updates
 */
function setupWebSocketConnection() {
    // Check if WebSocket is supported
    if (!window.WebSocket) {
        console.warn('WebSocket is not supported by your browser. Falling back to polling.');
        return;
    }
    
    try {
        // Create WebSocket connection
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/research-flows/${flowId}`;
        const socket = new WebSocket(wsUrl);
        
        // Connection opened
        socket.addEventListener('open', (event) => {
            console.log('WebSocket connection established');
            
            // If WebSocket is working, we can reduce polling frequency or disable it
            clearInterval(updateInterval);
            updateInterval = setInterval(fetchFlowData, 10000); // Reduce to every 10 seconds as backup
        });
        
        // Listen for messages
        socket.addEventListener('message', (event) => {
            try {
                const data = JSON.parse(event.data);
                
                // Update flow data with the received data
                flowData = data;
                
                // Update the UI
                updateFlowDetails();
                updateTaskList();
                updateFlowResults();
                updateFlowLogs();
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
            }
        });
        
        // Connection closed
        socket.addEventListener('close', (event) => {
            console.log('WebSocket connection closed');
            
            // Restore normal polling frequency
            clearInterval(updateInterval);
            updateInterval = setInterval(fetchFlowData, UPDATE_INTERVAL_MS);
        });
        
        // Connection error
        socket.addEventListener('error', (event) => {
            console.error('WebSocket error:', event);
            
            // Restore normal polling frequency
            clearInterval(updateInterval);
            updateInterval = setInterval(fetchFlowData, UPDATE_INTERVAL_MS);
        });
    } catch (error) {
        console.error('Error setting up WebSocket:', error);
    }
}

/**
 * Show an error message
 * @param {string} message - The error message to display
 */
function showErrorMessage(message) {
    errorMessageElement.textContent = message;
    errorMessageElement.style.display = 'block';
    
    // Hide the message after 5 seconds
    setTimeout(() => {
        hideErrorMessage();
    }, 5000);
}

/**
 * Hide the error message
 */
function hideErrorMessage() {
    errorMessageElement.style.display = 'none';
}

/**
 * Show a success message
 * @param {string} message - The success message to display
 */
function showSuccessMessage(message) {
    // Create a success message element if it doesn't exist
    let successMessageElement = document.getElementById('success-message');
    
    if (!successMessageElement) {
        successMessageElement = document.createElement('div');
        successMessageElement.id = 'success-message';
        successMessageElement.className = 'alert alert-success';
        document.querySelector('.container').prepend(successMessageElement);
    }
    
    successMessageElement.textContent = message;
    successMessageElement.style.display = 'block';
    
    // Hide the message after 3 seconds
    setTimeout(() => {
        successMessageElement.style.display = 'none';
    }, 3000);
}

// Initialize the detail view when the DOM is loaded
document.addEventListener('DOMContentLoaded', initDetailView);

// Clean up when leaving the page
window.addEventListener('beforeunload', () => {
    // Clear the update interval
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});
