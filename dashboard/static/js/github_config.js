/**
 * GitHub Configuration Dialog Handler
 * Manages the GitHub data mining configuration form
 */

document.addEventListener('DOMContentLoaded', function() {
    // Reference context handlers
    const addContextBtn = document.getElementById('add-context-btn');
    const referenceContexts = document.getElementById('reference-contexts');
    
    // Add new reference context input
    if (addContextBtn) {
        addContextBtn.addEventListener('click', function() {
            const newContext = document.createElement('div');
            newContext.className = 'input-group mb-2';
            newContext.innerHTML = `
                <input type="text" class="form-control" placeholder="Enter file path or URL" aria-label="Reference context">
                <button class="btn btn-outline-secondary remove-context" type="button">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            referenceContexts.appendChild(newContext);
            
            // Add event listener to the new remove button
            const removeBtn = newContext.querySelector('.remove-context');
            removeBtn.addEventListener('click', function() {
                newContext.remove();
            });
        });
    }
    
    // Add event listeners to existing remove buttons
    document.querySelectorAll('.remove-context').forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.input-group').remove();
        });
    });
    
    // Advanced options toggle
    const advancedOptionsToggle = document.getElementById('advanced-options-toggle');
    const advancedOptionsPanel = document.getElementById('advanced-options-panel');
    
    if (advancedOptionsToggle && advancedOptionsPanel) {
        advancedOptionsToggle.addEventListener('click', function() {
            const isExpanded = advancedOptionsToggle.getAttribute('aria-expanded') === 'true';
            advancedOptionsToggle.setAttribute('aria-expanded', !isExpanded);
            advancedOptionsPanel.classList.toggle('show');
            
            // Update the icon
            const icon = advancedOptionsToggle.querySelector('i');
            if (icon) {
                if (isExpanded) {
                    icon.classList.remove('bi-chevron-up');
                    icon.classList.add('bi-chevron-down');
                } else {
                    icon.classList.remove('bi-chevron-down');
                    icon.classList.add('bi-chevron-up');
                }
            }
        });
    }
    
    // Save template button handler
    const saveTemplateBtn = document.getElementById('save-template-btn');
    if (saveTemplateBtn) {
        saveTemplateBtn.addEventListener('click', function() {
            // Show the save template modal
            const saveTemplateModal = new bootstrap.Modal(document.getElementById('save-template-modal'));
            saveTemplateModal.show();
        });
    }
    
    // Confirm save template button handler
    const confirmSaveTemplateBtn = document.getElementById('confirm-save-template');
    if (confirmSaveTemplateBtn) {
        confirmSaveTemplateBtn.addEventListener('click', function() {
            const templateName = document.getElementById('template-name').value;
            const templateDescription = document.getElementById('template-description').value;
            
            // Validate template name
            if (!validators.required(templateName)) {
                showNotification('Please enter a template name', 'error');
                return;
            }
            
            // Get form data
            const templateData = getFormData();
            templateData.name = templateName;
            templateData.description = templateDescription;
            
            // Save template (in a real app, this would be an API call)
            saveTemplate(templateData);
        });
    }
    
    // Form submission handler
    const githubConfigForm = document.getElementById('github-config-form');
    if (githubConfigForm) {
        githubConfigForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validate form
            const customValidators = {
                'focus': validators.required,
                'parallel-workers': (value) => validators.numberRange(value, 1, 10),
                'cache-ttl': (value) => validators.numberRange(value, 0, 86400),
                'rate-limit-pause': (value) => validators.numberRange(value, 0, 3600),
                'max-retries': (value) => validators.numberRange(value, 0, 10),
                'timeout': (value) => validators.numberRange(value, 1, 300),
                'pool-connections': (value) => validators.numberRange(value, 1, 100),
                'pool-maxsize': (value) => validators.numberRange(value, 1, 100),
                'page-size': (value) => validators.numberRange(value, 1, 100)
            };
            
            if (!validateForm(githubConfigForm, customValidators)) {
                return;
            }
            
            // Get form data
            const formData = getFormData();
            
            // Start the data mining process (in a real app, this would be an API call)
            startDataMining(formData);
        });
    }
    
    // Cancel button handler
    const cancelBtn = document.getElementById('cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            window.location.href = '/data-mining';
        });
    }
    
    // Add keyboard navigation for better accessibility
    const focusableElements = githubConfigForm ? githubConfigForm.querySelectorAll('button, input, select, textarea, [tabindex]:not([tabindex="-1"])') : [];
    if (focusableElements.length > 0) {
        // Add keyboard navigation between form elements
        focusableElements.forEach((element, index) => {
            element.addEventListener('keydown', function(e) {
                // Handle tab navigation
                if (e.key === 'Tab') {
                    // No need to do anything, default behavior works
                } 
                // Handle arrow navigation
                else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                    e.preventDefault();
                    const nextElement = focusableElements[(index + 1) % focusableElements.length];
                    nextElement.focus();
                } 
                else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
                    e.preventDefault();
                    const prevElement = focusableElements[(index - 1 + focusableElements.length) % focusableElements.length];
                    prevElement.focus();
                }
            });
        });
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Function to get all form data
function getFormData() {
    const formData = {
        focus: document.getElementById('focus').value,
        description: document.getElementById('description').value,
        referenceContexts: [],
        searchScheme: document.getElementById('search-scheme').value,
        options: {
            searchRepositories: document.getElementById('search-repositories').checked,
            searchCode: document.getElementById('search-code').checked,
            searchIssues: document.getElementById('search-issues').checked,
            searchPullRequests: document.getElementById('search-pull-requests').checked
        },
        goal: document.getElementById('goal').value,
        parallelWorkers: parseInt(document.getElementById('parallel-workers').value),
        advancedOptions: {
            cloneRepositories: document.getElementById('clone-repositories').checked,
            followRepositoryLinks: document.getElementById('follow-repository-links').checked,
            includeForks: document.getElementById('include-forks').checked,
            saveFindings: document.getElementById('save-findings').checked
        },
        apiConfig: {
            cacheTTL: parseInt(document.getElementById('cache-ttl').value),
            rateLimitPause: parseInt(document.getElementById('rate-limit-pause').value),
            maxRetries: parseInt(document.getElementById('max-retries').value),
            timeout: parseInt(document.getElementById('timeout').value),
            poolConnections: parseInt(document.getElementById('pool-connections').value),
            poolMaxsize: parseInt(document.getElementById('pool-maxsize').value),
            pageSize: parseInt(document.getElementById('page-size').value)
        }
    };
    
    // Get all reference contexts
    document.querySelectorAll('#reference-contexts .input-group input').forEach(input => {
        if (input.value.trim()) {
            formData.referenceContexts.push(input.value.trim());
        }
    });
    
    return formData;
}

// Function to save a template
function saveTemplate(templateData) {
    console.log('Saving template:', templateData);
    
    // Show loading state
    showLoading('save-template-btn', 'Saving...');
    
    // In a real application, this would be an API call
    // For now, we'll simulate an API call with a timeout
    setTimeout(() => {
        try {
            // Hide the modal
            const saveTemplateModal = bootstrap.Modal.getInstance(document.getElementById('save-template-modal'));
            saveTemplateModal.hide();
            
            // Show success message
            showNotification('Template saved successfully', 'success');
            
            // Reset loading state
            hideLoading('save-template-btn');
        } catch (error) {
            console.error('Error saving template:', error);
            showNotification('Error saving template: ' + (error.message || 'Unknown error'), 'error');
            hideLoading('save-template-btn');
        }
    }, 1000);
}

// Function to start the data mining process
function startDataMining(formData) {
    console.log('Starting data mining with config:', formData);
    
    // Show loading state
    const startBtn = document.querySelector('#github-config-form button[type="submit"]');
    if (startBtn) {
        startBtn.disabled = true;
        startBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Starting...';
    }
    
    // In a real application, this would be an API call
    // For now, we'll simulate an API call with a timeout
    setTimeout(() => {
        try {
            // Show success message
            showNotification('Starting GitHub data mining process...', 'success');
            
            // Redirect to dashboard
            window.location.href = '/data-mining';
        } catch (error) {
            console.error('Error starting data mining:', error);
            showNotification('Error starting data mining: ' + (error.message || 'Unknown error'), 'error');
            
            // Reset button state
            if (startBtn) {
                startBtn.disabled = false;
                startBtn.innerHTML = 'Start';
            }
        }
    }, 1500);
}

// Function to show a notification
function showNotification(message, type = 'success') {
    // Create a toast notification
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

// Function to show a loading state
function showLoading(buttonId, message) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.disabled = true;
        button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${message}`;
    }
}

// Function to hide a loading state
function hideLoading(buttonId) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.disabled = false;
        button.innerHTML = button.getAttribute('data-bs-original-title') || 'Save as Template';
    }
}
