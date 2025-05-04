/**
 * Process Selection Dialog Handler
 * Manages the process selection dialog and redirects to appropriate configuration dialogs
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get the process selection modal element
    const processSelectionModal = document.getElementById('process-selection-modal');
    
    // Get all data source cards
    const dataSourceCards = document.querySelectorAll('.data-source-card');
    
    // Add click event listeners to each data source card
    dataSourceCards.forEach(card => {
        card.addEventListener('click', function() {
            // Get the data source type
            const sourceType = this.getAttribute('data-source');
            
            // Redirect to the appropriate configuration dialog
            switch(sourceType) {
                case 'github':
                    window.location.href = '/github-config';
                    break;
                case 'websearch':
                    window.location.href = '/websearch-config';
                    break;
                case 'youtube':
                    window.location.href = '/youtube-config';
                    break;
                case 'arxiv':
                    window.location.href = '/arxiv-config';
                    break;
                default:
                    console.error('Unknown data source type:', sourceType);
            }
        });
        
        // Add hover effect
        card.addEventListener('mouseenter', function() {
            this.classList.add('data-source-card-hover');
        });
        
        card.addEventListener('mouseleave', function() {
            this.classList.remove('data-source-card-hover');
        });
    });
    
    // Help button handler
    const helpButton = document.getElementById('help-btn');
    if (helpButton) {
        helpButton.addEventListener('click', function() {
            // Show help modal
            const helpModal = new bootstrap.Modal(document.getElementById('help-modal'));
            helpModal.show();
        });
    }
    
    // Cancel button handler
    const cancelButton = document.getElementById('cancel-btn');
    if (cancelButton) {
        cancelButton.addEventListener('click', function() {
            window.location.href = '/data-mining';
        });
    }
});

// Add event listeners for the active mining table
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the active mining table
    initializeActiveMiningTable();
    
    // Refresh button handler
    const refreshButton = document.getElementById('refresh-btn');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            refreshActiveMiningTable();
        });
    }
    
    // Filter dropdown handlers
    const filterLinks = document.querySelectorAll('[data-filter]');
    filterLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const filterValue = this.getAttribute('data-filter');
            filterActiveMiningTable(filterValue);
            
            // Update dropdown button text
            const filterDropdown = document.getElementById('filter-dropdown');
            if (filterDropdown) {
                filterDropdown.innerHTML = `Filter: ${filterValue.charAt(0).toUpperCase() + filterValue.slice(1)} <i class="bi bi-funnel"></i>`;
            }
        });
    });
    
    // Sort dropdown handlers
    const sortLinks = document.querySelectorAll('[data-sort]');
    sortLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const sortValue = this.getAttribute('data-sort');
            sortActiveMiningTable(sortValue);
            
            // Update dropdown button text
            const sortDropdown = document.getElementById('sort-dropdown');
            if (sortDropdown) {
                sortDropdown.innerHTML = `Sort By: ${sortValue.charAt(0).toUpperCase() + sortValue.slice(1)} <i class="bi bi-sort-down"></i>`;
            }
        });
    });
    
    // Export button handler
    const exportButton = document.getElementById('export-btn');
    if (exportButton) {
        exportButton.addEventListener('click', function() {
            exportActiveMiningData();
        });
    }
});

// Function to initialize the active mining table with sample data
function initializeActiveMiningTable() {
    // In a real application, this would fetch data from an API
    console.log('Initializing active mining table');
    
    // Add event listeners to action buttons
    document.querySelectorAll('#active-mining-table button').forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            
            const row = this.closest('tr');
            const taskId = row.getAttribute('data-task-id');
            
            if (this.classList.contains('btn-outline-secondary')) {
                // Pause/Resume button
                toggleTaskStatus(taskId);
            } else if (this.classList.contains('btn-outline-danger')) {
                // Stop button
                stopTask(taskId);
            }
        });
    });
}

// Function to refresh the active mining table
function refreshActiveMiningTable() {
    console.log('Refreshing active mining table');
    
    // In a real application, this would fetch updated data from an API
    // For now, just show a loading indicator and then restore the table
    
    const tableBody = document.querySelector('#active-mining-table tbody');
    if (!tableBody) return;
    
    // Show loading indicator
    const originalContent = tableBody.innerHTML;
    tableBody.innerHTML = `
        <tr>
            <td colspan="5" class="text-center py-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Refreshing data...</p>
            </td>
        </tr>
    `;
    
    // Simulate API call delay
    setTimeout(() => {
        tableBody.innerHTML = originalContent;
        
        // Re-add event listeners
        document.querySelectorAll('#active-mining-table button').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                
                const row = this.closest('tr');
                const taskId = row.getAttribute('data-task-id');
                
                if (this.classList.contains('btn-outline-secondary')) {
                    // Pause/Resume button
                    toggleTaskStatus(taskId);
                } else if (this.classList.contains('btn-outline-danger')) {
                    // Stop button
                    stopTask(taskId);
                }
            });
        });
        
        // Show toast notification
        showToast('Data refreshed successfully');
    }, 1000);
}

// Function to filter the active mining table
function filterActiveMiningTable(filterValue) {
    console.log('Filtering table by:', filterValue);
    
    // In a real application, this would filter the table based on the selected value
    // For now, just log the filter value
}

// Function to sort the active mining table
function sortActiveMiningTable(sortValue) {
    console.log('Sorting table by:', sortValue);
    
    // In a real application, this would sort the table based on the selected value
    // For now, just log the sort value
}

// Function to export active mining data
function exportActiveMiningData() {
    console.log('Exporting active mining data');
    
    // In a real application, this would export the data to a file
    // For now, just show a toast notification
    showToast('Data exported successfully');
}

// Function to toggle task status (pause/resume)
function toggleTaskStatus(taskId) {
    console.log('Toggling status for task:', taskId);
    
    // In a real application, this would call an API to pause/resume the task
    // For now, just log the task ID
}

// Function to stop a task
function stopTask(taskId) {
    console.log('Stopping task:', taskId);
    
    // In a real application, this would call an API to stop the task
    // For now, just log the task ID
}

// Function to show a toast notification
function showToast(message, type = 'success') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'primary' : 'danger'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
    bsToast.show();
    
    // Remove from DOM after hiding
    toast.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

