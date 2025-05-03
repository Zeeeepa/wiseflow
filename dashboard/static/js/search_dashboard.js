// Search Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tabs
    const triggerTabList = document.querySelectorAll('#searchTabs button');
    triggerTabList.forEach(triggerEl => {
        const tabTrigger = new bootstrap.Tab(triggerEl);
        triggerEl.addEventListener('click', event => {
            event.preventDefault();
            tabTrigger.show();
        });
    });

    // Add mining buttons in listings tab
    const addGithubMiningBtn = document.getElementById('add-github-mining-btn');
    const addArxivMiningBtn = document.getElementById('add-arxiv-mining-btn');
    const addWebMiningBtn = document.getElementById('add-web-mining-btn');
    const addYoutubeMiningBtn = document.getElementById('add-youtube-mining-btn');

    if (addGithubMiningBtn) {
        addGithubMiningBtn.addEventListener('click', function() {
            document.getElementById('github-tab').click();
            // Initialize the advanced GitHub dialog
            initializeAdvancedGitHubDialog();
        });
    }

    if (addArxivMiningBtn) {
        addArxivMiningBtn.addEventListener('click', function() {
            document.getElementById('arxiv-tab').click();
        });
    }

    if (addWebMiningBtn) {
        addWebMiningBtn.addEventListener('click', function() {
            document.getElementById('web-tab').click();
        });
    }

    if (addYoutubeMiningBtn) {
        addYoutubeMiningBtn.addEventListener('click', function() {
            document.getElementById('youtube-tab').click();
        });
    }

    // Setup file upload handling for each search type
    setupFileUpload('github');
    setupFileUpload('arxiv');
    setupFileUpload('web');
    setupFileUpload('youtube');

    // Setup search buttons
    setupSearchButton('github');
    setupSearchButton('arxiv');
    setupSearchButton('web');
    setupSearchButton('youtube');
    
    // Initialize the advanced GitHub dialog when the GitHub tab is clicked
    document.getElementById('github-tab').addEventListener('click', function() {
        initializeAdvancedGitHubDialog();
    });
});

// Initialize the advanced GitHub dialog
function initializeAdvancedGitHubDialog() {
    // Hide content analysis section by default (only show when advanced search is selected)
    const contentAnalysisSection = document.querySelector('.mb-4:has(label.form-label:contains("Content Analysis"))');
    if (contentAnalysisSection) {
        contentAnalysisSection.style.display = 'none';
    }
    
    // Hide advanced search options by default
    const advancedOptions = document.querySelectorAll('#github-search-issues, #github-search-prs, #github-search-discussions');
    advancedOptions.forEach(option => {
        const formCheck = option.closest('.form-check');
        if (formCheck) {
            formCheck.style.display = 'none';
        }
    });
}

// Function to setup file upload for a specific search type
function setupFileUpload(searchType) {
    const selectFilesBtn = document.getElementById(`${searchType}-select-files-btn`);
    const contextFileInput = document.getElementById(`${searchType}-context-file-input`);
    const selectedFilesContainer = document.getElementById(`${searchType}-selected-files-container`);
    const selectedFilesList = document.getElementById(`${searchType}-selected-files-list`);
    const dropArea = document.getElementById(`${searchType}-context-files-container`);
    
    if (selectFilesBtn) {
        selectFilesBtn.addEventListener('click', function() {
            contextFileInput.click();
        });
    }
    
    if (contextFileInput) {
        contextFileInput.addEventListener('change', function() {
            handleFileSelection(this.files, searchType);
        });
    }
    
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, function() {
                dropArea.classList.add('border-primary');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, function() {
                dropArea.classList.remove('border-primary');
            }, false);
        });
        
        dropArea.addEventListener('drop', function(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFileSelection(files, searchType);
        });
    }
    
    function handleFileSelection(files, type) {
        if (files.length > 0) {
            const filesContainer = document.getElementById(`${type}-selected-files-container`);
            const filesList = document.getElementById(`${type}-selected-files-list`);
            
            filesContainer.style.display = 'block';
            filesList.innerHTML = '';
            
            Array.from(files).forEach(file => {
                // Check file size
                if (file.size > 5 * 1024 * 1024) { // 5MB
                    alert(`File ${file.name} is too large. Maximum file size is 5MB.`);
                    return;
                }
                
                // Add file to the list
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                
                const fileIcon = document.createElement('i');
                fileIcon.className = 'bi bi-file-earmark-text me-2';
                
                const fileName = document.createElement('span');
                fileName.textContent = file.name;
                
                const fileSize = document.createElement('span');
                fileSize.className = 'badge bg-secondary';
                fileSize.textContent = formatFileSize(file.size);
                
                const removeBtn = document.createElement('button');
                removeBtn.className = 'btn btn-sm btn-outline-danger';
                removeBtn.innerHTML = '<i class="bi bi-x"></i>';
                removeBtn.addEventListener('click', function() {
                    listItem.remove();
                    if (filesList.children.length === 0) {
                        filesContainer.style.display = 'none';
                    }
                });
                
                listItem.appendChild(fileIcon);
                listItem.appendChild(fileName);
                listItem.appendChild(fileSize);
                listItem.appendChild(removeBtn);
                
                filesList.appendChild(listItem);
            });
        }
    }
}

// Function to setup search button for a specific search type
function setupSearchButton(searchType) {
    const startSearchBtn = document.getElementById(`start-${searchType}-search-btn`);
    const searchStatus = document.getElementById(`${searchType}-search-status`);
    
    if (startSearchBtn) {
        startSearchBtn.addEventListener('click', function() {
            const searchGoal = document.getElementById(`${searchType}-search-goal`).value;
            
            if (!searchGoal) {
                alert('Please enter a search goal');
                return;
            }
            
            // Show search in progress
            searchStatus.innerHTML = '<i class="bi bi-arrow-repeat spin me-2"></i> Search in progress...';
            searchStatus.className = 'mt-3 text-center text-primary';
            
            // Add spinning animation
            const style = document.createElement('style');
            style.innerHTML = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .spin {
                    animation: spin 1s linear infinite;
                    display: inline-block;
                }
            `;
            document.head.appendChild(style);
            
            // Simulate search completion after 3 seconds
            setTimeout(function() {
                searchStatus.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i> Search completed successfully!';
                searchStatus.className = 'mt-3 text-center text-success';
                
                // Redirect to listings tab to show results
                document.getElementById('listings-tab').click();
                
                // Add the new search to the listings
                const miningListings = document.getElementById('mining-listings');
                const newRow = document.createElement('tr');
                
                // Get the search goal
                const goal = document.getElementById(`${searchType}-search-goal`).value;
                
                // Capitalize first letter of search type
                const typeDisplay = searchType.charAt(0).toUpperCase() + searchType.slice(1);
                
                newRow.innerHTML = `
                    <td>${goal}</td>
                    <td>${typeDisplay}</td>
                    <td><span class="badge bg-success">Active</span></td>
                    <td>${new Date().toLocaleString()}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary">View Findings</button>
                        <button class="btn btn-sm btn-outline-warning">Edit</button>
                        <button class="btn btn-sm btn-outline-secondary">Turn Off</button>
                        <button class="btn btn-sm btn-outline-danger">Remove</button>
                    </td>
                `;
                miningListings.prepend(newRow);
            }, 3000);
        });
    }
}

// Helper function to format file size
function formatFileSize(bytes) {
    if (bytes < 1024) {
        return bytes + ' B';
    } else if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(1) + ' KB';
    } else {
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
}
