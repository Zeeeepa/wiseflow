/**
 * GitHub Configuration Dialog JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const form = document.getElementById('github-config-form');
    const addReferenceBtn = document.getElementById('add-reference');
    const referenceContainer = document.getElementById('reference-context-container');
    const cancelButton = document.getElementById('cancel-button');
    const saveTemplateButton = document.getElementById('save-template-button');
    
    // Add more reference context fields
    addReferenceBtn.addEventListener('click', function() {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'reference-context full-width';
        input.name = 'reference-context[]';
        referenceContainer.appendChild(input);
    });
    
    // Form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate form
        if (!validateForm()) {
            return;
        }
        
        // Collect form data
        const formData = new FormData(form);
        const data = {
            focus: formData.get('focus'),
            description: formData.get('description'),
            references: Array.from(formData.getAll('reference-context[]')).filter(ref => ref.trim() !== ''),
            searchScheme: formData.get('search-scheme'),
            options: {
                searchRepos: formData.has('search-repos'),
                searchCode: formData.has('search-code'),
                searchIssues: formData.has('search-issues'),
                searchPRs: formData.has('search-prs')
            },
            goal: formData.get('goal'),
            parallelWorkers: parseInt(formData.get('parallel-workers'), 10),
            advancedOptions: {
                cloneRepos: formData.has('clone-repos'),
                followLinks: formData.has('follow-links'),
                includeForks: formData.has('include-forks'),
                saveFindings: formData.has('save-findings')
            }
        };
        
        // Send data to server
        fetch('/api/data-mining/github/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCSRFToken() // Add CSRF protection
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Handle successful response
            window.location.href = '/dashboard';
        })
        .catch(error => {
            console.error('Error starting GitHub data mining:', error);
            showToast('There was an error starting the data mining process. Please try again.', 'error');
        });
    });
    
    // Save as template
    saveTemplateButton.addEventListener('click', function() {
        // Validate form
        if (!validateForm()) {
            return;
        }
        
        // Collect form data
        const formData = new FormData(form);
        const data = {
            name: formData.get('focus'),
            type: 'github',
            config: {
                focus: formData.get('focus'),
                description: formData.get('description'),
                references: Array.from(formData.getAll('reference-context[]')).filter(ref => ref.trim() !== ''),
                searchScheme: formData.get('search-scheme'),
                options: {
                    searchRepos: formData.has('search-repos'),
                    searchCode: formData.has('search-code'),
                    searchIssues: formData.has('search-issues'),
                    searchPRs: formData.has('search-prs')
                },
                goal: formData.get('goal'),
                parallelWorkers: parseInt(formData.get('parallel-workers'), 10),
                advancedOptions: {
                    cloneRepos: formData.has('clone-repos'),
                    followLinks: formData.has('follow-links'),
                    includeForks: formData.has('include-forks'),
                    saveFindings: formData.has('save-findings')
                }
            }
        };
        
        // Send data to server
        fetch('/api/templates/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCSRFToken() // Add CSRF protection
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            showToast('Template saved successfully!', 'success');
        })
        .catch(error => {
            console.error('Error saving template:', error);
            showToast('There was an error saving the template. Please try again.', 'error');
        });
    });
    
    // Cancel button
    cancelButton.addEventListener('click', function() {
        window.location.href = '/dashboard';
    });
    
    /**
     * Validate the form inputs
     * @returns {boolean} True if validation passes, false otherwise
     */
    function validateForm() {
        // Required fields
        const focus = document.getElementById('focus').value.trim();
        if (!focus) {
            showToast('Please enter a focus for your data mining task.', 'error');
            document.getElementById('focus').focus();
            return false;
        }
        
        // Validate goal field
        const goal = document.getElementById('goal').value.trim();
        if (!goal) {
            showToast('Please enter a goal for your data mining task.', 'error');
            document.getElementById('goal').focus();
            return false;
        }
        
        // Validate parallel workers
        const parallelWorkers = parseInt(document.getElementById('parallel-workers').value, 10);
        if (isNaN(parallelWorkers) || parallelWorkers < 1 || parallelWorkers > 10) {
            showToast('Parallel workers must be a number between 1 and 10.', 'error');
            document.getElementById('parallel-workers').focus();
            return false;
        }
        
        // Validate at least one search option is selected
        const searchRepos = document.getElementById('search-repos').checked;
        const searchCode = document.getElementById('search-code').checked;
        const searchIssues = document.getElementById('search-issues').checked;
        const searchPRs = document.getElementById('search-prs').checked;
        
        if (!searchRepos && !searchCode && !searchIssues && !searchPRs) {
            showToast('Please select at least one search option.', 'error');
            return false;
        }
        
        // Validate references
        const references = Array.from(document.querySelectorAll('.reference-context'))
            .map(input => input.value.trim())
            .filter(ref => ref !== '');
            
        // Validate URL format for references
        for (const ref of references) {
            if (ref.startsWith('http')) {
                try {
                    new URL(ref);
                } catch (e) {
                    showToast(`Invalid URL format: ${ref}`, 'error');
                    return false;
                }
            }
        }
        
        return true;
    }
    
    /**
     * Show a toast message
     * @param {string} message - The message to show
     * @param {string} type - The type of toast (success, error, warning, info)
     */
    function showToast(message, type = 'success') {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type}`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add the toast to the container
        toastContainer.appendChild(toastEl);
        
        // Initialize and show the toast
        const toast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 3000
        });
        
        toast.show();
        
        // Remove the toast element after it's hidden
        toastEl.addEventListener('hidden.bs.toast', function() {
            toastEl.remove();
        });
    }
    
    /**
     * Get CSRF token from meta tag
     * @returns {string} CSRF token
     */
    function getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
});
