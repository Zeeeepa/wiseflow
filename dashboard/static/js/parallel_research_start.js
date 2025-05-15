/**
 * Parallel Research Start JavaScript
 * Handles the form for starting new research flows
 */

// Global variables
let taskCounter = 0;
let flowTemplates = [];

// DOM elements
const newResearchFlowForm = document.getElementById('new-research-flow-form');
const tasksContainer = document.getElementById('tasks-container');
const addTaskBtn = document.getElementById('add-task-btn');
const saveAsTemplateBtn = document.getElementById('save-as-template-btn');
const clearFormBtn = document.getElementById('clear-form-btn');
const templatesContainer = document.getElementById('templates-container');
const taskTemplate = document.getElementById('task-template');
const toastNotification = document.getElementById('toast-notification');
const toastTitle = document.getElementById('toast-title');
const toastMessage = document.getElementById('toast-message');

// Source config templates
const webSourceTemplate = document.getElementById('web-source-template');
const githubSourceTemplate = document.getElementById('github-source-template');
const arxivSourceTemplate = document.getElementById('arxiv-source-template');
const youtubeSourceTemplate = document.getElementById('youtube-source-template');
const customSourceTemplate = document.getElementById('custom-source-template');

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    initializePage();
    setupEventListeners();
});

/**
 * Initialize the page
 */
function initializePage() {
    // Add the first task by default
    addTask();
    
    // Load templates
    loadTemplates();
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Add task button
    addTaskBtn.addEventListener('click', addTask);
    
    // Save as template button
    saveAsTemplateBtn.addEventListener('click', saveAsTemplate);
    
    // Clear form button
    clearFormBtn.addEventListener('click', clearForm);
    
    // Form submission
    newResearchFlowForm.addEventListener('submit', handleFormSubmit);
}

/**
 * Add a new task to the form
 */
function addTask() {
    // Clone the task template
    const taskNode = document.importNode(taskTemplate.content, true);
    const taskCard = taskNode.querySelector('.task-card');
    const taskId = `task-${taskCounter++}`;
    taskCard.id = taskId;
    
    // Set up event listeners for the task
    const removeTaskBtn = taskNode.querySelector('.remove-task-btn');
    removeTaskBtn.addEventListener('click', () => removeTask(taskId));
    
    const sourceSelect = taskNode.querySelector('.task-source');
    sourceSelect.addEventListener('change', (e) => handleSourceTypeChange(e, taskId));
    
    // Add the task to the container
    tasksContainer.appendChild(taskNode);
}

/**
 * Remove a task from the form
 */
function removeTask(taskId) {
    const taskCard = document.getElementById(taskId);
    if (taskCard) {
        taskCard.remove();
    }
    
    // If no tasks left, add one
    if (tasksContainer.children.length === 0) {
        addTask();
    }
}

/**
 * Handle source type change
 */
function handleSourceTypeChange(event, taskId) {
    const sourceType = event.target.value;
    const taskCard = document.getElementById(taskId);
    const configContainer = taskCard.querySelector('.source-config-container');
    
    // Clear the container
    configContainer.innerHTML = '';
    
    // Add the appropriate config template
    let templateNode;
    switch (sourceType) {
        case 'web':
            templateNode = document.importNode(webSourceTemplate.content, true);
            break;
        case 'github':
            templateNode = document.importNode(githubSourceTemplate.content, true);
            break;
        case 'arxiv':
            templateNode = document.importNode(arxivSourceTemplate.content, true);
            break;
        case 'youtube':
            templateNode = document.importNode(youtubeSourceTemplate.content, true);
            break;
        case 'custom':
            templateNode = document.importNode(customSourceTemplate.content, true);
            break;
        default:
            return;
    }
    
    configContainer.appendChild(templateNode);
}

/**
 * Handle form submission
 */
function handleFormSubmit(event) {
    event.preventDefault();
    
    // Validate the form
    if (!validateForm()) {
        return;
    }
    
    // Get form data
    const formData = getFormData();
    
    // Create the research flow
    createResearchFlow(formData);
}

/**
 * Validate the form
 */
function validateForm() {
    // Check if flow name is provided
    const flowName = document.getElementById('flow-name').value.trim();
    if (!flowName) {
        showToast('Validation Error', 'Please enter a name for the research flow.', 'error');
        return false;
    }
    
    // Check if at least one task is provided
    const taskCards = tasksContainer.querySelectorAll('.task-card');
    if (taskCards.length === 0) {
        showToast('Validation Error', 'Please add at least one research task.', 'error');
        return false;
    }
    
    // Validate each task
    for (const taskCard of taskCards) {
        const taskName = taskCard.querySelector('.task-name').value.trim();
        if (!taskName) {
            showToast('Validation Error', 'Please enter a name for all research tasks.', 'error');
            return false;
        }
        
        const sourceType = taskCard.querySelector('.task-source').value;
        if (!sourceType) {
            showToast('Validation Error', 'Please select a source type for all research tasks.', 'error');
            return false;
        }
        
        // Validate source-specific fields
        const configContainer = taskCard.querySelector('.source-config-container');
        
        switch (sourceType) {
            case 'web':
            case 'github':
            case 'arxiv':
            case 'youtube':
                const searchQuery = configContainer.querySelector('.config-search-query');
                if (searchQuery && !searchQuery.value.trim()) {
                    showToast('Validation Error', 'Please enter a search query for all research tasks.', 'error');
                    return false;
                }
                break;
            case 'custom':
                const apiEndpoint = configContainer.querySelector('.config-api-endpoint');
                if (apiEndpoint && !apiEndpoint.value.trim()) {
                    showToast('Validation Error', 'Please enter an API endpoint for all custom sources.', 'error');
                    return false;
                }
                break;
        }
    }
    
    return true;
}

/**
 * Get form data
 */
function getFormData() {
    const flowName = document.getElementById('flow-name').value.trim();
    const flowDescription = document.getElementById('flow-description').value.trim();
    
    const tasks = [];
    const taskCards = tasksContainer.querySelectorAll('.task-card');
    
    for (const taskCard of taskCards) {
        const taskName = taskCard.querySelector('.task-name').value.trim();
        const taskDescription = taskCard.querySelector('.task-description').value.trim();
        const sourceType = taskCard.querySelector('.task-source').value;
        
        // Get source config
        const sourceConfig = getSourceConfig(taskCard, sourceType);
        
        tasks.push({
            name: taskName,
            description: taskDescription,
            source: sourceType,
            source_config: sourceConfig
        });
    }
    
    return {
        name: flowName,
        description: flowDescription,
        tasks: tasks
    };
}

/**
 * Get source configuration based on source type
 */
function getSourceConfig(taskCard, sourceType) {
    const configContainer = taskCard.querySelector('.source-config-container');
    let sourceConfig = {};
    
    switch (sourceType) {
        case 'web':
            sourceConfig = {
                search_query: configContainer.querySelector('.config-search-query').value.trim(),
                max_results: parseInt(configContainer.querySelector('.config-max-results').value) || 10,
                time_range: configContainer.querySelector('.config-time-range').value
            };
            break;
        case 'github':
            sourceConfig = {
                repository: configContainer.querySelector('.config-repository').value.trim(),
                search_query: configContainer.querySelector('.config-search-query').value.trim(),
                search_type: configContainer.querySelector('.config-search-type').value
            };
            break;
        case 'arxiv':
            const categoriesSelect = configContainer.querySelector('.config-categories');
            const selectedCategories = Array.from(categoriesSelect.selectedOptions).map(option => option.value);
            
            sourceConfig = {
                search_query: configContainer.querySelector('.config-search-query').value.trim(),
                categories: selectedCategories,
                max_results: parseInt(configContainer.querySelector('.config-max-results').value) || 10,
                sort_by: configContainer.querySelector('.config-sort-by').value
            };
            break;
        case 'youtube':
            sourceConfig = {
                search_query: configContainer.querySelector('.config-search-query').value.trim(),
                max_results: parseInt(configContainer.querySelector('.config-max-results').value) || 10,
                content_type: configContainer.querySelector('.config-content-type').value,
                duration: configContainer.querySelector('.config-duration').value
            };
            break;
        case 'custom':
            let parameters = {};
            let headers = {};
            
            try {
                const parametersText = configContainer.querySelector('.config-parameters').value.trim();
                if (parametersText) {
                    parameters = JSON.parse(parametersText);
                }
                
                const headersText = configContainer.querySelector('.config-headers').value.trim();
                if (headersText) {
                    headers = JSON.parse(headersText);
                }
            } catch (error) {
                console.error('Error parsing JSON:', error);
                showToast('Validation Error', 'Invalid JSON in parameters or headers.', 'error');
            }
            
            sourceConfig = {
                api_endpoint: configContainer.querySelector('.config-api-endpoint').value.trim(),
                method: configContainer.querySelector('.config-method').value,
                parameters: parameters,
                headers: headers
            };
            break;
    }
    
    return sourceConfig;
}

/**
 * Create a new research flow
 */
function createResearchFlow(formData) {
    // Show loading state
    document.body.classList.add('wait');
    
    // Send the request to create the flow
    fetch('/research-flows', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to create research flow');
        }
        return response.json();
    })
    .then(data => {
        showToast('Success', 'Research flow created successfully', 'success');
        
        // Redirect to the flow details page
        setTimeout(() => {
            window.location.href = `/dashboard/parallel-research/${data.flow_id}`;
        }, 1000);
    })
    .catch(error => {
        console.error('Error creating research flow:', error);
        showToast('Error', 'Failed to create research flow. Please try again.', 'error');
        document.body.classList.remove('wait');
    });
}

/**
 * Save the current form as a template
 */
function saveAsTemplate() {
    // Validate the form
    if (!validateForm()) {
        return;
    }
    
    // Get form data
    const formData = getFormData();
    
    // Prompt for template name
    const templateName = prompt('Enter a name for this template:', formData.name);
    if (!templateName) {
        return; // User cancelled
    }
    
    // Create template object
    const template = {
        id: `template-${Date.now()}`,
        name: templateName,
        description: formData.description,
        tasks: formData.tasks
    };
    
    // Save to local storage
    saveTemplateToLocalStorage(template);
    
    // Show success message
    showToast('Success', 'Template saved successfully', 'success');
    
    // Reload templates
    loadTemplates();
}

/**
 * Save a template to local storage
 */
function saveTemplateToLocalStorage(template) {
    // Get existing templates
    let templates = JSON.parse(localStorage.getItem('researchFlowTemplates') || '[]');
    
    // Add the new template
    templates.push(template);
    
    // Save back to local storage
    localStorage.setItem('researchFlowTemplates', JSON.stringify(templates));
}

/**
 * Load templates from local storage
 */
function loadTemplates() {
    // Get templates from local storage
    flowTemplates = JSON.parse(localStorage.getItem('researchFlowTemplates') || '[]');
    
    // Clear the container
    templatesContainer.innerHTML = '';
    
    // If no templates, show message
    if (flowTemplates.length === 0) {
        templatesContainer.innerHTML = `
            <div class="col-12 text-center">
                <p>No templates available</p>
            </div>
        `;
        return;
    }
    
    // Render each template
    flowTemplates.forEach(template => {
        const templateCard = document.createElement('div');
        templateCard.className = 'col-md-4 mb-3';
        templateCard.innerHTML = `
            <div class="card template-card h-100" data-template-id="${template.id}">
                <div class="card-body">
                    <h5 class="card-title">${template.name}</h5>
                    <p class="card-text">${template.description || 'No description'}</p>
                    <p class="card-text"><small class="text-muted">${template.tasks.length} task(s)</small></p>
                </div>
                <div class="card-footer d-flex justify-content-between">
                    <button type="button" class="btn btn-sm btn-outline-primary load-template-btn" data-template-id="${template.id}">
                        Load Template
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-danger delete-template-btn" data-template-id="${template.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `;
        
        templatesContainer.appendChild(templateCard);
    });
    
    // Add event listeners to template buttons
    document.querySelectorAll('.load-template-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const templateId = e.currentTarget.getAttribute('data-template-id');
            loadTemplate(templateId);
        });
    });
    
    document.querySelectorAll('.delete-template-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const templateId = e.currentTarget.getAttribute('data-template-id');
            deleteTemplate(templateId);
        });
    });
}

/**
 * Load a template into the form
 */
function loadTemplate(templateId) {
    // Find the template
    const template = flowTemplates.find(t => t.id === templateId);
    if (!template) {
        console.error('Template not found:', templateId);
        return;
    }
    
    // Confirm with the user
    if (!confirm('Loading this template will replace your current form data. Continue?')) {
        return;
    }
    
    // Clear the form
    clearForm();
    
    // Fill in the form data
    document.getElementById('flow-name').value = template.name;
    document.getElementById('flow-description').value = template.description || '';
    
    // Add tasks
    template.tasks.forEach(task => {
        addTask();
        
        // Get the last added task
        const taskCard = tasksContainer.lastElementChild;
        
        // Fill in task data
        taskCard.querySelector('.task-name').value = task.name;
        taskCard.querySelector('.task-description').value = task.description || '';
        
        const sourceSelect = taskCard.querySelector('.task-source');
        sourceSelect.value = task.source;
        
        // Trigger the source type change event
        const event = new Event('change');
        sourceSelect.dispatchEvent(event);
        
        // Fill in source config
        fillSourceConfig(taskCard, task.source, task.source_config);
    });
    
    // Show success message
    showToast('Success', 'Template loaded successfully', 'success');
}

/**
 * Fill in source configuration fields
 */
function fillSourceConfig(taskCard, sourceType, sourceConfig) {
    const configContainer = taskCard.querySelector('.source-config-container');
    
    switch (sourceType) {
        case 'web':
            configContainer.querySelector('.config-search-query').value = sourceConfig.search_query || '';
            configContainer.querySelector('.config-max-results').value = sourceConfig.max_results || 10;
            configContainer.querySelector('.config-time-range').value = sourceConfig.time_range || 'any';
            break;
        case 'github':
            configContainer.querySelector('.config-repository').value = sourceConfig.repository || '';
            configContainer.querySelector('.config-search-query').value = sourceConfig.search_query || '';
            configContainer.querySelector('.config-search-type').value = sourceConfig.search_type || 'code';
            break;
        case 'arxiv':
            configContainer.querySelector('.config-search-query').value = sourceConfig.search_query || '';
            
            const categoriesSelect = configContainer.querySelector('.config-categories');
            if (sourceConfig.categories && Array.isArray(sourceConfig.categories)) {
                for (const option of categoriesSelect.options) {
                    option.selected = sourceConfig.categories.includes(option.value);
                }
            }
            
            configContainer.querySelector('.config-max-results').value = sourceConfig.max_results || 10;
            configContainer.querySelector('.config-sort-by').value = sourceConfig.sort_by || 'relevance';
            break;
        case 'youtube':
            configContainer.querySelector('.config-search-query').value = sourceConfig.search_query || '';
            configContainer.querySelector('.config-max-results').value = sourceConfig.max_results || 10;
            configContainer.querySelector('.config-content-type').value = sourceConfig.content_type || 'any';
            configContainer.querySelector('.config-duration').value = sourceConfig.duration || 'any';
            break;
        case 'custom':
            configContainer.querySelector('.config-api-endpoint').value = sourceConfig.api_endpoint || '';
            configContainer.querySelector('.config-method').value = sourceConfig.method || 'GET';
            
            if (sourceConfig.parameters) {
                configContainer.querySelector('.config-parameters').value = JSON.stringify(sourceConfig.parameters, null, 2);
            }
            
            if (sourceConfig.headers) {
                configContainer.querySelector('.config-headers').value = JSON.stringify(sourceConfig.headers, null, 2);
            }
            break;
    }
}

/**
 * Delete a template
 */
function deleteTemplate(templateId) {
    // Confirm with the user
    if (!confirm('Are you sure you want to delete this template? This action cannot be undone.')) {
        return;
    }
    
    // Get existing templates
    let templates = JSON.parse(localStorage.getItem('researchFlowTemplates') || '[]');
    
    // Filter out the template to delete
    templates = templates.filter(t => t.id !== templateId);
    
    // Save back to local storage
    localStorage.setItem('researchFlowTemplates', JSON.stringify(templates));
    
    // Show success message
    showToast('Success', 'Template deleted successfully', 'success');
    
    // Reload templates
    loadTemplates();
}

/**
 * Clear the form
 */
function clearForm() {
    // Clear flow name and description
    document.getElementById('flow-name').value = '';
    document.getElementById('flow-description').value = '';
    
    // Clear tasks
    tasksContainer.innerHTML = '';
    
    // Add one empty task
    addTask();
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

