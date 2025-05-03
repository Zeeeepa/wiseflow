// Settings JavaScript

// Initialize the settings page
document.addEventListener('DOMContentLoaded', function() {
    // Set up event listeners for collapsible sections
    const collapsibleButtons = document.querySelectorAll('.card-header button');
    collapsibleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const icon = this.querySelector('i');
            if (icon.classList.contains('bi-chevron-down')) {
                icon.classList.replace('bi-chevron-down', 'bi-chevron-up');
            } else {
                icon.classList.replace('bi-chevron-up', 'bi-chevron-down');
            }
        });
    });

    // Set up event listeners for range inputs
    const cpuLimit = document.getElementById('cpuLimit');
    const cpuLimitValue = document.getElementById('cpuLimitValue');
    if (cpuLimit && cpuLimitValue) {
        cpuLimit.addEventListener('input', function() {
            cpuLimitValue.textContent = this.value + '%';
        });
    }

    const memoryLimit = document.getElementById('memoryLimit');
    const memoryLimitValue = document.getElementById('memoryLimitValue');
    if (memoryLimit && memoryLimitValue) {
        memoryLimit.addEventListener('input', function() {
            memoryLimitValue.textContent = this.value + '%';
        });
    }

    // Set up event listeners for password toggle buttons
    setupPasswordToggle('toggleGithubKey', 'githubApiKey');
    setupPasswordToggle('toggleGoogleKey', 'googleApiKey');
    setupPasswordToggle('toggleBingKey', 'bingApiKey');
    setupPasswordToggle('toggleSearchId', 'customSearchId');
    setupPasswordToggle('toggleYoutubeKey', 'youtubeApiKey');

    // Set up event listeners for save and reset buttons
    const saveButton = document.getElementById('saveButton');
    if (saveButton) {
        saveButton.addEventListener('click', saveSettings);
    }

    const resetButton = document.getElementById('resetButton');
    if (resetButton) {
        resetButton.addEventListener('click', resetSettings);
    }

    // Load settings from localStorage if available
    loadSettings();
});

// Function to toggle password visibility
function setupPasswordToggle(buttonId, inputId) {
    const toggleButton = document.getElementById(buttonId);
    const input = document.getElementById(inputId);
    
    if (toggleButton && input) {
        toggleButton.addEventListener('click', function() {
            const icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.replace('bi-eye', 'bi-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.replace('bi-eye-slash', 'bi-eye');
            }
        });
    }
}

// Function to save settings
function saveSettings() {
    try {
        const settings = {
            interface: {
                darkMode: document.getElementById('darkMode').checked,
                compactView: document.getElementById('compactView').checked,
                showTooltips: document.getElementById('showTooltips').checked,
                refreshRate: document.getElementById('refreshRate').value
            },
            database: {
                storageLocation: document.getElementById('storageLocation').value,
                autoBackup: document.getElementById('autoBackup').value,
                retentionPeriod: document.getElementById('retentionPeriod').value
            },
            processing: {
                maxParallelTasks: document.getElementById('maxParallelTasks').value,
                defaultWorkers: document.getElementById('defaultWorkers').value,
                cpuLimit: document.getElementById('cpuLimit').value,
                memoryLimit: document.getElementById('memoryLimit').value
            },
            apiKeys: {
                github: {
                    apiKey: document.getElementById('githubApiKey').value,
                    rateLimit: document.getElementById('githubRateLimit').value
                },
                searchEngines: {
                    googleApiKey: document.getElementById('googleApiKey').value,
                    bingApiKey: document.getElementById('bingApiKey').value,
                    customSearchId: document.getElementById('customSearchId').value
                },
                youtube: {
                    apiKey: document.getElementById('youtubeApiKey').value,
                    rateLimit: document.getElementById('youtubeRateLimit').value
                },
                arxiv: {
                    email: document.getElementById('arxivEmail').value,
                    rateLimit: document.getElementById('arxivRateLimit').value
                }
            }
        };

        // In a real application, this would be sent to the server
        // For demonstration, we'll save to localStorage
        localStorage.setItem('wiseflowSettings', JSON.stringify(settings));
        
        // Show success message
        showAlert('Settings saved successfully!', 'success');
        
        // In a real application, you would also make an API call:
        // fetch('/api/settings', {
        //     method: 'POST',
        //     headers: {
        //         'Content-Type': 'application/json'
        //     },
        //     body: JSON.stringify(settings)
        // })
        // .then(response => response.json())
        // .then(data => {
        //     showAlert('Settings saved successfully!', 'success');
        // })
        // .catch(error => {
        //     console.error('Error saving settings:', error);
        //     showAlert('Error saving settings: ' + error.message, 'danger');
        // });
    } catch (error) {
        console.error('Error saving settings:', error);
        showAlert('Error saving settings: ' + error.message, 'danger');
    }
}

// Function to reset settings to defaults
function resetSettings() {
    if (confirm('Are you sure you want to reset all settings to default values?')) {
        // Default settings
        const defaultSettings = {
            interface: {
                darkMode: true,
                compactView: true,
                showTooltips: false,
                refreshRate: '30'
            },
            database: {
                storageLocation: '/data/findings',
                autoBackup: 'daily',
                retentionPeriod: '90'
            },
            processing: {
                maxParallelTasks: '8',
                defaultWorkers: '4',
                cpuLimit: '80',
                memoryLimit: '70'
            },
            apiKeys: {
                github: {
                    apiKey: '************************',
                    rateLimit: '5000 requests/hour'
                },
                searchEngines: {
                    googleApiKey: '************************',
                    bingApiKey: '************************',
                    customSearchId: '******************'
                },
                youtube: {
                    apiKey: '************************',
                    rateLimit: '10000 units/day'
                },
                arxiv: {
                    email: 'user@example.com',
                    rateLimit: '100 requests/minute'
                }
            }
        };

        // Apply default settings to form
        applySettings(defaultSettings);
        
        // Save default settings to localStorage
        localStorage.setItem('wiseflowSettings', JSON.stringify(defaultSettings));
        
        // Show success message
        showAlert('Settings reset to defaults!', 'success');
    }
}

// Function to load settings from localStorage
function loadSettings() {
    try {
        const savedSettings = localStorage.getItem('wiseflowSettings');
        if (savedSettings) {
            const settings = JSON.parse(savedSettings);
            applySettings(settings);
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

// Function to apply settings to form
function applySettings(settings) {
    // Interface settings
    document.getElementById('darkMode').checked = settings.interface.darkMode;
    document.getElementById('compactView').checked = settings.interface.compactView;
    document.getElementById('showTooltips').checked = settings.interface.showTooltips;
    document.getElementById('refreshRate').value = settings.interface.refreshRate;
    
    // Database settings
    document.getElementById('storageLocation').value = settings.database.storageLocation;
    document.getElementById('autoBackup').value = settings.database.autoBackup;
    document.getElementById('retentionPeriod').value = settings.database.retentionPeriod;
    
    // Processing settings
    document.getElementById('maxParallelTasks').value = settings.processing.maxParallelTasks;
    document.getElementById('defaultWorkers').value = settings.processing.defaultWorkers;
    document.getElementById('cpuLimit').value = settings.processing.cpuLimit;
    document.getElementById('cpuLimitValue').textContent = settings.processing.cpuLimit + '%';
    document.getElementById('memoryLimit').value = settings.processing.memoryLimit;
    document.getElementById('memoryLimitValue').textContent = settings.processing.memoryLimit + '%';
    
    // API Keys settings
    document.getElementById('githubApiKey').value = settings.apiKeys.github.apiKey;
    document.getElementById('githubRateLimit').value = settings.apiKeys.github.rateLimit;
    document.getElementById('googleApiKey').value = settings.apiKeys.searchEngines.googleApiKey;
    document.getElementById('bingApiKey').value = settings.apiKeys.searchEngines.bingApiKey;
    document.getElementById('customSearchId').value = settings.apiKeys.searchEngines.customSearchId;
    document.getElementById('youtubeApiKey').value = settings.apiKeys.youtube.apiKey;
    document.getElementById('youtubeRateLimit').value = settings.apiKeys.youtube.rateLimit;
    document.getElementById('arxivEmail').value = settings.apiKeys.arxiv.email;
    document.getElementById('arxivRateLimit').value = settings.apiKeys.arxiv.rateLimit;
}

// Function to show alert messages
function showAlert(message, type) {
    // Check if alert container exists, if not create it
    let alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alertContainer';
        alertContainer.style.position = 'fixed';
        alertContainer.style.top = '20px';
        alertContainer.style.right = '20px';
        alertContainer.style.zIndex = '1050';
        document.body.appendChild(alertContainer);
    }
    
    // Create alert element
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type} alert-dismissible fade show`;
    alertElement.role = 'alert';
    alertElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add alert to container
    alertContainer.appendChild(alertElement);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertElement);
        bsAlert.close();
    }, 5000);
}

