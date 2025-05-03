/**
 * Research Dashboard JavaScript
 * Handles UI interactions and API calls for the research connector
 */

// Initialize the research dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Update depth value display
    document.getElementById('searchDepth').addEventListener('input', function() {
        document.getElementById('depthValue').textContent = this.value;
    });
    
    document.getElementById('defaultSearchDepth').addEventListener('input', function() {
        document.getElementById('defaultDepthValue').textContent = this.value;
    });
    
    // Toggle previous research dropdown
    document.getElementById('continuousResearch').addEventListener('change', function() {
        document.getElementById('previousResearch').disabled = !this.checked;
    });
    
    // Start research button click handler
    document.getElementById('startResearch').addEventListener('click', function() {
        const researchTopic = document.getElementById('researchTopic').value;
        if (!researchTopic) {
            showAlert('Please enter a research topic', 'danger');
            return;
        }
        
        // Show loading state
        showLoading(true);
        
        // Get research parameters
        const researchMode = document.getElementById('researchMode').value;
        const searchAPI = document.getElementById('searchAPI').value;
        const searchDepth = parseInt(document.getElementById('searchDepth').value);
        const queriesPerIteration = parseInt(document.getElementById('queriesPerIteration').value);
        const continuousResearch = document.getElementById('continuousResearch').checked;
        
        // Prepare request data
        let requestData = {
            topic: researchTopic,
            research_mode: researchMode,
            search_api: searchAPI,
            max_search_depth: searchDepth,
            number_of_queries: queriesPerIteration,
            visualization_enabled: true
        };
        
        // If continuous research is enabled, include previous results
        if (continuousResearch) {
            const previousResearchId = document.getElementById('previousResearch').value;
            if (!previousResearchId) {
                showAlert('Please select a previous research', 'danger');
                showLoading(false);
                return;
            }
            
            // Fetch previous research results and then perform continuous research
            fetchPreviousResearch(previousResearchId)
                .then(previousResults => {
                    return performContinuousResearch(previousResults, requestData);
                })
                .then(displayResearchResults)
                .catch(error => {
                    console.error('Error performing continuous research:', error);
                    showAlert('Error performing research: ' + error.message, 'danger');
                    showLoading(false);
                });
        } else {
            // Perform new research
            performResearch(requestData)
                .then(displayResearchResults)
                .catch(error => {
                    console.error('Error performing research:', error);
                    showAlert('Error performing research: ' + error.message, 'danger');
                    showLoading(false);
                });
        }
    });
    
    // Initialize research mode cards in settings
    initializeResearchModeCards();
});

/**
 * Initialize research mode cards in settings
 */
function initializeResearchModeCards() {
    const linearModeDefault = document.getElementById('linearModeDefault');
    const graphModeDefault = document.getElementById('graphModeDefault');
    const multiAgentModeDefault = document.getElementById('multiAgentModeDefault');
    
    // Ensure only one mode is selected as default
    linearModeDefault.addEventListener('change', function() {
        if (this.checked) {
            graphModeDefault.checked = false;
            multiAgentModeDefault.checked = false;
        }
    });
    
    graphModeDefault.addEventListener('change', function() {
        if (this.checked) {
            linearModeDefault.checked = false;
            multiAgentModeDefault.checked = false;
        }
    });
    
    multiAgentModeDefault.addEventListener('change', function() {
        if (this.checked) {
            linearModeDefault.checked = false;
            graphModeDefault.checked = false;
        }
    });
}

/**
 * Perform research using the research connector API
 * @param {Object} requestData - Research request data
 * @returns {Promise<Object>} - Research results
 */
async function performResearch(requestData) {
    const response = await fetch('/research', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to perform research');
    }
    
    return response.json();
}

/**
 * Perform continuous research using the research connector API
 * @param {Object} previousResults - Previous research results
 * @param {Object} requestData - Research request data
 * @returns {Promise<Object>} - Research results
 */
async function performContinuousResearch(previousResults, requestData) {
    const continuousRequestData = {
        previous_results: previousResults,
        new_topic: requestData.topic,
        research_mode: requestData.research_mode,
        search_api: requestData.search_api,
        max_search_depth: requestData.max_search_depth,
        number_of_queries: requestData.number_of_queries
    };
    
    const response = await fetch('/continuous-research', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(continuousRequestData)
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to perform continuous research');
    }
    
    return response.json();
}

/**
 * Fetch previous research results by ID
 * @param {string} researchId - ID of the previous research
 * @returns {Promise<Object>} - Previous research results
 */
async function fetchPreviousResearch(researchId) {
    // This is a mock function - in a real implementation, this would fetch from an API
    return {
        topic: 'Previous Research Topic',
        sections: [],
        raw_sections: { sections: [] },
        metadata: {
            search_api: 'tavily',
            research_mode: 'graph',
            search_depth: 2,
            queries_per_iteration: 2
        }
    };
}

/**
 * Display research results in the UI
 * @param {Object} results - Research results from the API
 */
function displayResearchResults(results) {
    // Hide loading state
    showLoading(false);
    
    // Update result topic
    document.getElementById('resultTopic').textContent = results.topic;
    
    // Update badges
    const badgesContainer = document.querySelector('.research-results .d-flex .badge').parentElement;
    badgesContainer.innerHTML = '';
    
    // Add API badge
    const apiBadge = document.createElement('span');
    apiBadge.className = 'badge bg-primary api-badge';
    apiBadge.textContent = results.metadata.search_api;
    badgesContainer.appendChild(apiBadge);
    
    // Add mode badge
    const modeBadge = document.createElement('span');
    modeBadge.className = 'badge bg-success api-badge';
    modeBadge.textContent = results.metadata.research_mode;
    badgesContainer.appendChild(modeBadge);
    
    // Add depth badge
    const depthBadge = document.createElement('span');
    depthBadge.className = 'badge bg-info api-badge';
    depthBadge.textContent = 'Depth: ' + results.metadata.search_depth;
    badgesContainer.appendChild(depthBadge);
    
    // Update research content
    const researchContent = document.querySelector('.research-content');
    researchContent.innerHTML = '';
    
    // Add sections
    results.sections.forEach(section => {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'result-section';
        
        const sectionTitle = document.createElement('h6');
        sectionTitle.textContent = section.title;
        sectionDiv.appendChild(sectionTitle);
        
        const sectionContent = document.createElement('div');
        sectionContent.innerHTML = section.content;
        sectionDiv.appendChild(sectionContent);
        
        researchContent.appendChild(sectionDiv);
    });
    
    // Show research results
    document.querySelector('.research-results').classList.remove('d-none');
    
    // Scroll to results
    document.querySelector('.research-results').scrollIntoView({ behavior: 'smooth' });
    
    // Add to research history (in a real implementation, this would be saved to a database)
    addToResearchHistory(results);
}

/**
 * Add research results to history
 * @param {Object} results - Research results
 */
function addToResearchHistory(results) {
    // This is a mock function - in a real implementation, this would save to a database
    console.log('Added to research history:', results);
}

/**
 * Show or hide loading state
 * @param {boolean} isLoading - Whether to show or hide loading state
 */
function showLoading(isLoading) {
    const startButton = document.getElementById('startResearch');
    
    if (isLoading) {
        startButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Researching...';
        startButton.disabled = true;
    } else {
        startButton.innerHTML = '<i class="bi bi-search"></i> Start Research';
        startButton.disabled = false;
    }
}

/**
 * Show an alert message
 * @param {string} message - Alert message
 * @param {string} type - Alert type (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add alert to the page
    const container = document.querySelector('.card-body');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
    }, 5000);
}

