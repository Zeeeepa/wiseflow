// Data Mining Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the dashboard
    initDashboard();
    
    // Load active data mining tasks
    loadDataMiningTasks();
    
    // Set up event listeners
    setupEventListeners();
});

// Initialize the dashboard
function initDashboard() {
    console.log('Initializing Data Mining Dashboard...');
}

// Load active data mining tasks
function loadDataMiningTasks() {
    const tasksContainer = document.getElementById('data-mining-tasks');
    
    // Show loading indicator
    tasksContainer.innerHTML = `
        <tr>
            <td colspan="5" class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading data mining tasks...</p>
            </td>
        </tr>
    `;
    
    // In a real application, this would fetch data from the API
    // For now, we'll use mock data to match the UI mockup
    setTimeout(() => {
        // Mock data for demonstration
        const mockTasks = [
            {
                id: 1,
                name: 'Python Agentic RAG',
                source: 'GitHub',
                runtime: '2h 37min',
                progress: 85,
                status: 'active'
            },
            {
                id: 2,
                name: 'Database For Data Mining',
                source: 'GitHub',
                runtime: '14h 37min',
                progress: 92,
                status: 'active'
            },
            {
                id: 3,
                name: 'Best Ways to create codebase RAG',
                source: 'WebResearch',
                runtime: '5h 12min',
                progress: 78,
                status: 'active'
            },
            {
                id: 4,
                name: 'AI Agent Frameworks',
                source: 'YouTube',
                runtime: '5h 12min',
                progress: 45,
                status: 'active'
            },
            {
                id: 5,
                name: 'Vector Databases',
                source: 'ArXiv',
                runtime: '8h 03min',
                progress: 63,
                status: 'active'
            },
            {
                id: 6,
                name: 'Vector implementations',
                source: 'ArXiv',
                runtime: '12h 03min',
                progress: 63,
                status: 'active'
            }
        ];
        
        displayDataMiningTasks(mockTasks);
    }, 1000);
    
    // In a real application, you would fetch the data from the API like this:
    /*
    fetch('/api/data-mining/tasks')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.tasks) {
                displayDataMiningTasks(data.tasks);
            } else {
                tasksContainer.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center py-4">
                            <p>No data mining tasks found.</p>
                            <button class="btn btn-primary mt-2" data-bs-toggle="modal" data-bs-target="#newDataMiningModal">
                                <i class="bi bi-plus-lg"></i> Create New Task
                            </button>
                        </td>
                    </tr>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading data mining tasks:', error);
            tasksContainer.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-4">
                        <div class="alert alert-danger" role="alert">
                            <i class="bi bi-exclamation-triangle-fill me-2"></i>
                            Error loading tasks. Please try again.
                        </div>
                        <button class="btn btn-outline-primary mt-2" id="retry-load-btn">
                            <i class="bi bi-arrow-clockwise"></i> Retry
                        </button>
                    </td>
                </tr>
            `;
            
            // Add event listener to retry button
            document.getElementById('retry-load-btn').addEventListener('click', loadDataMiningTasks);
        });
    */
}

// Display data mining tasks
function displayDataMiningTasks(tasks) {
    const tasksContainer = document.getElementById('data-mining-tasks');
    
    // Clear existing content
    tasksContainer.innerHTML = '';
    
    // Add each task to the table
    tasks.forEach((task, index) => {
        const row = document.createElement('tr');
        row.className = 'task-row';
        row.setAttribute('data-task-id', task.id);
        row.setAttribute('data-source', task.source.toLowerCase());
        row.setAttribute('data-progress', task.progress);
        row.setAttribute('data-status', task.status);
        
        // Get source icon
        const sourceIcon = getSourceIcon(task.source);
        
        // Create progress bar
        const progressClass = getProgressClass(task.progress);
        
        row.innerHTML = `
            <td>
                <span class="fw-medium">${index + 1}. ${task.name}</span>
            </td>
            <td>
                <span class="badge bg-light text-dark">
                    <i class="${sourceIcon} me-1"></i> ${task.source}
                </span>
            </td>
            <td>${task.runtime}</td>
            <td>
                <div class="progress" style="height: 8px;">
                    <div class="progress-bar ${progressClass}" role="progressbar" style="width: ${task.progress}%;" 
                        aria-valuenow="${task.progress}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
                <span class="small">${task.progress}%</span>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary view-task-btn" data-task-id="${task.id}">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-outline-secondary pause-task-btn" data-task-id="${task.id}">
                        <i class="bi bi-pause-fill"></i>
                    </button>
                    <button class="btn btn-outline-danger stop-task-btn" data-task-id="${task.id}">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
            </td>
        `;
        
        tasksContainer.appendChild(row);
    });
    
    // Add event listeners to the task action buttons
    addTaskButtonEventListeners();
}

// Get source icon based on source type
function getSourceIcon(source) {
    switch(source.toLowerCase()) {
        case 'github':
            return 'bi bi-github';
        case 'webresearch':
        case 'web':
            return 'bi bi-globe';
        case 'youtube':
            return 'bi bi-youtube';
        case 'arxiv':
            return 'bi bi-journal-text';
        default:
            return 'bi bi-question-circle';
    }
}

// Get progress bar class based on progress percentage
function getProgressClass(progress) {
    if (progress < 30) {
        return 'bg-danger';
    } else if (progress < 70) {
        return 'bg-warning';
    } else {
        return 'bg-success';
    }
}

// Add event listeners to task action buttons
function addTaskButtonEventListeners() {
    // View task buttons
    document.querySelectorAll('.view-task-btn').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            viewTaskDetails(taskId);
        });
    });
    
    // Pause task buttons
    document.querySelectorAll('.pause-task-btn').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            pauseTask(taskId);
        });
    });
    
    // Stop task buttons
    document.querySelectorAll('.stop-task-btn').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            stopTask(taskId);
        });
    });
    
    // Make rows clickable to view task details
    document.querySelectorAll('.task-row').forEach(row => {
        row.addEventListener('click', function(event) {
            // Only trigger if the click wasn't on a button
            if (!event.target.closest('button')) {
                const taskId = this.getAttribute('data-task-id');
                viewTaskDetails(taskId);
            }
        });
    });
}

// View task details
function viewTaskDetails(taskId) {
    console.log(`Viewing details for task ${taskId}`);
    
    // In a real application, you would fetch the task details from the API
    // For now, we'll use mock data
    const taskDetails = {
        id: taskId,
        name: 'Python Agentic RAG',
        source: 'GitHub',
        description: 'Analyze Python repositories implementing agentic RAG patterns',
        runtime: '2h 37min',
        progress: 85,
        status: 'active',
        created_at: '2025-05-01T10:30:00Z',
        updated_at: '2025-05-03T08:15:00Z',
        findings: {
            repositories: 24,
            code_files: 156,
            entities: 78,
            insights: 12
        }
    };
    
    // Update the modal content
    const modalContent = document.getElementById('task-details-content');
    modalContent.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-muted">Task Information</h6>
                <table class="table table-sm">
                    <tr>
                        <th>Name:</th>
                        <td>${taskDetails.name}</td>
                    </tr>
                    <tr>
                        <th>Source:</th>
                        <td><i class="${getSourceIcon(taskDetails.source)}"></i> ${taskDetails.source}</td>
                    </tr>
                    <tr>
                        <th>Description:</th>
                        <td>${taskDetails.description}</td>
                    </tr>
                    <tr>
                        <th>Status:</th>
                        <td><span class="badge bg-success">Active</span></td>
                    </tr>
                    <tr>
                        <th>Created:</th>
                        <td>${new Date(taskDetails.created_at).toLocaleString()}</td>
                    </tr>
                    <tr>
                        <th>Last Updated:</th>
                        <td>${new Date(taskDetails.updated_at).toLocaleString()}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6 class="text-muted">Progress</h6>
                <div class="progress mb-3" style="height: 20px;">
                    <div class="progress-bar ${getProgressClass(taskDetails.progress)}" role="progressbar" 
                        style="width: ${taskDetails.progress}%;" aria-valuenow="${taskDetails.progress}" 
                        aria-valuemin="0" aria-valuemax="100">
                        ${taskDetails.progress}%
                    </div>
                </div>
                
                <h6 class="text-muted mt-4">Findings Summary</h6>
                <div class="row text-center">
                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body py-2">
                                <h3 class="mb-0">${taskDetails.findings.repositories}</h3>
                                <small class="text-muted">Repositories</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body py-2">
                                <h3 class="mb-0">${taskDetails.findings.code_files}</h3>
                                <small class="text-muted">Code Files</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body py-2">
                                <h3 class="mb-0">${taskDetails.findings.entities}</h3>
                                <small class="text-muted">Entities</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card">
                            <div class="card-body py-2">
                                <h3 class="mb-0">${taskDetails.findings.insights}</h3>
                                <small class="text-muted">Insights</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-3">
            <div class="col-12">
                <h6 class="text-muted">Actions</h6>
                <div class="btn-group">
                    <button class="btn btn-outline-primary" onclick="pauseTask(${taskDetails.id})">
                        <i class="bi bi-pause-fill"></i> Pause
                    </button>
                    <button class="btn btn-outline-success" onclick="resumeTask(${taskDetails.id})">
                        <i class="bi bi-play-fill"></i> Resume
                    </button>
                    <button class="btn btn-outline-danger" onclick="stopTask(${taskDetails.id})">
                        <i class="bi bi-x-lg"></i> Stop
                    </button>
                    <button class="btn btn-outline-secondary" onclick="editTask(${taskDetails.id})">
                        <i class="bi bi-pencil"></i> Edit
                    </button>
                    <button class="btn btn-outline-info" onclick="exportTaskResults(${taskDetails.id})">
                        <i class="bi bi-download"></i> Export
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Set the view findings button action
    document.getElementById('viewFindingsBtn').setAttribute('data-task-id', taskId);
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('taskDetailsModal'));
    modal.show();
}

// Pause a task
function pauseTask(taskId) {
    console.log(`Pausing task ${taskId}`);
    // In a real application, you would call the API to pause the task
    alert(`Task ${taskId} paused`);
}

// Resume a task
function resumeTask(taskId) {
    console.log(`Resuming task ${taskId}`);
    // In a real application, you would call the API to resume the task
    alert(`Task ${taskId} resumed`);
}

// Stop a task
function stopTask(taskId) {
    console.log(`Stopping task ${taskId}`);
    
    // Confirm before stopping
    if (confirm('Are you sure you want to stop this task? This action cannot be undone.')) {
        // In a real application, you would call the API to stop the task
        alert(`Task ${taskId} stopped`);
    }
}

// Edit a task
function editTask(taskId) {
    console.log(`Editing task ${taskId}`);
    // In a real application, you would open a modal to edit the task
    alert(`Edit task ${taskId} (not implemented in this demo)`);
}

// Export task results
function exportTaskResults(taskId) {
    console.log(`Exporting results for task ${taskId}`);
    // In a real application, you would call the API to export the results
    alert(`Exporting results for task ${taskId} (not implemented in this demo)`);
}

// Setup event listeners
function setupEventListeners() {
    // Refresh button
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDataMiningTasks);
    }
    
    // Export button
    const exportBtn = document.getElementById('export-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            alert('Export functionality not implemented in this demo');
        });
    }
    
    // Filter dropdown items
    document.querySelectorAll('[data-filter]').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const filter = this.getAttribute('data-filter');
            filterTasks(filter);
        });
    });
    
    // Sort dropdown items
    document.querySelectorAll('[data-sort]').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const sort = this.getAttribute('data-sort');
            sortTasks(sort);
            
            // Update the dropdown button text
            const sortText = this.textContent.trim();
            document.getElementById('sortDropdown').innerHTML = `<i class="bi bi-sort-down"></i> Sort By: ${sortText}`;
        });
    });
    
    // Data source selection in the new task modal
    document.querySelectorAll('.data-source-card').forEach(card => {
        card.addEventListener('click', function() {
            const source = this.getAttribute('data-source');
            selectDataSource(source);
        });
    });
    
    // View findings button in task details modal
    document.getElementById('viewFindingsBtn').addEventListener('click', function() {
        const taskId = this.getAttribute('data-task-id');
        viewTaskFindings(taskId);
    });
    
    // Help button
    document.getElementById('helpBtn').addEventListener('click', function() {
        alert('Help functionality not implemented in this demo');
    });
}

// Filter tasks
function filterTasks(filter) {
    console.log(`Filtering tasks by: ${filter}`);
    
    const rows = document.querySelectorAll('.task-row');
    
    rows.forEach(row => {
        const source = row.getAttribute('data-source');
        const status = row.getAttribute('data-status');
        
        if (filter === 'all') {
            row.style.display = '';
        } else if (filter === source) {
            row.style.display = '';
        } else if (filter === 'active' && status === 'active') {
            row.style.display = '';
        } else if (filter === 'completed' && status === 'completed') {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Sort tasks
function sortTasks(sort) {
    console.log(`Sorting tasks by: ${sort}`);
    
    const tasksContainer = document.getElementById('data-mining-tasks');
    const rows = Array.from(document.querySelectorAll('.task-row'));
    
    // Sort the rows based on the selected sort option
    rows.sort((a, b) => {
        if (sort === 'name-asc') {
            return a.querySelector('td:first-child').textContent.localeCompare(b.querySelector('td:first-child').textContent);
        } else if (sort === 'name-desc') {
            return b.querySelector('td:first-child').textContent.localeCompare(a.querySelector('td:first-child').textContent);
        } else if (sort === 'source-asc') {
            return a.getAttribute('data-source').localeCompare(b.getAttribute('data-source'));
        } else if (sort === 'progress-desc') {
            return parseInt(b.getAttribute('data-progress')) - parseInt(a.getAttribute('data-progress'));
        } else if (sort === 'progress-asc') {
            return parseInt(a.getAttribute('data-progress')) - parseInt(b.getAttribute('data-progress'));
        } else if (sort === 'runtime-desc' || sort === 'runtime-asc') {
            // For demo purposes, we'll just use the current order
            // In a real application, you would parse the runtime and sort accordingly
            return sort === 'runtime-desc' ? 1 : -1;
        } else if (sort === 'date-desc') {
            // For demo purposes, we'll just use the current order
            // In a real application, you would parse the date and sort accordingly
            return -1;
        }
        
        return 0;
    });
    
    // Clear the container and append the sorted rows
    tasksContainer.innerHTML = '';
    rows.forEach(row => tasksContainer.appendChild(row));
    
    // Re-add event listeners
    addTaskButtonEventListeners();
}

// Select data source for new task
function selectDataSource(source) {
    console.log(`Selected data source: ${source}`);
    
    // In a real application, you would redirect to the appropriate configuration page
    // For now, we'll just close the modal and show an alert
    const modal = bootstrap.Modal.getInstance(document.getElementById('newDataMiningModal'));
    modal.hide();
    
    alert(`Selected ${source} as data source. In a real application, this would open the ${source} configuration dialog.`);
}

// View task findings
function viewTaskFindings(taskId) {
    console.log(`Viewing findings for task ${taskId}`);
    
    // In a real application, you would redirect to the findings page
    // For now, we'll just show an alert
    alert(`Viewing findings for task ${taskId} (not implemented in this demo)`);
}

// Add CSS styles for the data mining dashboard
document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.textContent = `
        .data-source-card {
            border: 1px solid #dee2e6;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .data-source-card:hover {
            border-color: #007bff;
            background-color: rgba(0, 123, 255, 0.05);
            transform: translateY(-5px);
        }
        
        .data-source-icon {
            font-size: 2.5rem;
            color: #6c757d;
        }
        
        .task-row {
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .task-row:hover {
            background-color: rgba(0, 123, 255, 0.05);
        }
    `;
    document.head.appendChild(style);
});

