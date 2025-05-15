/**
 * Parallel Research Dashboard JavaScript
 * Handles the main dashboard view for parallel research flows
 */

// Global variables
let researchFlows = [];
let statusChart = null;
let currentFilter = 'all';
let pollingInterval = null;
const POLLING_INTERVAL_MS = 5000; // 5 seconds

// DOM elements
const researchFlowsList = document.getElementById('research-flows-list');
const totalFlowsElement = document.getElementById('total-flows');
const activeFlowsElement = document.getElementById('active-flows');
const completedFlowsElement = document.getElementById('completed-flows');
const failedFlowsElement = document.getElementById('failed-flows');
const recentActivityList = document.getElementById('recent-activity-list');
const flowActionModal = document.getElementById('flow-action-modal');
const flowActionModalLabel = document.getElementById('flow-action-modal-label');
const flowActionModalBody = document.getElementById('flow-action-modal-body');
const flowActionConfirmBtn = document.getElementById('flow-action-confirm');
const toastNotification = document.getElementById('toast-notification');
const toastTitle = document.getElementById('toast-title');
const toastMessage = document.getElementById('toast-message');

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
    setupEventListeners();
    startPolling();
});

/**
 * Initialize the dashboard
 */
function initializeDashboard() {
    loadResearchFlows();
    initializeStatusChart();
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Filter buttons
    document.querySelectorAll('[data-filter]').forEach(button => {
        button.addEventListener('click', (e) => {
            const filter = e.target.getAttribute('data-filter');
            setActiveFilter(filter);
            filterResearchFlows(filter);
        });
    });

    // Modal confirm button
    flowActionConfirmBtn.addEventListener('click', handleFlowActionConfirm);

    // When modal is hidden, clear any stored data
    flowActionModal.addEventListener('hidden.bs.modal', () => {
        flowActionConfirmBtn.removeAttribute('data-flow-id');
        flowActionConfirmBtn.removeAttribute('data-action');
    });
}

/**
 * Start polling for updates
 */
function startPolling() {
    // Clear any existing interval
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }

    // Set up new polling interval
    pollingInterval = setInterval(() => {
        loadResearchFlows();
    }, POLLING_INTERVAL_MS);
}

/**
 * Load research flows from the API
 */
function loadResearchFlows() {
    // Show loading state
    if (researchFlowsList.querySelector('.placeholder-row')) {
        researchFlowsList.querySelector('.placeholder-row td').textContent = 'Loading research flows...';
    }

    // Fetch research flows from the API
    fetch('/research-flows')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load research flows');
            }
            return response.json();
        })
        .then(data => {
            researchFlows = data;
            renderResearchFlows();
            updateStatistics();
            updateRecentActivity();
            updateStatusChart();
        })
        .catch(error => {
            console.error('Error loading research flows:', error);
            showToast('Error', 'Failed to load research flows. Please try again.', 'error');
            
            // Show error message in the table
            if (researchFlowsList.querySelector('.placeholder-row')) {
                researchFlowsList.querySelector('.placeholder-row td').textContent = 'Error loading research flows. Please try again.';
            } else {
                researchFlowsList.innerHTML = `
                    <tr class="placeholder-row">
                        <td colspan="6" class="text-center text-danger">Error loading research flows. Please try again.</td>
                    </tr>
                `;
            }
        });
}

/**
 * Render research flows in the table
 */
function renderResearchFlows() {
    // Filter flows based on current filter
    const filteredFlows = filterResearchFlows(currentFilter, false);
    
    // Clear the table
    researchFlowsList.innerHTML = '';
    
    // If no flows, show message
    if (filteredFlows.length === 0) {
        researchFlowsList.innerHTML = `
            <tr class="placeholder-row">
                <td colspan="6" class="text-center">No research flows found. Create a new flow to get started.</td>
            </tr>
        `;
        return;
    }
    
    // Render each flow
    filteredFlows.forEach(flow => {
        const row = document.createElement('tr');
        row.setAttribute('data-flow-id', flow.flow_id);
        row.setAttribute('data-status', flow.status);
        
        // Calculate task statistics
        const totalTasks = flow.tasks.length;
        const completedTasks = flow.tasks.filter(task => task.status === 'completed').length;
        const failedTasks = flow.tasks.filter(task => task.status === 'failed').length;
        
        // Format dates
        const createdDate = new Date(flow.created_at);
        const formattedDate = createdDate.toLocaleDateString() + ' ' + createdDate.toLocaleTimeString();
        
        // Create the row content
        row.innerHTML = `
            <td>
                <a href="/dashboard/parallel-research/${flow.flow_id}" class="fw-bold">${flow.name}</a>
                <div class="small text-muted">${flow.description || 'No description'}</div>
            </td>
            <td>
                <span class="badge status-${flow.status}">${capitalizeFirstLetter(flow.status)}</span>
            </td>
            <td>
                <div class="progress" style="height: 10px;">
                    <div class="progress-bar ${flow.status === 'failed' ? 'bg-danger' : ''}" 
                         role="progressbar" 
                         style="width: ${Math.round(flow.progress * 100)}%;" 
                         aria-valuenow="${Math.round(flow.progress * 100)}" 
                         aria-valuemin="0" 
                         aria-valuemax="100"></div>
                </div>
                <div class="small text-center mt-1">${Math.round(flow.progress * 100)}%</div>
            </td>
            <td>
                <div>${completedTasks} of ${totalTasks} completed</div>
                ${failedTasks > 0 ? `<div class="small text-danger">${failedTasks} failed</div>` : ''}
            </td>
            <td>${formattedDate}</td>
            <td>
                <div class="btn-group">
                    <button type="button" class="btn btn-sm btn-outline-primary view-flow-btn" data-flow-id="${flow.flow_id}">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary flow-actions-btn" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="bi bi-three-dots"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end">
                        ${getFlowActionMenuItems(flow)}
                    </ul>
                </div>
            </td>
        `;
        
        researchFlowsList.appendChild(row);
    });
    
    // Add event listeners to the buttons
    addFlowActionEventListeners();
}

/**
 * Get the dropdown menu items for a flow based on its status
 */
function getFlowActionMenuItems(flow) {
    let items = `
        <li><a class="dropdown-item view-flow-btn" href="/dashboard/parallel-research/${flow.flow_id}">View Details</a></li>
    `;
    
    // Add status-specific actions
    switch (flow.status) {
        case 'pending':
            items += `
                <li><a class="dropdown-item start-flow-btn" href="#" data-flow-id="${flow.flow_id}">Start Flow</a></li>
            `;
            break;
        case 'running':
            items += `
                <li><a class="dropdown-item pause-flow-btn" href="#" data-flow-id="${flow.flow_id}">Pause Flow</a></li>
                <li><a class="dropdown-item cancel-flow-btn" href="#" data-flow-id="${flow.flow_id}">Cancel Flow</a></li>
            `;
            break;
        case 'paused':
            items += `
                <li><a class="dropdown-item resume-flow-btn" href="#" data-flow-id="${flow.flow_id}">Resume Flow</a></li>
                <li><a class="dropdown-item cancel-flow-btn" href="#" data-flow-id="${flow.flow_id}">Cancel Flow</a></li>
            `;
            break;
    }
    
    // Add delete option for all flows
    items += `
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item delete-flow-btn text-danger" href="#" data-flow-id="${flow.flow_id}">Delete Flow</a></li>
    `;
    
    return items;
}

/**
 * Add event listeners to flow action buttons
 */
function addFlowActionEventListeners() {
    // View flow buttons
    document.querySelectorAll('.view-flow-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            if (e.currentTarget.tagName === 'A') return; // Let the link handle navigation
            
            const flowId = e.currentTarget.getAttribute('data-flow-id');
            window.location.href = `/dashboard/parallel-research/${flowId}`;
        });
    });
    
    // Start flow buttons
    document.querySelectorAll('.start-flow-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const flowId = e.currentTarget.getAttribute('data-flow-id');
            showFlowActionModal('Start Research Flow', 'Are you sure you want to start this research flow?', 'start', flowId);
        });
    });
    
    // Pause flow buttons
    document.querySelectorAll('.pause-flow-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const flowId = e.currentTarget.getAttribute('data-flow-id');
            showFlowActionModal('Pause Research Flow', 'Are you sure you want to pause this research flow?', 'pause', flowId);
        });
    });
    
    // Resume flow buttons
    document.querySelectorAll('.resume-flow-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const flowId = e.currentTarget.getAttribute('data-flow-id');
            showFlowActionModal('Resume Research Flow', 'Are you sure you want to resume this research flow?', 'resume', flowId);
        });
    });
    
    // Cancel flow buttons
    document.querySelectorAll('.cancel-flow-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const flowId = e.currentTarget.getAttribute('data-flow-id');
            showFlowActionModal('Cancel Research Flow', 'Are you sure you want to cancel this research flow? This action cannot be undone.', 'cancel', flowId);
        });
    });
    
    // Delete flow buttons
    document.querySelectorAll('.delete-flow-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const flowId = e.currentTarget.getAttribute('data-flow-id');
            showFlowActionModal('Delete Research Flow', 'Are you sure you want to delete this research flow? This action cannot be undone and all data will be lost.', 'delete', flowId);
        });
    });
}

/**
 * Show the flow action confirmation modal
 */
function showFlowActionModal(title, message, action, flowId) {
    flowActionModalLabel.textContent = title;
    flowActionModalBody.textContent = message;
    flowActionConfirmBtn.setAttribute('data-flow-id', flowId);
    flowActionConfirmBtn.setAttribute('data-action', action);
    
    // Show the modal
    const modal = new bootstrap.Modal(flowActionModal);
    modal.show();
}

/**
 * Handle flow action confirmation
 */
function handleFlowActionConfirm() {
    const flowId = flowActionConfirmBtn.getAttribute('data-flow-id');
    const action = flowActionConfirmBtn.getAttribute('data-action');
    
    if (!flowId || !action) {
        console.error('Missing flow ID or action');
        return;
    }
    
    // Hide the modal
    const modal = bootstrap.Modal.getInstance(flowActionModal);
    modal.hide();
    
    // Perform the action
    switch (action) {
        case 'start':
            startFlow(flowId);
            break;
        case 'pause':
            pauseFlow(flowId);
            break;
        case 'resume':
            resumeFlow(flowId);
            break;
        case 'cancel':
            cancelFlow(flowId);
            break;
        case 'delete':
            deleteFlow(flowId);
            break;
        default:
            console.error('Unknown action:', action);
    }
}

/**
 * Start a research flow
 */
function startFlow(flowId) {
    fetch(`/research-flows/${flowId}/start`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to start research flow');
        }
        return response.json();
    })
    .then(data => {
        showToast('Success', 'Research flow started successfully', 'success');
        loadResearchFlows(); // Reload the flows
    })
    .catch(error => {
        console.error('Error starting research flow:', error);
        showToast('Error', 'Failed to start research flow. Please try again.', 'error');
    });
}

/**
 * Pause a research flow
 */
function pauseFlow(flowId) {
    fetch(`/research-flows/${flowId}/pause`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to pause research flow');
        }
        return response.json();
    })
    .then(data => {
        showToast('Success', 'Research flow paused successfully', 'success');
        loadResearchFlows(); // Reload the flows
    })
    .catch(error => {
        console.error('Error pausing research flow:', error);
        showToast('Error', 'Failed to pause research flow. Please try again.', 'error');
    });
}

/**
 * Resume a research flow
 */
function resumeFlow(flowId) {
    fetch(`/research-flows/${flowId}/resume`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to resume research flow');
        }
        return response.json();
    })
    .then(data => {
        showToast('Success', 'Research flow resumed successfully', 'success');
        loadResearchFlows(); // Reload the flows
    })
    .catch(error => {
        console.error('Error resuming research flow:', error);
        showToast('Error', 'Failed to resume research flow. Please try again.', 'error');
    });
}

/**
 * Cancel a research flow
 */
function cancelFlow(flowId) {
    fetch(`/research-flows/${flowId}/cancel`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to cancel research flow');
        }
        return response.json();
    })
    .then(data => {
        showToast('Success', 'Research flow cancelled successfully', 'success');
        loadResearchFlows(); // Reload the flows
    })
    .catch(error => {
        console.error('Error cancelling research flow:', error);
        showToast('Error', 'Failed to cancel research flow. Please try again.', 'error');
    });
}

/**
 * Delete a research flow
 */
function deleteFlow(flowId) {
    fetch(`/research-flows/${flowId}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to delete research flow');
        }
        return response.json();
    })
    .then(data => {
        showToast('Success', 'Research flow deleted successfully', 'success');
        loadResearchFlows(); // Reload the flows
    })
    .catch(error => {
        console.error('Error deleting research flow:', error);
        showToast('Error', 'Failed to delete research flow. Please try again.', 'error');
    });
}

/**
 * Filter research flows based on status
 */
function filterResearchFlows(filter, updateUI = true) {
    if (updateUI) {
        currentFilter = filter;
        setActiveFilter(filter);
    }
    
    let filteredFlows;
    
    switch (filter) {
        case 'running':
            filteredFlows = researchFlows.filter(flow => flow.status === 'running');
            break;
        case 'pending':
            filteredFlows = researchFlows.filter(flow => flow.status === 'pending');
            break;
        case 'completed':
            filteredFlows = researchFlows.filter(flow => flow.status === 'completed');
            break;
        case 'failed':
            filteredFlows = researchFlows.filter(flow => flow.status === 'failed');
            break;
        default:
            filteredFlows = [...researchFlows];
    }
    
    if (updateUI) {
        renderResearchFlows();
    }
    
    return filteredFlows;
}

/**
 * Set the active filter button
 */
function setActiveFilter(filter) {
    document.querySelectorAll('[data-filter]').forEach(button => {
        if (button.getAttribute('data-filter') === filter) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
}

/**
 * Update dashboard statistics
 */
function updateStatistics() {
    const totalFlows = researchFlows.length;
    const activeFlows = researchFlows.filter(flow => flow.status === 'running' || flow.status === 'paused').length;
    const completedFlows = researchFlows.filter(flow => flow.status === 'completed').length;
    const failedFlows = researchFlows.filter(flow => flow.status === 'failed').length;
    
    totalFlowsElement.textContent = totalFlows;
    activeFlowsElement.textContent = activeFlows;
    completedFlowsElement.textContent = completedFlows;
    failedFlowsElement.textContent = failedFlows;
}

/**
 * Update recent activity list
 */
function updateRecentActivity() {
    // Sort flows by updated_at (most recent first)
    const sortedFlows = [...researchFlows].sort((a, b) => {
        return new Date(b.updated_at) - new Date(a.updated_at);
    });
    
    // Take the 5 most recent
    const recentFlows = sortedFlows.slice(0, 5);
    
    // Clear the list
    recentActivityList.innerHTML = '';
    
    // If no recent activity, show message
    if (recentFlows.length === 0) {
        recentActivityList.innerHTML = `
            <li class="list-group-item text-center">No recent activity</li>
        `;
        return;
    }
    
    // Render each activity item
    recentFlows.forEach(flow => {
        const updatedDate = new Date(flow.updated_at);
        const formattedDate = updatedDate.toLocaleDateString() + ' ' + updatedDate.toLocaleTimeString();
        
        const activityItem = document.createElement('li');
        activityItem.className = `list-group-item activity-${flow.status}`;
        
        let activityText = '';
        switch (flow.status) {
            case 'running':
                activityText = 'started running';
                break;
            case 'completed':
                activityText = 'completed successfully';
                break;
            case 'failed':
                activityText = 'failed';
                break;
            case 'paused':
                activityText = 'was paused';
                break;
            case 'cancelled':
                activityText = 'was cancelled';
                break;
            default:
                activityText = 'was updated';
        }
        
        activityItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${flow.name}</strong> ${activityText}
                </div>
                <span class="badge status-${flow.status}">${capitalizeFirstLetter(flow.status)}</span>
            </div>
            <div class="activity-timestamp">${formattedDate}</div>
        `;
        
        recentActivityList.appendChild(activityItem);
    });
}

/**
 * Initialize the status chart
 */
function initializeStatusChart() {
    const ctx = document.getElementById('flow-status-chart').getContext('2d');
    
    statusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Pending', 'Running', 'Completed', 'Failed', 'Paused', 'Cancelled'],
            datasets: [{
                data: [0, 0, 0, 0, 0, 0],
                backgroundColor: [
                    '#6c757d', // Pending - gray
                    '#0d6efd', // Running - blue
                    '#198754', // Completed - green
                    '#dc3545', // Failed - red
                    '#fd7e14', // Paused - orange
                    '#6c757d'  // Cancelled - gray
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

/**
 * Update the status chart
 */
function updateStatusChart() {
    if (!statusChart) return;
    
    const pending = researchFlows.filter(flow => flow.status === 'pending').length;
    const running = researchFlows.filter(flow => flow.status === 'running').length;
    const completed = researchFlows.filter(flow => flow.status === 'completed').length;
    const failed = researchFlows.filter(flow => flow.status === 'failed').length;
    const paused = researchFlows.filter(flow => flow.status === 'paused').length;
    const cancelled = researchFlows.filter(flow => flow.status === 'cancelled').length;
    
    statusChart.data.datasets[0].data = [pending, running, completed, failed, paused, cancelled];
    statusChart.update();
}

/**
 * Show a toast notification
 */
function showToast(title, message, type = 'info') {
    toastTitle.textContent = title;
    toastMessage.textContent = message;
    
    // Set toast color based on type
    toastNotification.className = 'toast';
    switch (type) {
        case 'success':
            toastNotification.classList.add('bg-success', 'text-white');
            break;
        case 'error':
            toastNotification.classList.add('bg-danger', 'text-white');
            break;
        case 'warning':
            toastNotification.classList.add('bg-warning');
            break;
        default:
            toastNotification.classList.add('bg-info', 'text-white');
    }
    
    // Show the toast
    const toast = new bootstrap.Toast(toastNotification);
    toast.show();
}

/**
 * Capitalize the first letter of a string
 */
function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

// Clean up when leaving the page
window.addEventListener('beforeunload', () => {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
});

