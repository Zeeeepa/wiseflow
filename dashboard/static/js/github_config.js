/**
 * GitHub Configuration Dialog
 * Handles the configuration of GitHub data mining tasks
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the GitHub configuration dialog
    initGitHubConfig();
});

/**
 * Initialize the GitHub configuration dialog
 */
function initGitHubConfig() {
    // Add event listener to the "Add More" button for reference contexts
    const addReferenceBtn = document.getElementById('add-reference-btn');
    if (addReferenceBtn) {
        addReferenceBtn.addEventListener('click', function() {
            addReferenceContextInput();
        });
    }
    
    // Add event listeners to remove reference context buttons
    setupRemoveReferenceButtons();
    
    // Add event listener to the cancel button
    const cancelBtn = document.getElementById('cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            window.location.href = '/data-mining';
        });
    }
    
    // Add event listener to the start button
    const startBtn = document.getElementById('start-btn');
    if (startBtn) {
        startBtn.addEventListener('click', function() {
            startGitHubDataMining();
        });
    }
    
    // Add event listener to the save template button
    const saveTemplateBtn = document.getElementById('save-template-btn');
    if (saveTemplateBtn) {
        saveTemplateBtn.addEventListener('click', function() {
            showSaveTemplateModal();
        });
    }
    
    // Add event listener to the confirm save template button
    const confirmSaveTemplateBtn = document.getElementById('confirm-save-template-btn');
    if (confirmSaveTemplateBtn) {
        confirmSaveTemplateBtn.addEventListener('click', function() {
            saveAsTemplate();
        });
    }
    
    // Load template if specified in URL
    const urlParams = new URLSearchParams(window.location.search);
    const templateId = urlParams.get('template');
    if (templateId) {
        loadTemplate(templateId);
    }
}

/**
 * Add a new reference context input field
 */
function addReferenceContextInput() {
    const referenceContexts = document.getElementById('reference-contexts');
    if (referenceContexts) {
        const inputGroup = document.createElement('div');
        inputGroup.className = 'input-group mb-2';
        
        inputGroup.innerHTML = `
            <input type="text" class="form-control" placeholder="File path or URL">
            <button class="btn btn-outline-danger remove-reference" type="button">
                <i class="bi bi-trash"></i>
            </button>
        `;
        
        referenceContexts.appendChild(inputGroup);
        
        // Add event listener to the new remove button
        const removeBtn = inputGroup.querySelector('.remove-reference');
        if (removeBtn) {
            removeBtn.addEventListener('click', function() {
                inputGroup.remove();
            });
        }
    }
}

/**
 * Setup event listeners for remove reference buttons
 */
function setupRemoveReferenceButtons() {
    const removeButtons = document.querySelectorAll('.remove-reference');
    removeButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.input-group').remove();
        });
    });
}

/**
 * Start GitHub data mining with the current configuration
 */
function startGitHubDataMining() {
    // Get form values
    const config = getFormValues();
    
    // Validate form
    if (!validateForm(config)) {
        return;
    }
    
    // Send the configuration to the server
    fetch('/api/data-mining/github/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Redirect to the data mining dashboard
            window.location.href = '/data-mining?task=' + data.taskId;
        } else {
            alert('Error starting data mining task: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error starting data mining task:', error);
        alert('Error starting data mining task. Please try again.');
    });
}

/**
 * Get all form values
 * @returns {Object} Form values
 */
function getFormValues() {
    // Get reference contexts
    const referenceContexts = [];
    document.querySelectorAll('#reference-contexts input').forEach(input => {
        if (input.value.trim()) {
            referenceContexts.push(input.value.trim());
        }
    });
    
    // Return form values
    return {
        focus: document.getElementById('focus').value.trim(),
        description: document.getElementById('description').value.trim(),
        referenceContexts: referenceContexts,
        searchScheme: document.getElementById('search-scheme').value,
        options: {
            searchRepositories: document.getElementById('search-repositories').checked,
            searchCode: document.getElementById('search-code').checked,
            searchIssues: document.getElementById('search-issues').checked,
            searchPullRequests: document.getElementById('search-pull-requests').checked
        },
        goal: document.getElementById('goal').value.trim(),
        parallelWorkers: parseInt(document.getElementById('parallel-workers').value),
        advancedOptions: {
            cloneRepositories: document.getElementById('clone-repositories').checked,
            followRepositoryLinks: document.getElementById('follow-repository-links').checked,
            includeForks: document.getElementById('include-forks').checked,
            saveFindings: document.getElementById('save-findings').checked
        }
    };
}

/**
 * Validate the form
 * @param {Object} config - Form values
 * @returns {boolean} True if valid, false otherwise
 */
function validateForm(config) {
    if (!config.focus) {
        alert('Please enter a focus for the data mining task.');
        return false;
    }
    
    if (!config.goal) {
        alert('Please enter a goal for the data mining task.');
        return false;
    }
    
    if (config.parallelWorkers < 1 || config.parallelWorkers > 10) {
        alert('Parallel workers must be between 1 and 10.');
        return false;
    }
    
    return true;
}

/**
 * Show the save template modal
 */
function showSaveTemplateModal() {
    const modal = new bootstrap.Modal(document.getElementById('save-template-modal'));
    modal.show();
}

/**
 * Save the current configuration as a template
 */
function saveAsTemplate() {
    const templateName = document.getElementById('template-name').value.trim();
    const templateDescription = document.getElementById('template-description').value.trim();
    
    if (!templateName) {
        alert('Please enter a name for the template.');
        return;
    }
    
    // Get form values
    const config = getFormValues();
    
    // Add template metadata
    config.templateName = templateName;
    config.templateDescription = templateDescription;
    config.templateType = 'github';
    
    // Send the template to the server
    fetch('/api/templates/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Hide the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('save-template-modal'));
            modal.hide();
            
            // Show success message
            alert('Template saved successfully!');
        } else {
            alert('Error saving template: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error saving template:', error);
        alert('Error saving template. Please try again.');
    });
}

/**
 * Load a template
 * @param {string} templateId - Template ID
 */
function loadTemplate(templateId) {
    fetch(`/api/templates/${templateId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Fill the form with template data
            fillFormWithTemplate(data.template);
        } else {
            alert('Error loading template: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error loading template:', error);
        alert('Error loading template. Please try again.');
    });
}

/**
 * Fill the form with template data
 * @param {Object} template - Template data
 */
function fillFormWithTemplate(template) {
    // Set basic fields
    document.getElementById('focus').value = template.focus || '';
    document.getElementById('description').value = template.description || '';
    document.getElementById('search-scheme').value = template.searchScheme || 'basic';
    document.getElementById('goal').value = template.goal || '';
    document.getElementById('parallel-workers').value = template.parallelWorkers || 4;
    
    // Set options
    if (template.options) {
        document.getElementById('search-repositories').checked = template.options.searchRepositories !== false;
        document.getElementById('search-code').checked = template.options.searchCode !== false;
        document.getElementById('search-issues').checked = template.options.searchIssues === true;
        document.getElementById('search-pull-requests').checked = template.options.searchPullRequests === true;
    }
    
    // Set advanced options
    if (template.advancedOptions) {
        document.getElementById('clone-repositories').checked = template.advancedOptions.cloneRepositories !== false;
        document.getElementById('follow-repository-links').checked = template.advancedOptions.followRepositoryLinks !== false;
        document.getElementById('include-forks').checked = template.advancedOptions.includeForks === true;
        document.getElementById('save-findings').checked = template.advancedOptions.saveFindings !== false;
    }
    
    // Set reference contexts
    if (template.referenceContexts && template.referenceContexts.length > 0) {
        // Clear existing reference contexts
        const referenceContexts = document.getElementById('reference-contexts');
        referenceContexts.innerHTML = '';
        
        // Add reference contexts from template
        template.referenceContexts.forEach(context => {
            const inputGroup = document.createElement('div');
            inputGroup.className = 'input-group mb-2';
            
            inputGroup.innerHTML = `
                <input type="text" class="form-control" placeholder="File path or URL" value="${context}">
                <button class="btn btn-outline-danger remove-reference" type="button">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            
            referenceContexts.appendChild(inputGroup);
        });
        
        // Setup remove buttons
        setupRemoveReferenceButtons();
    }
}

