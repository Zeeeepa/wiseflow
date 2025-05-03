// Templates Management JavaScript

// Initialize the templates management page
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners for filter inputs
    const filterInput = document.querySelector('.filter-section input');
    if (filterInput) {
        filterInput.addEventListener('input', filterTemplates);
    }
    
    const typeSelect = document.querySelector('.filter-section select');
    if (typeSelect) {
        typeSelect.addEventListener('change', filterTemplates);
    }
    
    // Add event listeners for template actions
    setupTemplateActions();
    
    // Setup pagination
    setupPagination();
    
    // Setup import/export buttons
    setupBottomActions();
    
    // Load templates from API
    loadTemplates();
    
    // Subscribe to template events
    EventBus.subscribe(EventBus.Events.TEMPLATE_CREATED, handleTemplateCreated);
    EventBus.subscribe(EventBus.Events.TEMPLATE_UPDATED, handleTemplateUpdated);
    EventBus.subscribe(EventBus.Events.TEMPLATE_DELETED, handleTemplateDeleted);
});

// Load templates from API
function loadTemplates() {
    // Show loading indicator
    const templatesContainer = document.querySelector('.templates-container');
    if (templatesContainer) {
        templatesContainer.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading templates...</p>
            </div>
        `;
    }
    
    // Fetch templates from API
    ApiClient.dataMining.getTemplates()
        .then(data => {
            if (data.status === 'success' && data.templates) {
                displayTemplates(data.templates);
                
                // Update state
                StateManager.dispatch({
                    type: 'SET_TEMPLATES',
                    payload: data.templates
                });
            } else {
                if (templatesContainer) {
                    templatesContainer.innerHTML = `
                        <div class="alert alert-info">
                            <p>No templates found.</p>
                            <p>Create templates by saving configurations from data mining tasks.</p>
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.error('Error loading templates:', error);
            if (templatesContainer) {
                templatesContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <p>Error loading templates. Please try again.</p>
                        <button class="btn btn-outline-primary mt-2" id="retry-load-btn">
                            <i class="bi bi-arrow-clockwise"></i> Retry
                        </button>
                    </div>
                `;
                
                // Add event listener to retry button
                document.getElementById('retry-load-btn').addEventListener('click', loadTemplates);
            }
        });
}

// Display templates
function displayTemplates(templates) {
    const templatesContainer = document.querySelector('.templates-container');
    if (!templatesContainer) return;
    
    if (templates.length === 0) {
        templatesContainer.innerHTML = `
            <div class="alert alert-info">
                <p>No templates found.</p>
                <p>Create templates by saving configurations from data mining tasks.</p>
            </div>
        `;
        return;
    }
    
    // Clear existing content
    templatesContainer.innerHTML = '';
    
    // Sort templates by created_at (newest first)
    templates.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    // Add each template to the container
    templates.forEach(template => {
        const templateCard = document.createElement('div');
        templateCard.className = 'template-card';
        templateCard.setAttribute('data-template-id', template.template_id);
        templateCard.setAttribute('data-template-type', template.type);
        
        // Format dates
        const createdDate = WiseFlowUtils.formatDateTime(template.created_at);
        const lastUsedDate = template.last_used_at ? 
            WiseFlowUtils.formatDateTime(template.last_used_at) : 
            'Never';
        
        templateCard.innerHTML = `
            <div class="template-title">${template.name}</div>
            <div class="template-meta">
                <span class="badge bg-${getTemplateBadgeColor(template.type)}">${template.type}</span>
                <span class="ms-2">Created: ${createdDate}</span>
                <span class="ms-2">Last Used: ${lastUsedDate}</span>
            </div>
            <div class="template-actions">
                <button class="btn btn-sm btn-outline-primary load-template-btn">Load</button>
                <button class="btn btn-sm btn-outline-secondary edit-template-btn">Edit</button>
                <button class="btn btn-sm btn-outline-danger delete-template-btn">Delete</button>
            </div>
        `;
        
        templatesContainer.appendChild(templateCard);
    });
    
    // Add event listeners to the newly created buttons
    setupTemplateActions();
    
    // Update pagination
    updatePagination();
}

// Get template badge color based on type
function getTemplateBadgeColor(type) {
    switch(type.toLowerCase()) {
        case 'github':
            return 'primary';
        case 'arxiv':
            return 'success';
        case 'web':
        case 'webresearch':
            return 'info';
        case 'youtube':
            return 'danger';
        default:
            return 'secondary';
    }
}

// Handle template created event
function handleTemplateCreated(data) {
    console.log('Template created:', data);
    
    // Refresh the template list
    loadTemplates();
    
    // Show success notification
    WiseFlowUtils.showToast(`Template "${data.name}" created successfully`, 'success');
}

// Handle template updated event
function handleTemplateUpdated(data) {
    console.log('Template updated:', data);
    
    // Refresh the template list
    loadTemplates();
    
    // Show success notification
    WiseFlowUtils.showToast(`Template "${data.name}" updated successfully`, 'success');
}

// Handle template deleted event
function handleTemplateDeleted(data) {
    console.log('Template deleted:', data);
    
    // Refresh the template list
    loadTemplates();
    
    // Show success notification
    WiseFlowUtils.showToast(`Template deleted successfully`, 'success');
}

// Filter templates based on search text and type
function filterTemplates() {
    const searchText = document.querySelector('.filter-section input').value.toLowerCase();
    const selectedType = document.querySelector('.filter-section select').value;
    
    const templates = document.querySelectorAll('.template-card');
    
    templates.forEach(template => {
        const title = template.querySelector('.template-title').textContent.toLowerCase();
        const typeBadge = template.querySelector('.badge').textContent;
        
        const matchesSearch = title.includes(searchText);
        const matchesType = selectedType === 'All' || typeBadge === selectedType;
        
        if (matchesSearch && matchesType) {
            template.style.display = 'block';
        } else {
            template.style.display = 'none';
        }
    });
    
    // Update pagination after filtering
    updatePagination();
    
    // Update state
    StateManager.dispatch({
        type: 'SET_FILTERS',
        payload: {
            searchText: searchText,
            templateType: selectedType
        },
        persist: true
    });
}

// Setup event listeners for template action buttons
function setupTemplateActions() {
    // Load buttons
    const loadButtons = document.querySelectorAll('.template-actions button:nth-child(1)');
    loadButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const templateCard = e.target.closest('.template-card');
            const templateTitle = templateCard.querySelector('.template-title').textContent;
            const templateType = templateCard.querySelector('.badge').textContent;
            
            // In a real application, this would load the template data
            alert(`Loading template: ${templateTitle} (${templateType})`);
            
            // Update last used date
            const metaInfo = templateCard.querySelector('.template-meta');
            const today = new Date();
            const formattedDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
            
            // Update the last used date in the UI
            const spans = metaInfo.querySelectorAll('span');
            spans[2].textContent = `Last Used: ${formattedDate}`;
        });
    });
    
    // Edit buttons
    const editButtons = document.querySelectorAll('.template-actions button:nth-child(2)');
    editButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const templateCard = e.target.closest('.template-card');
            const templateTitle = templateCard.querySelector('.template-title').textContent;
            const templateType = templateCard.querySelector('.badge').textContent;
            
            // In a real application, this would open the edit form
            alert(`Editing template: ${templateTitle} (${templateType})`);
        });
    });
    
    // Delete buttons
    const deleteButtons = document.querySelectorAll('.template-actions button:nth-child(3)');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const templateCard = e.target.closest('.template-card');
            const templateTitle = templateCard.querySelector('.template-title').textContent;
            
            if (confirm(`Are you sure you want to delete the template "${templateTitle}"?`)) {
                // In a real application, this would delete the template from the database
                templateCard.remove();
                alert(`Template "${templateTitle}" has been deleted.`);
                
                // Update pagination after deletion
                updatePagination();
            }
        });
    });
}

// Setup pagination functionality
function setupPagination() {
    const paginationLinks = document.querySelectorAll('.pagination .page-link');
    
    paginationLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Don't do anything if the link is disabled
            if (this.parentElement.classList.contains('disabled')) {
                return;
            }
            
            // Update active page
            document.querySelector('.pagination .active').classList.remove('active');
            
            if (this.textContent === 'Previous') {
                const activePage = parseInt(document.querySelector('.pagination .active a').textContent);
                if (activePage > 1) {
                    document.querySelector(`.pagination li:nth-child(${activePage})`).classList.add('active');
                }
            } else if (this.textContent === 'Next') {
                const activePage = parseInt(document.querySelector('.pagination .active a').textContent);
                const totalPages = document.querySelectorAll('.pagination li').length - 2; // Subtract Previous and Next buttons
                if (activePage < totalPages) {
                    document.querySelector(`.pagination li:nth-child(${activePage + 2})`).classList.add('active');
                }
            } else {
                this.parentElement.classList.add('active');
            }
            
            // In a real application, this would load the templates for the selected page
            loadTemplatesForPage(this.textContent);
        });
    });
}

// Load templates for the selected page
function loadTemplatesForPage(page) {
    // This is a placeholder function
    // In a real application, this would fetch templates for the selected page from the server
    console.log(`Loading templates for page ${page}`);
}

// Update pagination based on the number of visible templates
function updatePagination() {
    const visibleTemplates = document.querySelectorAll('.template-card:not([style*="display: none"])').length;
    const templatesPerPage = 5;
    const totalPages = Math.ceil(visibleTemplates / templatesPerPage);
    
    // Update pagination UI
    const paginationContainer = document.querySelector('.pagination');
    let paginationHTML = `
        <li class="page-item ${totalPages <= 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" tabindex="-1" ${totalPages <= 1 ? 'aria-disabled="true"' : ''}>Previous</a>
        </li>
    `;
    
    for (let i = 1; i <= totalPages; i++) {
        paginationHTML += `
            <li class="page-item ${i === 1 ? 'active' : ''}">
                <a class="page-link" href="#">${i}</a>
            </li>
        `;
    }
    
    paginationHTML += `
        <li class="page-item ${totalPages <= 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" ${totalPages <= 1 ? 'aria-disabled="true"' : ''}>Next</a>
        </li>
    `;
    
    paginationContainer.innerHTML = paginationHTML;
    
    // Re-setup pagination event listeners
    setupPagination();
}

// Setup import/export buttons
function setupBottomActions() {
    const exportButton = document.querySelector('.bottom-actions button:nth-child(1)');
    if (exportButton) {
        exportButton.addEventListener('click', function() {
            // In a real application, this would export the templates
            alert('Exporting templates...');
            
            // Mock export functionality
            const templates = [];
            document.querySelectorAll('.template-card').forEach(card => {
                templates.push({
                    title: card.querySelector('.template-title').textContent,
                    type: card.querySelector('.badge').textContent,
                    created: card.querySelector('.template-meta span:nth-child(2)').textContent.replace('Created: ', ''),
                    lastUsed: card.querySelector('.template-meta span:nth-child(3)').textContent.replace('Last Used: ', '')
                });
            });
            
            // Create a download link for the JSON file
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(templates, null, 2));
            const downloadAnchorNode = document.createElement('a');
            downloadAnchorNode.setAttribute("href", dataStr);
            downloadAnchorNode.setAttribute("download", "wiseflow_templates.json");
            document.body.appendChild(downloadAnchorNode);
            downloadAnchorNode.click();
            downloadAnchorNode.remove();
        });
    }
    
    const importButton = document.querySelector('.bottom-actions button:nth-child(2)');
    if (importButton) {
        importButton.addEventListener('click', function() {
            // Create a file input element
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = '.json';
            fileInput.style.display = 'none';
            document.body.appendChild(fileInput);
            
            fileInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        try {
                            const templates = JSON.parse(e.target.result);
                            alert(`Successfully imported ${templates.length} templates.`);
                            
                            // In a real application, this would add the templates to the database
                            // and refresh the UI
                        } catch (error) {
                            alert('Error parsing the imported file. Please make sure it is a valid JSON file.');
                            console.error(error);
                        }
                    };
                    reader.readAsText(file);
                }
                
                // Remove the file input element
                fileInput.remove();
            });
            
            // Trigger the file input click
            fileInput.click();
        });
    }
}
