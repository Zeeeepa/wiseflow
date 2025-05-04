/**
 * Settings Page JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
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
        fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
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
            alert('Settings saved successfully!');
            // Optionally redirect
            // window.location.href = '/dashboard';
        })
        .catch(error => {
            console.error('Error saving settings:', error);
            alert('There was an error saving your settings. Please try again.');
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
});

