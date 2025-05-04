/**
 * Settings Interface
 * Handles the application settings functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the settings interface
    initSettings();
});

/**
 * Initialize the settings interface
 */
function initSettings() {
    // Add event listeners to the range inputs
    const cpuLimit = document.getElementById('cpu-limit');
    const cpuLimitValue = document.getElementById('cpu-limit-value');
    
    if (cpuLimit && cpuLimitValue) {
        cpuLimit.addEventListener('input', function() {
            cpuLimitValue.textContent = this.value + '%';
        });
    }
    
    const memoryLimit = document.getElementById('memory-limit');
    const memoryLimitValue = document.getElementById('memory-limit-value');
    
    if (memoryLimit && memoryLimitValue) {
        memoryLimit.addEventListener('input', function() {
            memoryLimitValue.textContent = this.value + '%';
        });
    }
    
    // Add event listeners to the toggle password buttons
    setupPasswordToggles();
    
    // Add event listener to the reset defaults button
    const resetDefaultsBtn = document.getElementById('reset-defaults-btn');
    if (resetDefaultsBtn) {
        resetDefaultsBtn.addEventListener('click', function() {
            showResetConfirmationModal();
        });
    }
    
    // Add event listener to the confirm reset button
    const confirmResetBtn = document.getElementById('confirm-reset-btn');
    if (confirmResetBtn) {
        confirmResetBtn.addEventListener('click', function() {
            resetToDefaults();
        });
    }
    
    // Add event listener to the save settings button
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', function() {
            saveSettings();
        });
    }
    
    // Add event listeners to the test connection buttons
    const testGithubConnectionBtn = document.getElementById('test-github-connection');
    if (testGithubConnectionBtn) {
        testGithubConnectionBtn.addEventListener('click', function() {
            testConnection('github');
        });
    }
    
    const testYoutubeConnectionBtn = document.getElementById('test-youtube-connection');
    if (testYoutubeConnectionBtn) {
        testYoutubeConnectionBtn.addEventListener('click', function() {
            testConnection('youtube');
        });
    }
}

/**
 * Setup password toggle buttons
 */
function setupPasswordToggles() {
    const toggleButtons = [
        { buttonId: 'toggle-github-key', inputId: 'github-api-key' },
        { buttonId: 'toggle-google-key', inputId: 'google-api-key' },
        { buttonId: 'toggle-bing-key', inputId: 'bing-api-key' },
        { buttonId: 'toggle-youtube-key', inputId: 'youtube-api-key' }
    ];
    
    toggleButtons.forEach(item => {
        const button = document.getElementById(item.buttonId);
        const input = document.getElementById(item.inputId);
        
        if (button && input) {
            button.addEventListener('click', function() {
                const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
                input.setAttribute('type', type);
                
                // Toggle the eye icon
                const icon = this.querySelector('i');
                if (icon) {
                    icon.classList.toggle('bi-eye');
                    icon.classList.toggle('bi-eye-slash');
                }
            });
        }
    });
}

/**
 * Show the reset confirmation modal
 */
function showResetConfirmationModal() {
    const modal = new bootstrap.Modal(document.getElementById('reset-confirmation-modal'));
    modal.show();
}

/**
 * Reset all settings to their default values
 */
function resetToDefaults() {
    // Interface settings
    document.getElementById('dark-mode').checked = true;
    document.getElementById('compact-view').checked = true;
    document.getElementById('show-tooltips').checked = false;
    document.getElementById('refresh-rate').value = '30';
    
    // Database settings
    document.getElementById('storage-location').value = '/data/findings';
    document.getElementById('auto-backup').value = 'daily';
    document.getElementById('retention-period').value = '90';
    
    // Processing settings
    document.getElementById('max-parallel-tasks').value = '8';
    document.getElementById('default-workers').value = '4';
    document.getElementById('cpu-limit').value = '80';
    document.getElementById('cpu-limit-value').textContent = '80%';
    document.getElementById('memory-limit').value = '70';
    document.getElementById('memory-limit-value').textContent = '70%';
    
    // GitHub settings
    document.getElementById('github-api-key').value = '************************';
    
    // Search engines settings
    document.getElementById('google-api-key').value = '************************';
    document.getElementById('bing-api-key').value = '************************';
    document.getElementById('custom-search-engine-id').value = '******************';
    
    // YouTube settings
    document.getElementById('youtube-api-key').value = '************************';
    
    // ArXiv settings
    document.getElementById('arxiv-email').value = 'user@example.com';
    
    // Hide the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('reset-confirmation-modal'));
    modal.hide();
    
    // Show success message
    showToast('Settings reset to defaults');
}

/**
 * Save the current settings
 */
function saveSettings() {
    // Get all settings
    const settings = {
        interface: {
            darkMode: document.getElementById('dark-mode').checked,
            compactView: document.getElementById('compact-view').checked,
            showTooltips: document.getElementById('show-tooltips').checked,
            refreshRate: parseInt(document.getElementById('refresh-rate').value)
        },
        database: {
            storageLocation: document.getElementById('storage-location').value,
            autoBackup: document.getElementById('auto-backup').value,
            retentionPeriod: parseInt(document.getElementById('retention-period').value)
        },
        processing: {
            maxParallelTasks: parseInt(document.getElementById('max-parallel-tasks').value),
            defaultWorkers: parseInt(document.getElementById('default-workers').value),
            cpuLimit: parseInt(document.getElementById('cpu-limit').value),
            memoryLimit: parseInt(document.getElementById('memory-limit').value)
        },
        github: {
            apiKey: document.getElementById('github-api-key').value
        },
        searchEngines: {
            googleApiKey: document.getElementById('google-api-key').value,
            bingApiKey: document.getElementById('bing-api-key').value,
            customSearchEngineId: document.getElementById('custom-search-engine-id').value
        },
        youtube: {
            apiKey: document.getElementById('youtube-api-key').value
        },
        arxiv: {
            email: document.getElementById('arxiv-email').value
        }
    };
    
    // Save the settings (in a real application, this would be sent to the server)
    console.log('Saving settings:', settings);
    
    // Show success message
    showToast('Settings saved successfully');
}

/**
 * Test a connection to an API
 * @param {string} service - The service to test (github, youtube, etc.)
 */
function testConnection(service) {
    // Get the API key
    let apiKey = '';
    
    switch (service) {
        case 'github':
            apiKey = document.getElementById('github-api-key').value;
            break;
        case 'youtube':
            apiKey = document.getElementById('youtube-api-key').value;
            break;
        default:
            console.error('Unknown service:', service);
            return;
    }
    
    // Check if the API key is set
    if (!apiKey || apiKey === '************************') {
        showToast('Please enter a valid API key', 'error');
        return;
    }
    
    // Show loading state
    const button = document.getElementById(`test-${service}-connection`);
    const originalText = button.textContent;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Testing...';
    button.disabled = true;
    
    // Simulate API call
    setTimeout(() => {
        // Reset button state
        button.innerHTML = originalText;
        button.disabled = false;
        
        // Show success message
        showToast(`${service.charAt(0).toUpperCase() + service.slice(1)} API connection successful`);
    }, 1500);
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

