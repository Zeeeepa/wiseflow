// Data Mining JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize data mining functionality
    initDataMining();
    
    // Load active data mining tasks
    loadDataMiningTasks();
    
    // Initialize advanced GitHub dialog functionality
    initAdvancedGitHubDialog();

    // Add event listener for "Add YouTube Mining" button in listings tab
    document.getElementById('add-youtube-mining-btn').addEventListener('click', function() {
        // Show YouTube configuration dialog
        showYouTubeConfigDialog();
        // Publish event for YouTube dialog opened
        EventBus.publish(EVENTS.DIALOG_OPENED, { dialogType: 'youtube' });
    });
    
    // Add event listener for the "Add Arxiv Mining" button to open the ArXiv dialog
    document.getElementById('add-arxiv-mining-btn').addEventListener('click', function() {
        const arxivConfigModal = new bootstrap.Modal(document.getElementById('arxivConfigModal'));
        arxivConfigModal.show();
        // Publish event for ArXiv dialog opened
        EventBus.publish(EVENTS.DIALOG_OPENED, { dialogType: 'arxiv' });
    });

    // Subscribe to template events
    EventBus.subscribe(EVENTS.DATA_LOADED, handleTemplateLoaded);
    
    // Subscribe to task events
    EventBus.subscribe(EVENTS.DATA_SAVED, handleTaskCreated);
    EventBus.subscribe(EVENTS.DATA_SAVED, handleTaskUpdated);
    EventBus.subscribe(EVENTS.DATA_DELETED, handleTaskDeleted);
});

// Handle template loaded event
function handleTemplateLoaded(data) {
    console.log('Template loaded:', data);
    
    // Load template data into the appropriate form based on template type
    if (data.type === 'github') {
        loadGitHubTemplate(data);
    } else if (data.type === 'youtube') {
        // Call the YouTube config loader from youtube_config.js
        if (typeof loadYouTubeConfigFromTemplate === 'function') {
            loadYouTubeConfigFromTemplate(data.config);
            
            // Show the YouTube config dialog
            showYouTubeConfigDialog();
        }
    } else if (data.type === 'arxiv') {
        // Handle ArXiv template loading
        loadArxivTemplate(data);
    } else if (data.type === 'web') {
        // Handle Web template loading
        loadWebTemplate(data);
    }
    
    // Show success notification
    WiseFlowUtils.showToast(`Template "${data.name}" loaded successfully`, 'success');
}

// Handle task created event
function handleTaskCreated(data) {
    console.log('Task created:', data);
    
    // Refresh the task list
    loadDataMiningTasks();
    
    // Show success notification
    WiseFlowUtils.showToast(`Task "${data.name}" created successfully`, 'success');
    
    // Navigate to listings tab
    document.getElementById('listings-tab').click();
}

// Handle task updated event
function handleTaskUpdated(data) {
    console.log('Task updated:', data);
    
    // Refresh the task list
    loadDataMiningTasks();
    
    // Show success notification
    WiseFlowUtils.showToast(`Task "${data.name}" updated successfully`, 'success');
}

// Handle task deleted event
function handleTaskDeleted(data) {
    console.log('Task deleted:', data);
    
    // Refresh the task list
    loadDataMiningTasks();
    
    // Show success notification
    WiseFlowUtils.showToast(`Task deleted successfully`, 'success');
}

// Initialize data mining functionality
function initDataMining() {
    // Add event listeners for data mining task creation
    setupDataMiningTaskCreation('github');
    setupDataMiningTaskCreation('arxiv');
    setupDataMiningTaskCreation('web');
    setupDataMiningTaskCreation('youtube');
    
    // Add event listeners for task actions (view, edit, toggle, delete)
    setupTaskActionListeners();
    
    // Add event listeners for task interconnection
    setupTaskInterconnection();
}

// Initialize advanced GitHub dialog functionality
function initAdvancedGitHubDialog() {
    // Add event listener for "Add More" button in reference context files
    const addMoreBtn = document.getElementById('github-add-more-btn');
    if (addMoreBtn) {
        addMoreBtn.addEventListener('click', function() {
            const fileInput = document.getElementById('github-context-file-input');
            if (fileInput) {
                fileInput.click();
            }
        });
    }
    
    // Add event listeners for dialog buttons
    setupGitHubDialogButtons();
    
    // Add event listener for search scheme change
    const searchScheme = document.getElementById('github-search-scheme');
    if (searchScheme) {
        searchScheme.addEventListener('change', function() {
            toggleAdvancedSearchOptions(this.value === 'advanced');
        });
    }
}

// Setup GitHub dialog buttons
function setupGitHubDialogButtons() {
    // Cancel button
    const cancelBtn = document.getElementById('github-cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            // Switch back to listings tab
            document.getElementById('listings-tab').click();
        });
    }
    
    // Save as Template button
    const saveTemplateBtn = document.getElementById('github-save-template-btn');
    if (saveTemplateBtn) {
        saveTemplateBtn.addEventListener('click', function() {
            saveGitHubSearchTemplate();
        });
    }
    
    // Preview button
    const previewBtn = document.getElementById('github-preview-btn');
    if (previewBtn) {
        previewBtn.addEventListener('click', function() {
            previewGitHubSearch();
        });
    }
    
    // Start button
    const startBtn = document.getElementById('github-start-btn');
    if (startBtn) {
        startBtn.addEventListener('click', function() {
            startGitHubSearch();
        });
    }
}

// Toggle advanced search options based on search scheme
function toggleAdvancedSearchOptions(showAdvanced) {
    const contentAnalysisSection = document.querySelector('.mb-4:has(label.form-label:contains("Content Analysis"))');
    if (contentAnalysisSection) {
        contentAnalysisSection.style.display = showAdvanced ? 'block' : 'none';
    }
    
    // Show/hide additional options based on search scheme
    const advancedOptions = document.querySelectorAll('#github-search-issues, #github-search-prs, #github-search-discussions');
    advancedOptions.forEach(option => {
        option.closest('.form-check').style.display = showAdvanced ? 'block' : 'none';
    });
}

// Save GitHub search as template
function saveGitHubSearchTemplate() {
    const templateName = prompt('Enter a name for this template:');
    if (!templateName) return;
    
    const templateData = collectGitHubFormData();
    templateData.name = templateName;
    
    // Show saving indicator
    const statusDiv = document.getElementById('github-search-status');
    if (statusDiv) {
        statusDiv.innerHTML = '<div class="alert alert-info">Saving template...</div>';
    }
    
    // Send template data to server
    fetch('/api/data-mining/templates', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(templateData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            if (statusDiv) {
                statusDiv.innerHTML = '<div class="alert alert-success">Template saved successfully!</div>';
                
                // Clear status after 3 seconds
                setTimeout(() => {
                    statusDiv.innerHTML = '';
                }, 3000);
            }
        } else {
            if (statusDiv) {
                statusDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.message || 'Unknown error'}</div>`;
            }
        }
    })
    .catch(error => {
        console.error('Error saving template:', error);
        if (statusDiv) {
            statusDiv.innerHTML = '<div class="alert alert-danger">Error saving template. Please try again.</div>';
        }
    });
}

// Preview GitHub search
function previewGitHubSearch() {
    const searchData = collectGitHubFormData();
    
    // Show preview indicator
    const statusDiv = document.getElementById('github-search-status');
    if (statusDiv) {
        statusDiv.innerHTML = '<div class="alert alert-info">Generating preview...</div>';
    }
    
    // Send search data to server for preview
    fetch('/api/data-mining/preview', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(searchData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Display preview results
            if (statusDiv) {
                let previewHtml = '<div class="alert alert-success">';
                previewHtml += '<h5>Preview Results</h5>';
                previewHtml += '<p>Estimated repositories: ' + data.estimated_repos + '</p>';
                previewHtml += '<p>Estimated code files: ' + data.estimated_files + '</p>';
                previewHtml += '<p>Estimated processing time: ' + data.estimated_time + '</p>';
                previewHtml += '</div>';
                
                statusDiv.innerHTML = previewHtml;
            }
        } else {
            if (statusDiv) {
                statusDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.message || 'Unknown error'}</div>`;
            }
        }
    })
    .catch(error => {
        console.error('Error generating preview:', error);
        if (statusDiv) {
            statusDiv.innerHTML = '<div class="alert alert-danger">Error generating preview. Please try again.</div>';
        }
    });
}

// Start GitHub search
function startGitHubSearch() {
    const searchData = collectGitHubFormData();
    
    // Show starting indicator
    const statusDiv = document.getElementById('github-search-status');
    if (statusDiv) {
        statusDiv.innerHTML = '<div class="alert alert-info">Starting search...</div>';
    }
    
    // Create form data for file upload
    const formData = new FormData();
    formData.append('name', searchData.focus || 'GitHub Search');
    formData.append('task_type', 'github');
    formData.append('description', searchData.description || '');
    formData.append('search_params', JSON.stringify(searchData));
    
    // Add context files if any
    const fileInput = document.getElementById('github-context-file-input');
    if (fileInput && fileInput.files.length > 0) {
        for (let i = 0; i < fileInput.files.length; i++) {
            formData.append('context_files', fileInput.files[i]);
        }
    }
    
    // Send search data to server
    fetch('/api/data-mining/tasks', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            if (statusDiv) {
                statusDiv.innerHTML = '<div class="alert alert-success">Search started successfully!</div>';
                
                // Switch to listings tab after 2 seconds
                setTimeout(() => {
                    document.getElementById('listings-tab').click();
                    
                    // Reload task listings
                    loadDataMiningTasks();
                }, 2000);
            }
        } else {
            if (statusDiv) {
                statusDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.message || 'Unknown error'}</div>`;
            }
        }
    })
    .catch(error => {
        console.error('Error starting search:', error);
        if (statusDiv) {
            statusDiv.innerHTML = '<div class="alert alert-danger">Error starting search. Please try again.</div>';
        }
    });
}

// Collect GitHub form data
function collectGitHubFormData() {
    return {
        focus: document.getElementById('github-search-focus')?.value || '',
        description: document.getElementById('github-search-description')?.value || '',
        goal: document.getElementById('github-search-goal')?.value || '',
        search_scheme: document.getElementById('github-search-scheme')?.value || 'basic',
        repository_filters: {
            language: document.getElementById('github-language-filter')?.value || 'all',
            stars: document.getElementById('github-stars-filter')?.value || 'any',
            updated: document.getElementById('github-updated-filter')?.value || 'any'
        },
        options: {
            search_repositories: document.getElementById('github-search-repos')?.checked || false,
            search_code: document.getElementById('github-search-code')?.checked || false,
            search_issues: document.getElementById('github-search-issues')?.checked || false,
            search_prs: document.getElementById('github-search-prs')?.checked || false,
            search_discussions: document.getElementById('github-search-discussions')?.checked || false
        },
        content_analysis: {
            code_structure: document.getElementById('github-analyze-code-structure')?.checked || false,
            documentation: document.getElementById('github-analyze-documentation')?.checked || false,
            dependencies: document.getElementById('github-analyze-dependencies')?.checked || false,
            test_coverage: document.getElementById('github-analyze-test-coverage')?.checked || false
        },
        parallel_workers: parseInt(document.getElementById('github-parallel-workers')?.value || '6'),
        advanced_options: {
            clone_locally: document.getElementById('github-clone-locally')?.checked || false,
            follow_links: document.getElementById('github-follow-links')?.checked || false,
            include_forks: document.getElementById('github-include-forks')?.checked || false,
            save_to_db: document.getElementById('github-save-to-db')?.checked || false,
            generate_report: document.getElementById('github-generate-report')?.checked || false,
            use_custom_api: document.getElementById('github-use-custom-api')?.checked || false
        }
    };
}

// Load active data mining tasks
function loadDataMiningTasks() {
    // Show loading indicator
    const miningListings = document.getElementById('mining-listings');
    if (miningListings) {
        miningListings.innerHTML = '<tr><td colspan="5" class="text-center"><i class="bi bi-arrow-repeat spin me-2"></i> Loading tasks...</td></tr>';
    }
    
    // Fetch tasks from API using ApiService
    ApiService.dataMining.getTasks()
        .then(data => {
            if (data.status === 'success' && data.tasks) {
                displayDataMiningTasks(data.tasks);
            } else {
                if (miningListings) {
                    miningListings.innerHTML = '<tr><td colspan="5" class="text-center">No data mining tasks found</td></tr>';
                }
            }
        })
        .catch(error => {
            console.error('Error loading data mining tasks:', error);
            if (miningListings) {
                miningListings.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading tasks</td></tr>';
            }
        });
}

// Display data mining tasks
function displayDataMiningTasks(tasks) {
    const miningListings = document.getElementById('mining-listings');
    if (!miningListings) return;
    
    if (tasks.length === 0) {
        miningListings.innerHTML = '<tr><td colspan="5" class="text-center">No data mining tasks found</td></tr>';
        return;
    }
    
    // Clear existing content
    miningListings.innerHTML = '';
    
    // Sort tasks by updated_at (newest first)
    tasks.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
    
    // Add each task to the table
    tasks.forEach(task => {
        const row = document.createElement('tr');
        
        // Format date
        const updatedDate = new Date(task.updated_at).toLocaleString();
        
        // Determine status badge class
        let statusBadgeClass = 'bg-secondary';
        if (task.status === 'active') {
            statusBadgeClass = 'bg-success';
        } else if (task.status === 'running') {
            statusBadgeClass = 'bg-primary';
        } else if (task.status === 'error') {
            statusBadgeClass = 'bg-danger';
        }
        
        // Capitalize task type
        const typeDisplay = task.task_type.charAt(0).toUpperCase() + task.task_type.slice(1);
        
        row.innerHTML = `
            <td>${task.name}</td>
            <td>${typeDisplay}</td>
            <td><span class="badge ${statusBadgeClass}">${task.status}</span></td>
            <td>${updatedDate}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary view-findings-btn" data-task-id="${task.task_id}">View Findings</button>
                <button class="btn btn-sm btn-outline-warning edit-task-btn" data-task-id="${task.task_id}">Edit</button>
                ${task.status === 'active' ? 
                    `<button class="btn btn-sm btn-outline-secondary toggle-task-btn" data-task-id="${task.task_id}" data-action="off">Turn Off</button>` : 
                    `<button class="btn btn-sm btn-outline-success toggle-task-btn" data-task-id="${task.task_id}" data-action="on">Turn On</button>`
                }
                <button class="btn btn-sm btn-outline-danger delete-task-btn" data-task-id="${task.task_id}">Remove</button>
                <button class="btn btn-sm btn-outline-info interconnect-task-btn" data-task-id="${task.task_id}" data-bs-toggle="modal" data-bs-target="#interconnectTaskModal">Interconnect</button>
            </td>
        `;
        
        miningListings.appendChild(row);
    });
    
    // Add event listeners to the newly created buttons
    addTaskButtonEventListeners();
}

// Add event listeners to task action buttons
function addTaskButtonEventListeners() {
    // View findings buttons
    document.querySelectorAll('.view-findings-btn').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            showExpandedFindings(taskId);
        });
    });
    
    // Edit task buttons
    document.querySelectorAll('.edit-task-btn').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            editTask(taskId);
        });
    });
    
    // Toggle task buttons
    document.querySelectorAll('.toggle-task-btn').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            const action = this.getAttribute('data-action');
            toggleTask(taskId, action === 'on');
        });
    });
    
    // Delete task buttons
    document.querySelectorAll('.delete-task-btn').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            deleteTask(taskId);
        });
    });
    
    // Interconnect task buttons
    document.querySelectorAll('.interconnect-task-btn').forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.getAttribute('data-task-id');
            prepareInterconnectModal(taskId);
        });
    });
}

// Setup data mining task creation
function setupDataMiningTaskCreation(taskType) {
    const startSearchBtn = document.getElementById(`start-${taskType}-search-btn`);
    const searchForm = document.getElementById(`${taskType}-search-form`);
    
    if (startSearchBtn && searchForm) {
        startSearchBtn.addEventListener('click', function() {
            // Get form data
            const searchGoal = document.getElementById(`${taskType}-search-goal`).value;
            const searchDescription = document.getElementById(`${taskType}-search-description`).value;
            
            // Validate required fields
            if (!searchGoal) {
                alert('Please enter a search goal');
                return;
            }
            
            // Get additional parameters based on task type
            let searchParams = {
                goal: searchGoal,
                description: searchDescription
            };
            
            // Add type-specific parameters
            if (taskType === 'github') {
                const searchStrategy = document.getElementById('github-search-strategy').value;
                const searchPriority = document.getElementById('github-search-priority').value;
                searchParams.strategy = searchStrategy;
                searchParams.priority = searchPriority;
            } else if (taskType === 'arxiv') {
                const searchCategory = document.getElementById('arxiv-search-category').value;
                const searchSort = document.getElementById('arxiv-search-sort').value;
                searchParams.category = searchCategory;
                searchParams.sort = searchSort;
            } else if (taskType === 'web') {
                const searchType = document.getElementById('web-search-type').value;
                const searchTimeframe = document.getElementById('web-search-timeframe').value;
                searchParams.type = searchType;
                searchParams.timeframe = searchTimeframe;
            } else if (taskType === 'youtube') {
                const searchType = document.getElementById('youtube-search-type').value;
                const searchDuration = document.getElementById('youtube-search-duration').value;
                searchParams.type = searchType;
                searchParams.duration = searchDuration;
            }
            
            // Create FormData object
            const formData = new FormData();
            formData.append('name', searchGoal);
            formData.append('task_type', taskType);
            formData.append('description', searchDescription);
            formData.append('search_params', JSON.stringify(searchParams));
            
            // Add context files if any
            const contextFilesList = document.getElementById(`${taskType}-selected-files-list`);
            if (contextFilesList) {
                const fileItems = contextFilesList.querySelectorAll('li');
                fileItems.forEach((item, index) => {
                    const fileInput = document.getElementById(`${taskType}-context-file-input`);
                    if (fileInput && fileInput.files[index]) {
                        formData.append('context_files', fileInput.files[index]);
                    }
                });
            }
            
            // Show search in progress
            const searchStatus = document.getElementById(`${taskType}-search-status`);
            if (searchStatus) {
                searchStatus.innerHTML = '<i class="bi bi-arrow-repeat spin me-2"></i> Creating data mining task...';
                searchStatus.className = 'mt-3 text-center text-primary';
            }
            
            // Create the task via API
            fetch('/data-mining/api/data-mining/tasks', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    if (searchStatus) {
                        searchStatus.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i> Data mining task created successfully!';
                        searchStatus.className = 'mt-3 text-center text-success';
                    }
                    
                    // Redirect to listings tab to show results
                    document.getElementById('listings-tab').click();
                    
                    // Reload tasks
                    loadDataMiningTasks();
                    
                    // Reset form
                    searchForm.reset();
                } else {
                    if (searchStatus) {
                        searchStatus.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i> Error: ${data.message || 'Failed to create task'}`;
                        searchStatus.className = 'mt-3 text-center text-danger';
                    }
                }
            })
            .catch(error => {
                console.error('Error creating data mining task:', error);
                if (searchStatus) {
                    searchStatus.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-2"></i> Error creating task';
                    searchStatus.className = 'mt-3 text-center text-danger';
                }
            });
        });
    }
}

// Setup task action listeners
function setupTaskActionListeners() {
    // These are set up when tasks are loaded
}

// View task findings
function viewTaskFindings(taskId) {
    // Fetch task results
    fetch(`/data-mining/api/data-mining/tasks/${taskId}/results`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Show results in a modal
                showTaskResultsModal(taskId, data.results);
            } else {
                alert('Error fetching task results');
            }
        })
        .catch(error => {
            console.error('Error fetching task results:', error);
            alert('Error fetching task results');
        });
}

// Show task results modal
function showTaskResultsModal(taskId, results) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('taskResultsModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'taskResultsModal';
        modal.tabIndex = '-1';
        modal.setAttribute('aria-labelledby', 'taskResultsModalLabel');
        modal.setAttribute('aria-hidden', 'true');
        
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="taskResultsModalLabel">Task Results</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" id="taskResultsModalBody">
                        <!-- Results will be inserted here -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" id="analyzeTaskBtn">Analyze</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Add event listener for analyze button
        document.getElementById('analyzeTaskBtn').addEventListener('click', function() {
            analyzeTask(taskId);
        });
    }
    
    // Update modal content
    const modalBody = document.getElementById('taskResultsModalBody');
    
    if (results.error) {
        modalBody.innerHTML = `<div class="alert alert-danger">${results.error}</div>`;
    } else if (results.analysis) {
        // Show analysis results
        let analysisHtml = '<h4>Analysis Results</h4>';
        
        // Entities
        if (results.analysis.entities && results.analysis.entities.length > 0) {
            analysisHtml += '<h5>Entities</h5><ul>';
            results.analysis.entities.forEach(entity => {
                analysisHtml += `<li><strong>${entity.name}</strong> (${entity.type}): ${entity.description || ''}</li>`;
            });
            analysisHtml += '</ul>';
        }
        
        // Topics
        if (results.analysis.topics && results.analysis.topics.length > 0) {
            analysisHtml += '<h5>Topics</h5><ul>';
            results.analysis.topics.forEach(topic => {
                analysisHtml += `<li><strong>${topic.label}</strong>: ${topic.description || ''}</li>`;
            });
            analysisHtml += '</ul>';
        }
        
        // Temporal patterns
        if (results.analysis.temporal_patterns && results.analysis.temporal_patterns.patterns) {
            analysisHtml += '<h5>Temporal Patterns</h5><ul>';
            results.analysis.temporal_patterns.patterns.forEach(pattern => {
                analysisHtml += `<li><strong>${pattern.pattern_type}</strong>: ${pattern.description || ''}</li>`;
            });
            analysisHtml += '</ul>';
            
            if (results.analysis.temporal_patterns.summary) {
                analysisHtml += `<p><strong>Summary:</strong> ${results.analysis.temporal_patterns.summary}</p>`;
            }
        }
        
        // Knowledge graph
        if (results.analysis.knowledge_graph_path) {
            analysisHtml += `<h5>Knowledge Graph</h5>
                <div class="text-center">
                    <img src="${results.analysis.knowledge_graph_path}" class="img-fluid" alt="Knowledge Graph">
                </div>`;
        }
        
        modalBody.innerHTML = analysisHtml;
    } else {
        // Show raw results
        modalBody.innerHTML = `
            <div class="alert alert-info">No analysis available yet. Click "Analyze" to generate insights.</div>
            <h5>Raw Results</h5>
            <pre class="bg-light p-3">${JSON.stringify(results, null, 2)}</pre>
        `;
    }
    
    // Show the modal
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Analyze task
function analyzeTask(taskId) {
    // Show loading indicator
    const modalBody = document.getElementById('taskResultsModalBody');
    modalBody.innerHTML = '<div class="text-center"><i class="bi bi-arrow-repeat spin me-2"></i> Analyzing data... This may take a moment.</div>';
    
    // Call analyze API
    fetch(`/data-mining/api/data-mining/tasks/${taskId}/analyze`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            modalBody.innerHTML = '<div class="alert alert-success">Analysis started. This may take a few minutes. Close this modal and check back later.</div>';
            
            // Reload task results after a delay
            setTimeout(() => {
                viewTaskFindings(taskId);
            }, 5000);
        } else {
            modalBody.innerHTML = `<div class="alert alert-danger">Error starting analysis: ${data.message || 'Unknown error'}</div>`;
        }
    })
    .catch(error => {
        console.error('Error analyzing task:', error);
        modalBody.innerHTML = '<div class="alert alert-danger">Error starting analysis. Please try again later.</div>';
    });
}

// Edit task
function editTask(taskId) {
    // Fetch task details
    fetch(`/data-mining/api/data-mining/tasks/${taskId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.task) {
                showEditTaskModal(data.task);
            } else {
                alert('Error fetching task details');
            }
        })
        .catch(error => {
            console.error('Error fetching task details:', error);
            alert('Error fetching task details');
        });
}

// Show edit task modal
function showEditTaskModal(task) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('editTaskModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'editTaskModal';
        modal.tabIndex = '-1';
        modal.setAttribute('aria-labelledby', 'editTaskModalLabel');
        modal.setAttribute('aria-hidden', 'true');
        
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="editTaskModalLabel">Edit Task</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editTaskForm">
                            <input type="hidden" id="edit-task-id">
                            <div class="mb-3">
                                <label for="edit-task-name" class="form-label">Task Name</label>
                                <input type="text" class="form-control" id="edit-task-name" required>
                            </div>
                            <div class="mb-3">
                                <label for="edit-task-description" class="form-label">Description</label>
                                <textarea class="form-control" id="edit-task-description" rows="3"></textarea>
                            </div>
                            <div class="mb-3">
                                <label for="edit-task-params" class="form-label">Search Parameters</label>
                                <textarea class="form-control" id="edit-task-params" rows="5"></textarea>
                                <small class="text-muted">JSON format</small>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="saveTaskChangesBtn">Save Changes</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Add event listener for save button
        document.getElementById('saveTaskChangesBtn').addEventListener('click', function() {
            saveTaskChanges();
        });
    }
    
    // Fill form with task details
    document.getElementById('edit-task-id').value = task.task_id;
    document.getElementById('edit-task-name').value = task.name;
    document.getElementById('edit-task-description').value = task.description;
    document.getElementById('edit-task-params').value = JSON.stringify(task.search_params, null, 2);
    
    // Update modal title
    document.getElementById('editTaskModalLabel').textContent = `Edit Task: ${task.name}`;
    
    // Show the modal
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
}

// Save task changes
function saveTaskChanges() {
    const taskId = document.getElementById('edit-task-id').value;
    const name = document.getElementById('edit-task-name').value;
    const description = document.getElementById('edit-task-description').value;
    let searchParams;
    
    try {
        searchParams = JSON.parse(document.getElementById('edit-task-params').value);
    } catch (error) {
        alert('Invalid JSON in search parameters');
        return;
    }
    
    // Prepare update data
    const updateData = {
        name: name,
        description: description,
        search_params: searchParams
    };
    
    // Update task via API
    fetch(`/data-mining/api/data-mining/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updateData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editTaskModal'));
            modal.hide();
            
            // Reload tasks
            loadDataMiningTasks();
            
            // Show success message
            alert('Task updated successfully');
        } else {
            alert(`Error updating task: ${data.message || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error('Error updating task:', error);
        alert('Error updating task');
    });
}

// Toggle task status
function toggleTask(taskId, active) {
    // Confirm action
    const action = active ? 'activate' : 'deactivate';
    if (!confirm(`Are you sure you want to ${action} this task?`)) {
        return;
    }
    
    // Toggle task via API
    fetch(`/data-mining/api/data-mining/tasks/${taskId}/toggle`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ active: active })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Reload tasks
            loadDataMiningTasks();
        } else {
            alert(`Error toggling task: ${data.message || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error('Error toggling task:', error);
        alert('Error toggling task');
    });
}

// Delete task
function deleteTask(taskId) {
    // Confirm deletion
    if (!confirm('Are you sure you want to delete this task? This action cannot be undone.')) {
        return;
    }
    
    // Delete task via API
    fetch(`/data-mining/api/data-mining/tasks/${taskId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Reload tasks
            loadDataMiningTasks();
        } else {
            alert(`Error deleting task: ${data.message || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error('Error deleting task:', error);
        alert('Error deleting task');
    });
}

// Setup task interconnection
function setupTaskInterconnection() {
    // Create interconnect modal if it doesn't exist
    let modal = document.getElementById('interconnectTaskModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'interconnectTaskModal';
        modal.tabIndex = '-1';
        modal.setAttribute('aria-labelledby', 'interconnectTaskModalLabel');
        modal.setAttribute('aria-hidden', 'true');
        
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="interconnectTaskModalLabel">Interconnect Tasks</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="interconnectTaskForm">
                            <input type="hidden" id="source-task-id">
                            <div class="mb-3">
                                <label for="target-task-select" class="form-label">Connect with Task</label>
                                <select class="form-select" id="target-task-select" required>
                                    <option value="">Select a task</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="interconnection-type" class="form-label">Connection Type</label>
                                <select class="form-select" id="interconnection-type" required>
                                    <option value="feed">Feed results as input</option>
                                    <option value="filter">Use as filter</option>
                                    <option value="combine">Combine results</option>
                                    <option value="sequence">Run in sequence</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="interconnection-description" class="form-label">Description</label>
                                <textarea class="form-control" id="interconnection-description" rows="3" placeholder="Describe how these tasks should work together..."></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="saveInterconnectionBtn">Connect Tasks</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Add event listener for save button
        document.getElementById('saveInterconnectionBtn').addEventListener('click', function() {
            saveTaskInterconnection();
        });
    }
}

// Prepare interconnect modal
function prepareInterconnectModal(taskId) {
    // Set source task ID
    document.getElementById('source-task-id').value = taskId;
    
    // Fetch all tasks to populate target select
    fetch('/data-mining/api/data-mining/tasks')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.tasks) {
                const targetSelect = document.getElementById('target-task-select');
                targetSelect.innerHTML = '<option value="">Select a task</option>';
                
                // Add all tasks except the source task
                data.tasks.forEach(task => {
                    if (task.task_id !== taskId) {
                        const option = document.createElement('option');
                        option.value = task.task_id;
                        option.textContent = `${task.name} (${task.task_type})`;
                        targetSelect.appendChild(option);
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error fetching tasks for interconnection:', error);
        });
}

// Save task interconnection
function saveTaskInterconnection() {
    const sourceTaskId = document.getElementById('source-task-id').value;
    const targetTaskId = document.getElementById('target-task-select').value;
    const interconnectionType = document.getElementById('interconnection-type').value;
    const description = document.getElementById('interconnection-description').value;
    
    if (!targetTaskId) {
        alert('Please select a target task');
        return;
    }
    
    // Prepare interconnection data
    const interconnectionData = {
        target_task_id: targetTaskId,
        interconnection_type: interconnectionType,
        description: description
    };
    
    // Create interconnection via API
    fetch(`/data-mining/api/data-mining/tasks/${sourceTaskId}/interconnect`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(interconnectionData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('interconnectTaskModal'));
            modal.hide();
            
            // Show success message
            alert('Tasks interconnected successfully');
            
            // Reload tasks to show updated interconnections
            loadDataMiningTasks();
        } else {
            alert(`Error interconnecting tasks: ${data.message || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error('Error interconnecting tasks:', error);
        alert('Error interconnecting tasks');
    });
}

// Show YouTube configuration dialog
function showYouTubeConfigDialog() {
    // Create modal if it doesn't exist
    let modal = document.getElementById('youtubeConfigModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'youtubeConfigModal';
        modal.tabIndex = '-1';
        modal.setAttribute('aria-labelledby', 'youtubeConfigModalLabel');
        modal.setAttribute('aria-hidden', 'true');
        
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="youtubeConfigModalLabel">YouTube Configuration</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="youtubeConfigForm">
                            <div class="mb-3">
                                <label for="youtube-search-type" class="form-label">Search Type</label>
                                <select class="form-select" id="youtube-search-type" required>
                                    <option value="videos">Videos</option>
                                    <option value="playlists">Playlists</option>
                                    <option value="channels">Channels</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="youtube-search-timeframe" class="form-label">Timeframe</label>
                                <select class="form-select" id="youtube-search-timeframe" required>
                                    <option value="all">All Time</option>
                                    <option value="last-week">Last Week</option>
                                    <option value="last-month">Last Month</option>
                                    <option value="last-year">Last Year</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="youtube-search-duration" class="form-label">Duration</label>
                                <select class="form-select" id="youtube-search-duration" required>
                                    <option value="all">All</option>
                                    <option value="short">Short</option>
                                    <option value="medium">Medium</option>
                                    <option value="long">Long</option>
                                </select>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="saveYouTubeConfigBtn">Save Configuration</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Add event listener for save button
        document.getElementById('saveYouTubeConfigBtn').addEventListener('click', function() {
            saveYouTubeConfig();
        });
    }
}

// Save YouTube configuration
function saveYouTubeConfig() {
    const searchType = document.getElementById('youtube-search-type').value;
    const timeframe = document.getElementById('youtube-search-timeframe').value;
    const duration = document.getElementById('youtube-search-duration').value;
    
    // Prepare configuration data
    const configData = {
        search_type: searchType,
        timeframe: timeframe,
        duration: duration
    };
    
    // Save configuration via API
    fetch('/data-mining/api/data-mining/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(configData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('youtubeConfigModal'));
            modal.hide();
            
            // Show success message
            alert('YouTube configuration saved successfully');
        } else {
            alert(`Error saving configuration: ${data.message || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error('Error saving YouTube configuration:', error);
        alert('Error saving YouTube configuration');
    });
}
