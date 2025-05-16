// YouTube Configuration Dialog JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize YouTube Configuration Dialog
    initYouTubeConfigDialog();
});

// Initialize YouTube Configuration Dialog
function initYouTubeConfigDialog() {
    // Add event listeners for range inputs to update displayed values
    document.getElementById('youtube-max-results').addEventListener('input', function() {
        document.getElementById('youtube-max-results-value').textContent = this.value;
    });
    
    document.getElementById('youtube-workers').addEventListener('input', function() {
        document.getElementById('youtube-workers-value').textContent = this.value;
    });
    
    // Add event listener for API key checkbox
    document.getElementById('youtube-use-api-key').addEventListener('change', function() {
        document.getElementById('youtube-api-key').disabled = !this.checked;
    });
    
    // Add event listener for adding more reference fields
    document.getElementById('youtube-add-reference-btn').addEventListener('click', function() {
        const referenceContainer = document.getElementById('youtube-reference-container');
        const newReferenceField = document.createElement('div');
        newReferenceField.className = 'input-group mb-2';
        newReferenceField.innerHTML = `
            <input type="text" class="form-control youtube-reference" placeholder="Enter file path or URL...">
            <button class="btn btn-outline-danger remove-reference-btn" type="button">
                <i class="bi bi-trash"></i>
            </button>
        `;
        referenceContainer.appendChild(newReferenceField);
        
        // Add event listener for remove button
        newReferenceField.querySelector('.remove-reference-btn').addEventListener('click', function() {
            referenceContainer.removeChild(newReferenceField);
        });
    });
    
    // Add event listener for save template button
    document.getElementById('youtube-save-template-btn').addEventListener('click', function() {
        saveYouTubeConfigAsTemplate();
    });
    
    // Add event listener for start button
    document.getElementById('youtube-start-btn').addEventListener('click', function() {
        startYouTubeDataMining();
    });
}

// Save YouTube configuration as template
function saveYouTubeConfigAsTemplate() {
    // Get configuration data
    const configData = getYouTubeConfigData();
    
    // Show template name input dialog
    const templateName = prompt('Enter a name for this template:', configData.focus || 'YouTube Template');
    
    if (!templateName) {
        return; // User cancelled
    }
    
    // Add template name to config data
    configData.templateName = templateName;
    
    // Save template to server
    fetch('/data-mining/api/templates', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: templateName,
            type: 'youtube',
            config: configData
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert(`Template "${templateName}" saved successfully!`);
        } else {
            alert(`Error saving template: ${data.message || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error('Error saving template:', error);
        alert('Error saving template. Please try again.');
    });
}

// Start YouTube data mining
function startYouTubeDataMining() {
    // Get configuration data
    const configData = getYouTubeConfigData();
    
    // Validate required fields
    if (!configData.focus) {
        alert('Please enter a focus for your search.');
        return;
    }
    
    // Create task data
    const taskData = {
        name: configData.focus,
        task_type: 'youtube',
        description: configData.description || '',
        config: configData
    };
    
    // Create task on server
    fetch('/data-mining/api/data-mining/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(taskData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('youtubeConfigModal'));
            modal.hide();
            
            // Show success message
            alert(`YouTube data mining task "${configData.focus}" created successfully!`);
            
            // Reload tasks list if on listings tab
            if (document.getElementById('listings-tab').classList.contains('active')) {
                loadDataMiningTasks();
            }
            
            // Switch to listings tab
            const listingsTab = document.getElementById('listings-tab');
            const tab = new bootstrap.Tab(listingsTab);
            tab.show();
        } else {
            alert(`Error creating task: ${data.message || 'Unknown error'}`);
        }
    })
    .catch(error => {
        console.error('Error creating task:', error);
        alert('Error creating task. Please try again.');
    });
}

// Get YouTube configuration data from form
function getYouTubeConfigData() {
    // Get reference URLs
    const referenceInputs = document.querySelectorAll('.youtube-reference');
    const references = Array.from(referenceInputs)
        .map(input => input.value.trim())
        .filter(value => value !== '');
    
    // Get content types
    const contentTypes = {
        videos: document.getElementById('youtube-videos').checked,
        playlists: document.getElementById('youtube-playlists').checked,
        liveStreams: document.getElementById('youtube-live-streams').checked,
        shorts: document.getElementById('youtube-shorts').checked,
        channels: document.getElementById('youtube-channels').checked
    };
    
    // Get video lengths
    const videoLengths = {
        short: document.getElementById('youtube-short-videos').checked,
        medium: document.getElementById('youtube-medium-videos').checked,
        long: document.getElementById('youtube-long-videos').checked
    };
    
    // Get processing options
    const processingOptions = {
        transcribeAudio: document.getElementById('youtube-transcribe').checked,
        extractKeyPoints: document.getElementById('youtube-extract-key-points').checked,
        downloadVideos: document.getElementById('youtube-download-videos').checked,
        analyzeComments: document.getElementById('youtube-analyze-comments').checked,
        transcriptFormat: document.getElementById('youtube-transcript-format').value
    };
    
    // Get advanced options
    const advancedOptions = {
        followRecommended: document.getElementById('youtube-follow-recommended').checked,
        saveToDatabase: document.getElementById('youtube-save-to-db').checked,
        cacheEnabled: document.getElementById('youtube-cache-enabled').checked,
        useApiKey: document.getElementById('youtube-use-api-key').checked,
        apiKey: document.getElementById('youtube-api-key').value.trim()
    };
    
    // Get rate limiting options
    const rateLimiting = {
        rateLimitPerSecond: parseFloat(document.getElementById('youtube-rate-limit-per-second').value),
        rateLimitPerDay: parseInt(document.getElementById('youtube-rate-limit-per-day').value)
    };
    
    // Get retry settings
    const retrySettings = {
        maxRetries: parseInt(document.getElementById('youtube-max-retries').value),
        retryBackoffFactor: parseFloat(document.getElementById('youtube-retry-backoff-factor').value)
    };
    
    // Return configuration data
    return {
        focus: document.getElementById('youtube-focus').value.trim(),
        description: document.getElementById('youtube-description').value.trim(),
        references: references,
        contentTypes: contentTypes,
        timeRange: document.getElementById('youtube-time-range').value,
        videoLengths: videoLengths,
        maxResults: parseInt(document.getElementById('youtube-max-results').value),
        processingOptions: processingOptions,
        parallelWorkers: parseInt(document.getElementById('youtube-workers').value),
        advancedOptions: advancedOptions,
        rateLimiting: rateLimiting,
        retrySettings: retrySettings
    };
}

// Load YouTube configuration from template
function loadYouTubeConfigFromTemplate(templateConfig) {
    // Set focus and description
    document.getElementById('youtube-focus').value = templateConfig.focus || '';
    document.getElementById('youtube-description').value = templateConfig.description || '';
    
    // Set references
    const referenceContainer = document.getElementById('youtube-reference-container');
    referenceContainer.innerHTML = ''; // Clear existing references
    
    if (templateConfig.references && templateConfig.references.length > 0) {
        templateConfig.references.forEach(reference => {
            const referenceField = document.createElement('div');
            referenceField.className = 'input-group mb-2';
            referenceField.innerHTML = `
                <input type="text" class="form-control youtube-reference" placeholder="Enter file path or URL..." value="${reference}">
                <button class="btn btn-outline-danger remove-reference-btn" type="button">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            referenceContainer.appendChild(referenceField);
            
            // Add event listener for remove button
            referenceField.querySelector('.remove-reference-btn').addEventListener('click', function() {
                referenceContainer.removeChild(referenceField);
            });
        });
    } else {
        // Add empty reference field
        const referenceField = document.createElement('div');
        referenceField.className = 'input-group mb-2';
        referenceField.innerHTML = `
            <input type="text" class="form-control youtube-reference" placeholder="Enter file path or URL...">
        `;
        referenceContainer.appendChild(referenceField);
    }
    
    // Set content types
    if (templateConfig.contentTypes) {
        document.getElementById('youtube-videos').checked = templateConfig.contentTypes.videos !== false;
        document.getElementById('youtube-playlists').checked = templateConfig.contentTypes.playlists !== false;
        document.getElementById('youtube-live-streams').checked = templateConfig.contentTypes.liveStreams === true;
        document.getElementById('youtube-shorts').checked = templateConfig.contentTypes.shorts === true;
        document.getElementById('youtube-channels').checked = templateConfig.contentTypes.channels === true;
    }
    
    // Set time range
    if (templateConfig.timeRange) {
        document.getElementById('youtube-time-range').value = templateConfig.timeRange;
    }
    
    // Set video lengths
    if (templateConfig.videoLengths) {
        document.getElementById('youtube-short-videos').checked = templateConfig.videoLengths.short === true;
        document.getElementById('youtube-medium-videos').checked = templateConfig.videoLengths.medium !== false;
        document.getElementById('youtube-long-videos').checked = templateConfig.videoLengths.long !== false;
    }
    
    // Set max results
    if (templateConfig.maxResults) {
        const maxResultsInput = document.getElementById('youtube-max-results');
        maxResultsInput.value = templateConfig.maxResults;
        document.getElementById('youtube-max-results-value').textContent = templateConfig.maxResults;
    }
    
    // Set processing options
    if (templateConfig.processingOptions) {
        document.getElementById('youtube-transcribe').checked = templateConfig.processingOptions.transcribeAudio !== false;
        document.getElementById('youtube-extract-key-points').checked = templateConfig.processingOptions.extractKeyPoints !== false;
        document.getElementById('youtube-download-videos').checked = templateConfig.processingOptions.downloadVideos === true;
        document.getElementById('youtube-analyze-comments').checked = templateConfig.processingOptions.analyzeComments !== false;
        
        if (templateConfig.processingOptions.transcriptFormat) {
            document.getElementById('youtube-transcript-format').value = templateConfig.processingOptions.transcriptFormat;
        }
    }
    
    // Set parallel workers
    if (templateConfig.parallelWorkers) {
        const workersInput = document.getElementById('youtube-workers');
        workersInput.value = templateConfig.parallelWorkers;
        document.getElementById('youtube-workers-value').textContent = templateConfig.parallelWorkers;
    }
    
    // Set advanced options
    if (templateConfig.advancedOptions) {
        document.getElementById('youtube-follow-recommended').checked = templateConfig.advancedOptions.followRecommended !== false;
        document.getElementById('youtube-save-to-db').checked = templateConfig.advancedOptions.saveToDatabase !== false;
        document.getElementById('youtube-cache-enabled').checked = templateConfig.advancedOptions.cacheEnabled !== false;
        document.getElementById('youtube-use-api-key').checked = templateConfig.advancedOptions.useApiKey === true;
        
        const apiKeyInput = document.getElementById('youtube-api-key');
        apiKeyInput.value = templateConfig.advancedOptions.apiKey || '';
        apiKeyInput.disabled = !templateConfig.advancedOptions.useApiKey;
    }
    
    // Set rate limiting
    if (templateConfig.rateLimiting) {
        document.getElementById('youtube-rate-limit-per-second').value = templateConfig.rateLimiting.rateLimitPerSecond || 1;
        document.getElementById('youtube-rate-limit-per-day').value = templateConfig.rateLimiting.rateLimitPerDay || 10000;
    }
    
    // Set retry settings
    if (templateConfig.retrySettings) {
        document.getElementById('youtube-max-retries').value = templateConfig.retrySettings.maxRetries || 3;
        document.getElementById('youtube-retry-backoff-factor').value = templateConfig.retrySettings.retryBackoffFactor || 2;
    }
}

// Show YouTube configuration dialog
function showYouTubeConfigDialog(templateConfig = null) {
    // Get modal element
    const modal = document.getElementById('youtubeConfigModal');
    
    // If modal doesn't exist, add it to the DOM
    if (!modal) {
        // Load modal HTML from server
        fetch('/templates/youtube_config_dialog.html')
            .then(response => response.text())
            .then(html => {
                // Add modal to DOM
                document.body.insertAdjacentHTML('beforeend', html);
                
                // Initialize dialog
                initYouTubeConfigDialog();
                
                // Load template config if provided
                if (templateConfig) {
                    loadYouTubeConfigFromTemplate(templateConfig);
                }
                
                // Show modal
                const modalInstance = new bootstrap.Modal(document.getElementById('youtubeConfigModal'));
                modalInstance.show();
            })
            .catch(error => {
                console.error('Error loading YouTube configuration dialog:', error);
                alert('Error loading YouTube configuration dialog. Please try again.');
            });
    } else {
        // Load template config if provided
        if (templateConfig) {
            loadYouTubeConfigFromTemplate(templateConfig);
        } else {
            // Reset form
            document.getElementById('youtube-config-form').reset();
            
            // Reset range input displays
            document.getElementById('youtube-max-results-value').textContent = '50';
            document.getElementById('youtube-workers-value').textContent = '2';
            
            // Reset API key input
            document.getElementById('youtube-api-key').disabled = true;
            
            // Reset reference container
            const referenceContainer = document.getElementById('youtube-reference-container');
            referenceContainer.innerHTML = `
                <div class="input-group mb-2">
                    <input type="text" class="form-control youtube-reference" placeholder="Enter file path or URL...">
                </div>
            `;
            
            // Reset rate limiting and retry settings
            document.getElementById('youtube-rate-limit-per-second').value = '1';
            document.getElementById('youtube-rate-limit-per-day').value = '10000';
            document.getElementById('youtube-max-retries').value = '3';
            document.getElementById('youtube-retry-backoff-factor').value = '2';
        }
        
        // Show modal
        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();
    }
}

// Export functions
window.showYouTubeConfigDialog = showYouTubeConfigDialog;
