// Process Selection Dialog JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the process selection dialog
    initProcessSelectionDialog();
});

// Initialize the process selection dialog
function initProcessSelectionDialog() {
    // Create the dialog if it doesn't exist
    createProcessSelectionDialog();
    
    // Add event listener to the "New" button in the dashboard
    const newProcessBtn = document.getElementById('new-process-btn');
    if (newProcessBtn) {
        newProcessBtn.addEventListener('click', function() {
            showProcessSelectionDialog();
        });
    }
}

// Create the process selection dialog
function createProcessSelectionDialog() {
    // Check if the dialog already exists
    if (document.getElementById('processSelectionModal')) {
        return;
    }
    
    // Create the modal element
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'processSelectionModal';
    modal.tabIndex = '-1';
    modal.setAttribute('aria-labelledby', 'processSelectionModalLabel');
    modal.setAttribute('aria-hidden', 'true');
    
    // Set the modal content
    modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="processSelectionModalLabel">Select Data Source</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="data-source-selection">
                        <div class="row text-center">
                            <div class="col-3">
                                <button class="btn btn-outline-primary data-source-btn" data-source="github">
                                    <i class="bi bi-github mb-2" style="font-size: 2rem;"></i>
                                    <div>GitHub</div>
                                </button>
                                <div class="source-description mt-2">Code Mining Source</div>
                            </div>
                            <div class="col-3">
                                <button class="btn btn-outline-primary data-source-btn" data-source="web">
                                    <i class="bi bi-globe mb-2" style="font-size: 2rem;"></i>
                                    <div>WebSearch</div>
                                </button>
                                <div class="source-description mt-2">Web Content Mining</div>
                            </div>
                            <div class="col-3">
                                <button class="btn btn-outline-primary data-source-btn" data-source="youtube">
                                    <i class="bi bi-youtube mb-2" style="font-size: 2rem;"></i>
                                    <div>YouTube</div>
                                </button>
                                <div class="source-description mt-2">Video Mining Content</div>
                            </div>
                            <div class="col-3">
                                <button class="btn btn-outline-primary data-source-btn" data-source="arxiv">
                                    <i class="bi bi-journal-text mb-2" style="font-size: 2rem;"></i>
                                    <div>ArXiv</div>
                                </button>
                                <div class="source-description mt-2">Research Papers Mining</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-info" id="help-btn">Help</button>
                </div>
            </div>
        </div>
    `;
    
    // Add the modal to the document
    document.body.appendChild(modal);
    
    // Add event listeners to the data source buttons
    document.querySelectorAll('.data-source-btn').forEach(button => {
        button.addEventListener('click', function() {
            const source = this.getAttribute('data-source');
            selectDataSource(source);
        });
    });
    
    // Add event listener to the help button
    document.getElementById('help-btn').addEventListener('click', function() {
        showHelpDialog();
    });
}

// Show the process selection dialog
function showProcessSelectionDialog() {
    const modal = new bootstrap.Modal(document.getElementById('processSelectionModal'));
    modal.show();
}

// Select a data source
function selectDataSource(source) {
    // Hide the process selection dialog
    const modal = bootstrap.Modal.getInstance(document.getElementById('processSelectionModal'));
    modal.hide();
    
    // Navigate to the appropriate tab in the search dashboard
    window.location.href = `/search#${source}`;
    
    // Activate the tab programmatically after page load
    window.addEventListener('load', function() {
        const tab = document.getElementById(`${source}-tab`);
        if (tab) {
            const tabInstance = new bootstrap.Tab(tab);
            tabInstance.show();
        }
    });
}

// Show the help dialog
function showHelpDialog() {
    // Create a simple alert for now, but this could be a more sophisticated help dialog
    alert('Data Source Help:\n\n' +
          'GitHub: Search and analyze code repositories, issues, and pull requests.\n' +
          'WebSearch: Search and analyze web content from various search engines.\n' +
          'YouTube: Search and analyze video content and comments.\n' +
          'ArXiv: Search and analyze research papers and academic content.');
}

// Add CSS styles for the process selection dialog
function addProcessSelectionStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .data-source-btn {
            width: 100%;
            height: 100px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-bottom: 10px;
            transition: all 0.3s;
        }
        
        .data-source-btn:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        
        .source-description {
            font-size: 0.8rem;
            color: #6c757d;
            text-align: center;
        }
    `;
    document.head.appendChild(style);
}

// Call the function to add styles
addProcessSelectionStyles();

