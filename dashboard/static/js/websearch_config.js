/**
 * WebSearch Configuration Dialog Handler
 * Manages the WebSearch data mining configuration form
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
    
    // Custom search engine toggle
    const customEngineCheckbox = document.getElementById('custom-engine');
    const customEngineUrlInput = document.getElementById('custom-engine-url');
    
    if (customEngineCheckbox && customEngineUrlInput) {
        customEngineCheckbox.addEventListener('change', function() {
            customEngineUrlInput.disabled = !this.checked;
            if (this.checked) {
                customEngineUrlInput.focus();
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
            
            if (!templateName) {
                alert('Please enter a template name');
                return;
            }
            
            // Get form data
            const templateData = getFormData();
            templateData.name = templateName;
            templateData.description = templateDescription;
            
            // Save template (in a real app, this would be an API call)
            saveTemplate(templateData);
            
            // Hide the modal
            const saveTemplateModal = bootstrap.Modal.getInstance(document.getElementById('save-template-modal'));
            saveTemplateModal.hide();
            
            // Show success message
            showNotification('Template saved successfully');
        });
    }
    
    // Form submission handler
    const websearchConfigForm = document.getElementById('websearch-config-form');
    if (websearchConfigForm) {
        websearchConfigForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const formData = getFormData();
            
            // Start the data mining process (in a real app, this would be an API call)
            startDataMining(formData);
        });
    }
});

// Function to get all form data
function getFormData() {
    const formData = {
        focus: document.getElementById('focus').value,
        description: document.getElementById('description').value,
        referenceContexts: [],
        searchEngines: {
            google: document.getElementById('google-engine').checked,
            bing: document.getElementById('bing-engine').checked,
            duckduckgo: document.getElementById('duckduckgo-engine').checked,
            baidu: document.getElementById('baidu-engine').checked,
            custom: document.getElementById('custom-engine').checked ? document.getElementById('custom-engine-url').value : null
        },
        contentTypes: {
            articles: document.getElementById('articles-content').checked,
            blogs: document.getElementById('blogs-content').checked,
            documentation: document.getElementById('documentation-content').checked,
            forums: document.getElementById('forums-content').checked,
            news: document.getElementById('news-content').checked,
            academic: document.getElementById('academic-content').checked
        },
        timeRange: document.getElementById('time-range').value,
        maxResults: parseInt(document.getElementById('max-results').value),
        searchDepth: document.getElementById('search-depth').value,
        parallelWorkers: parseInt(document.getElementById('parallel-workers').value),
        advancedOptions: {
            extractCode: document.getElementById('extract-code').checked,
            followLinks: document.getElementById('follow-links').checked,
            saveFindings: document.getElementById('save-findings').checked,
            useProxy: document.getElementById('use-proxy').checked
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
    
    // In a real application, this would be an API call
    // For now, we'll just log to console
    
    // Example API call:
    // fetch('/api/templates', {
    //     method: 'POST',
    //     headers: {
    //         'Content-Type': 'application/json',
    //     },
    //     body: JSON.stringify(templateData),
    // })
    // .then(response => response.json())
    // .then(data => {
    //     console.log('Template saved:', data);
    //     showNotification('Template saved successfully');
    // })
    // .catch(error => {
    //     console.error('Error saving template:', error);
    //     showNotification('Error saving template', 'error');
    // });
}

// Function to start the data mining process
function startDataMining(formData) {
    console.log('Starting data mining with config:', formData);
    
    // In a real application, this would be an API call
    // For now, we'll just redirect to the dashboard
    
    // Example API call:
    // fetch('/api/data-mining/websearch', {
    //     method: 'POST',
    //     headers: {
    //         'Content-Type': 'application/json',
    //     },
    //     body: JSON.stringify(formData),
    // })
    // .then(response => response.json())
    // .then(data => {
    //     console.log('Data mining started:', data);
    //     window.location.href = '/dashboard';
    // })
    // .catch(error => {
    //     console.error('Error starting data mining:', error);
    //     showNotification('Error starting data mining', 'error');
    // });
    
    // Simulate API call and redirect
    showNotification('Starting WebSearch data mining process...');
    
    setTimeout(() => {
        window.location.href = '/dashboard';
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

