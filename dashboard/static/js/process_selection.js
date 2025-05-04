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
            
            // Hide the process selection modal
            const modal = bootstrap.Modal.getInstance(processSelectionModal);
            modal.hide();
            
            // Redirect to the appropriate configuration dialog
            switch(sourceType) {
                case 'github':
                    openGithubConfigDialog();
                    break;
                case 'websearch':
                    openWebsearchConfigDialog();
                    break;
                case 'youtube':
                    openYoutubeConfigDialog();
                    break;
                case 'arxiv':
                    openArxivConfigDialog();
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
            // Show help information
            alert('Select a data source to begin mining information. Each source has different configuration options tailored to that specific type of content.');
        });
    }
    
    // Function to open GitHub configuration dialog
    function openGithubConfigDialog() {
        // Load the GitHub configuration dialog via AJAX or redirect
        window.location.href = '/data-mining/github-config';
    }
    
    // Function to open WebSearch configuration dialog
    function openWebsearchConfigDialog() {
        // Load the WebSearch configuration dialog via AJAX or redirect
        window.location.href = '/data-mining/websearch-config';
    }
    
    // Function to open YouTube configuration dialog
    function openYoutubeConfigDialog() {
        // Load the YouTube configuration dialog via AJAX or redirect
        window.location.href = '/data-mining/youtube-config';
    }
    
    // Function to open ArXiv configuration dialog
    function openArxivConfigDialog() {
        // Load the ArXiv configuration dialog via AJAX or redirect
        window.location.href = '/data-mining/arxiv-config';
    }
});

// Add event listeners for the dashboard active mining table
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
            filterDropdown.innerHTML = `Filter: ${filterValue.charAt(0).toUpperCase() + filterValue.slice(1)} <i class="bi bi-funnel"></i>`;
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
            sortDropdown.innerHTML = `Sort By: ${sortValue.charAt(0).toUpperCase() + sortValue.slice(1)} <i class="bi bi-sort-down"></i>`;
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
    const tableBody = document.querySelector('#active-mining-table tbody');
    if (!tableBody) return;
    
    // Sample data - in a real application, this would come from an API
    const sampleData = [
        { id: 1, source: 'GitHub', focus: 'Python Agentic RAG', runtime: '2h 37min', progress: 85 },
        { id: 2, source: 'GitHub', focus: 'Database For Data Mining', runtime: '14h 37min', progress: 92 },
        { id: 3, source: 'WebSearch', focus: 'Best Ways to create codebase RAG', runtime: '1h 15min', progress: 78 },
        { id: 4, source: 'YouTube', focus: 'AI Agent Frameworks', runtime: '5h 12min', progress: 45 },
        { id: 5, source: 'ArXiv', focus: 'Vector Databases', runtime: '8h 03min', progress: 63 },
        { id: 6, source: 'ArXiv', focus: 'Vector implementations', runtime: '12h 03min', progress: 63 }
    ];
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // Add sample data rows
    sampleData.forEach(item => {
        const row = document.createElement('tr');
        
        // Create table cells
        row.innerHTML = `
            <td>${item.id}</td>
            <td>${item.source}</td>
            <td>${item.focus}</td>
            <td>${item.runtime}</td>
            <td>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar" role="progressbar" style="width: ${item.progress}%;" 
                         aria-valuenow="${item.progress}" aria-valuemin="0" aria-valuemax="100">
                        ${item.progress}%
                    </div>
                </div>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary" data-action="view" data-id="${item.id}">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button type="button" class="btn btn-outline-secondary" data-action="pause" data-id="${item.id}">
                        <i class="bi bi-pause-fill"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger" data-action="stop" data-id="${item.id}">
                        <i class="bi bi-stop-fill"></i>
                    </button>
                </div>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Add action button event listeners
    addActionButtonListeners();
}

// Function to refresh the active mining table
function refreshActiveMiningTable() {
    // In a real application, this would fetch fresh data from an API
    // For now, we'll just re-initialize with the same sample data
    initializeActiveMiningTable();
    
    // Show a toast or notification
    showNotification('Table refreshed successfully');
}

// Function to filter the active mining table
function filterActiveMiningTable(filterValue) {
    const tableRows = document.querySelectorAll('#active-mining-table tbody tr');
    
    tableRows.forEach(row => {
        const sourceCell = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        
        if (filterValue === 'all' || sourceCell.includes(filterValue.toLowerCase())) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
    
    showNotification(`Filtered by: ${filterValue}`);
}

// Function to sort the active mining table
function sortActiveMiningTable(sortValue) {
    const tableBody = document.querySelector('#active-mining-table tbody');
    const tableRows = Array.from(tableBody.querySelectorAll('tr'));
    
    // Define column index based on sort value
    let columnIndex;
    switch(sortValue) {
        case 'source':
            columnIndex = 1;
            break;
        case 'focus':
            columnIndex = 2;
            break;
        case 'runtime':
            columnIndex = 3;
            break;
        case 'progress':
            columnIndex = 4;
            break;
        default:
            columnIndex = 0;
    }
    
    // Sort the rows
    tableRows.sort((a, b) => {
        let aValue, bValue;
        
        if (sortValue === 'progress') {
            // Extract progress percentage for sorting
            aValue = parseInt(a.querySelector('.progress-bar').getAttribute('aria-valuenow'));
            bValue = parseInt(b.querySelector('.progress-bar').getAttribute('aria-valuenow'));
        } else {
            aValue = a.querySelector(`td:nth-child(${columnIndex + 1})`).textContent;
            bValue = b.querySelector(`td:nth-child(${columnIndex + 1})`).textContent;
        }
        
        return aValue > bValue ? 1 : -1;
    });
    
    // Clear and re-append sorted rows
    tableBody.innerHTML = '';
    tableRows.forEach(row => tableBody.appendChild(row));
    
    // Re-add action button listeners
    addActionButtonListeners();
    
    showNotification(`Sorted by: ${sortValue}`);
}

// Function to export active mining data
function exportActiveMiningData() {
    // In a real application, this would generate a CSV or JSON file
    showNotification('Exporting data...');
    
    // Simulate download after a short delay
    setTimeout(() => {
        showNotification('Data exported successfully');
    }, 1000);
}

// Function to add event listeners to action buttons
function addActionButtonListeners() {
    const actionButtons = document.querySelectorAll('[data-action]');
    
    actionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            const id = this.getAttribute('data-id');
            
            switch(action) {
                case 'view':
                    viewMiningProcess(id);
                    break;
                case 'pause':
                    pauseMiningProcess(id);
                    break;
                case 'stop':
                    stopMiningProcess(id);
                    break;
            }
        });
    });
}

// Function to view a mining process
function viewMiningProcess(id) {
    showNotification(`Viewing process #${id}`);
    // In a real application, this would open a detailed view
}

// Function to pause a mining process
function pauseMiningProcess(id) {
    showNotification(`Paused process #${id}`);
    // In a real application, this would send a pause command to the server
}

// Function to stop a mining process
function stopMiningProcess(id) {
    if (confirm(`Are you sure you want to stop process #${id}?`)) {
        showNotification(`Stopped process #${id}`);
        // In a real application, this would send a stop command to the server
    }
}

// Function to show a notification
function showNotification(message) {
    // Create a toast notification
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-primary border-0';
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
    
    // Add to the document
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.appendChild(toast);
    document.body.appendChild(toastContainer);
    
    // Initialize and show the toast
    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
    bsToast.show();
    
    // Remove from DOM after hiding
    toast.addEventListener('hidden.bs.toast', function() {
        toastContainer.remove();
    });
}

