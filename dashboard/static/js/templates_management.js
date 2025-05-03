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
});

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

