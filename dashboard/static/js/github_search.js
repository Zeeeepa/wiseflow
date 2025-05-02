// GitHub Search JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Tab navigation
    const searchTabs = document.querySelectorAll('.sidebar-link[data-search-tab]');
    const tabContents = document.querySelectorAll('.search-tab');
    
    // Initialize tab navigation
    searchTabs.forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get the tab to show
            const tabToShow = this.getAttribute('data-search-tab');
            
            // Update active tab in sidebar
            searchTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Hide all tabs and show the selected one
            tabContents.forEach(content => {
                content.style.display = 'none';
            });
            
            document.getElementById(`${tabToShow}-tab`).style.display = 'block';
        });
    });
    
    // File upload handling
    const selectFilesBtn = document.getElementById('select-files-btn');
    const contextFileInput = document.getElementById('context-file-input');
    const selectedFilesContainer = document.getElementById('selected-files-container');
    const selectedFilesList = document.getElementById('selected-files-list');
    
    if (selectFilesBtn) {
        selectFilesBtn.addEventListener('click', function() {
            contextFileInput.click();
        });
    }
    
    if (contextFileInput) {
        contextFileInput.addEventListener('change', function() {
            handleFileSelection(this.files);
        });
    }
    
    // Drag and drop functionality
    const dropArea = document.querySelector('.context-files-container');
    
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            dropArea.classList.add('border-primary');
        }
        
        function unhighlight() {
            dropArea.classList.remove('border-primary');
        }
        
        dropArea.addEventListener('drop', function(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFileSelection(files);
        });
    }
    
    function handleFileSelection(files) {
        if (files.length > 0) {
            selectedFilesContainer.style.display = 'block';
            selectedFilesList.innerHTML = '';
            
            Array.from(files).forEach(file => {
                // Check file type and size
                const validExtensions = ['.js', '.jsx', '.ts', '.tsx', '.py', '.txt', '.md'];
                const fileExt = '.' + file.name.split('.').pop().toLowerCase();
                
                if (!validExtensions.includes(fileExt)) {
                    alert(`File type ${fileExt} is not supported. Please upload only js, jsx, ts, tsx, py, txt, or md files.`);
                    return;
                }
                
                if (file.size > 5 * 1024 * 1024) { // 5MB
                    alert(`File ${file.name} is too large. Maximum file size is 5MB.`);
                    return;
                }
                
                // Add file to the list
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                
                const fileIcon = document.createElement('i');
                fileIcon.className = 'bi bi-file-earmark-code me-2';
                
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
                    if (selectedFilesList.children.length === 0) {
                        selectedFilesContainer.style.display = 'none';
                    }
                });
                
                listItem.appendChild(fileIcon);
                listItem.appendChild(fileName);
                listItem.appendChild(fileSize);
                listItem.appendChild(removeBtn);
                
                selectedFilesList.appendChild(listItem);
            });
        }
    }
    
    function formatFileSize(bytes) {
        if (bytes < 1024) {
            return bytes + ' B';
        } else if (bytes < 1024 * 1024) {
            return (bytes / 1024).toFixed(1) + ' KB';
        } else {
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }
    }
    
    // Start search button
    const startSearchBtn = document.getElementById('start-github-search-btn');
    const searchStatus = document.getElementById('search-status');
    
    if (startSearchBtn) {
        startSearchBtn.addEventListener('click', function() {
            const searchGoal = document.getElementById('github-search-goal').value;
            const searchDescription = document.getElementById('github-search-description').value;
            const searchStrategy = document.getElementById('github-search-strategy').value;
            const searchPriority = document.getElementById('github-search-priority').value;
            
            if (!searchGoal) {
                alert('Please enter a search goal');
                return;
            }
            
            if (!searchDescription) {
                alert('Please enter a detailed description');
                return;
            }
            
            // In a real application, this would send the search request to the server
            // For demonstration, we'll just update the status
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
                document.querySelector('.sidebar-link[data-search-tab="listings"]').click();
                
                // Add the new search to the listings
                const miningListings = document.getElementById('mining-listings');
                const newRow = document.createElement('tr');
                newRow.innerHTML = `
                    <td>${searchGoal}</td>
                    <td>GitHub</td>
                    <td><span class="badge bg-success">Active</span></td>
                    <td>${new Date().toLocaleString()}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary">View</button>
                        <button class="btn btn-sm btn-outline-warning">Edit</button>
                        <button class="btn btn-sm btn-outline-danger">Remove</button>
                    </td>
                `;
                miningListings.prepend(newRow);
            }, 3000);
        });
    }
    
    // Add new mining button
    const addMiningBtn = document.getElementById('add-mining-btn');
    
    if (addMiningBtn) {
        addMiningBtn.addEventListener('click', function() {
            // Redirect to GitHub search tab
            document.querySelector('.sidebar-link[data-search-tab="github"]').click();
        });
    }
});

