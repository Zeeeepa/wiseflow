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
    // DOM Elements
    const form = document.getElementById('settings-form');
    const toggleButtons = document.querySelectorAll('.toggle-btn');
    const showHideButtons = document.querySelectorAll('.show-hide-btn');
    const cancelButton = document.getElementById('cancel-button');
    const resetButton = document.getElementById('reset-defaults-button');
    const cpuLimitSlider = document.getElementById('cpu-limit');
    const cpuLimitValue = document.getElementById('cpu-limit-value');
    const memoryLimitSlider = document.getElementById('memory-limit');
    const memoryLimitValue = document.getElementById('memory-limit-value');
    
    // Initialize settings from server
    fetchSettings();
    
    // Toggle settings groups
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const targetContent = document.getElementById(targetId);
            
            if (targetContent.classList.contains('expanded')) {
                targetContent.classList.remove('expanded');
                this.classList.remove('expanded');
                this.textContent = '▶';
            } else {
                targetContent.classList.add('expanded');
                this.classList.add('expanded');
                this.textContent = '▼';
            }
        });
    });
    
    // Show/hide password fields
    showHideButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const targetInput = document.getElementById(targetId);
            
            if (targetInput.type === 'password') {
                targetInput.type = 'text';
                this.textContent = 'Hide';
            } else {
                targetInput.type = 'password';
                this.textContent = 'Show';
            }
        });
    });
    
    // Update slider value displays
    cpuLimitSlider.addEventListener('input', function() {
        cpuLimitValue.textContent = this.value + '%';
    });
    
    memoryLimitSlider.addEventListener('input', function() {
        memoryLimitValue.textContent = this.value + '%';
    });
    
    // Form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Collect form data
        const formData = new FormData(form);
        const data = {
            interface: {
                darkMode: formData.has('dark-mode'),
                compactView: formData.has('compact-view'),
                showTooltips: formData.has('show-tooltips'),
                refreshRate: formData.get('refresh-rate')
            },
            database: {
                storageLocation: formData.get('storage-location'),
                autoBackup: formData.get('auto-backup'),
                retentionPeriod: formData.get('retention-period')
            },
            processing: {
                maxParallelTasks: parseInt(formData.get('max-parallel-tasks'), 10),
                defaultWorkers: parseInt(formData.get('default-workers'), 10),
                cpuLimit: parseInt(formData.get('cpu-limit'), 10),
                memoryLimit: parseInt(formData.get('memory-limit'), 10)
            },
            apiKeys: {
                github: formData.get('github-api-key'),
                google: formData.get('google-api-key'),
                bing: formData.get('bing-api-key'),
                customSearchId: formData.get('custom-search-id'),
                youtube: formData.get('youtube-api-key'),
                arxivEmail: formData.get('arxiv-email')
            }
        };
        
        // Send data to server
        saveSettings(data);
    });
    
    // Reset to defaults
    resetButton.addEventListener('click', function() {
        if (confirm('Are you sure you want to reset all settings to their default values?')) {
            resetSettings();
        }
    });
    
    // Cancel button
    cancelButton.addEventListener('click', function() {
        window.location.href = '/dashboard';
    });
    
    // Fetch settings from server
    function fetchSettings() {
        fetch('/api/settings')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Populate form with settings
                populateSettings(data);
            })
            .catch(error => {
                console.error('Error fetching settings:', error);
                alert('There was an error loading your settings. Please try refreshing the page.');
            });
    }
    
    // Populate form with settings
    function populateSettings(data) {
        // Interface settings
        document.getElementById('dark-mode').checked = data.interface.darkMode;
        document.getElementById('compact-view').checked = data.interface.compactView;
        document.getElementById('show-tooltips').checked = data.interface.showTooltips;
        document.getElementById('refresh-rate').value = data.interface.refreshRate;
        
        // Database settings
        document.getElementById('storage-location').value = data.database.storageLocation;
        document.getElementById('auto-backup').value = data.database.autoBackup;
        document.getElementById('retention-period').value = data.database.retentionPeriod;
        
        // Processing settings
        document.getElementById('max-parallel-tasks').value = data.processing.maxParallelTasks;
        document.getElementById('default-workers').value = data.processing.defaultWorkers;
        document.getElementById('cpu-limit').value = data.processing.cpuLimit;
        cpuLimitValue.textContent = data.processing.cpuLimit + '%';
        document.getElementById('memory-limit').value = data.processing.memoryLimit;
        memoryLimitValue.textContent = data.processing.memoryLimit + '%';
        
        // API Keys
        // Note: We don't show the actual API keys for security reasons
        // The server should send placeholder values like '************************'
    }
    
    // Save settings to server
    function saveSettings(data) {
        // Validate sensitive fields before saving
        if (!validateApiKeys()) {
            return;
        }

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
            apiKeys: secureApiKeys()
        };
        
        // Save the settings (in a real application, this would be sent to the server)
        console.log('Saving settings:', settings);
        
        // Send settings to server using secure connection
        fetch('/api/settings/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCSRFToken() // Add CSRF protection
            },
            body: JSON.stringify(settings)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to save settings');
            }
            return response.json();
        })
        .then(data => {
            showToast('Settings saved successfully');
        })
        .catch(error => {
            console.error('Error saving settings:', error);
            showToast('Failed to save settings. Please try again.', 'error');
        });
    }
    
    // Reset settings to defaults
    function resetSettings() {
        fetch('/api/settings/reset', {
            method: 'POST'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            alert('Settings have been reset to defaults.');
            // Reload settings
            fetchSettings();
        })
        .catch(error => {
            console.error('Error resetting settings:', error);
            alert('There was an error resetting your settings. Please try again.');
        });
    }
}

/**
 * Save the current settings
 */
function saveSettings() {
    // Validate sensitive fields before saving
    if (!validateApiKeys()) {
        return;
    }

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
        apiKeys: secureApiKeys()
    };
    
    // Save the settings (in a real application, this would be sent to the server)
    console.log('Saving settings:', settings);
    
    // Send settings to server using secure connection
    fetch('/api/settings/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': getCSRFToken() // Add CSRF protection
        },
        body: JSON.stringify(settings)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to save settings');
        }
        return response.json();
    })
    .then(data => {
        showToast('Settings saved successfully');
    })
    .catch(error => {
        console.error('Error saving settings:', error);
        showToast('Failed to save settings. Please try again.', 'error');
    });
}

/**
 * Validate API keys before saving
 * @returns {boolean} True if validation passes, false otherwise
 */
function validateApiKeys() {
    const apiKeyFields = [
        { id: 'github-api-key', name: 'GitHub API Key' },
        { id: 'google-api-key', name: 'Google API Key' },
        { id: 'bing-api-key', name: 'Bing API Key' },
        { id: 'youtube-api-key', name: 'YouTube API Key' }
    ];
    
    for (const field of apiKeyFields) {
        const value = document.getElementById(field.id).value;
        
        // Skip validation for masked values (unchanged)
        if (value === '************************') {
            continue;
        }
        
        // Basic validation - API keys should be at least 10 characters
        if (value && value.length < 10) {
            showToast(`${field.name} appears to be invalid. API keys are typically longer.`, 'error');
            document.getElementById(field.id).focus();
            return false;
        }
    }
    
    return true;
}

/**
 * Securely handle API keys for transmission
 * @returns {Object} Object containing API keys
 */
function secureApiKeys() {
    const apiKeys = {};
    const apiKeyFields = [
        { id: 'github-api-key', key: 'github' },
        { id: 'google-api-key', key: 'google' },
        { id: 'bing-api-key', key: 'bing' },
        { id: 'youtube-api-key', key: 'youtube' },
        { id: 'custom-search-engine-id', key: 'customSearchId' },
        { id: 'arxiv-email', key: 'arxivEmail' }
    ];
    
    for (const field of apiKeyFields) {
        const element = document.getElementById(field.id);
        const value = element.value;
        
        // Only send if the value has changed from the placeholder
        if (value !== '************************' && value !== '******************') {
            // In a real implementation, we would encrypt sensitive data here
            // For this demo, we'll just set the value
            apiKeys[field.key] = value;
        } else {
            // For unchanged values, send a special flag to indicate no change
            apiKeys[field.key] = '__UNCHANGED__';
        }
    }
    
    return apiKeys;
}

/**
 * Get CSRF token from meta tag
 * @returns {string} CSRF token
 */
function getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}
