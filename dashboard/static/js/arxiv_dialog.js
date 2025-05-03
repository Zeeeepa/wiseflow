// ArXiv Configuration Dialog JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initArxivDialog();
});

function initArxivDialog() {
    // Add event listener for the "Add More" button for reference context
    document.querySelector('.add-more-context-btn').addEventListener('click', function() {
        addReferenceContextInput();
    });

    // Add event listener for the "More" button for subcategories
    document.getElementById('more-subcategories-btn').addEventListener('click', function() {
        showMoreSubcategories();
    });

    // Add event listener for the "Start" button
    document.getElementById('start-arxiv-mining-btn').addEventListener('click', function() {
        startArxivMining();
    });

    // Add event listener for the "Save as Template" button
    document.getElementById('save-template-btn').addEventListener('click', function() {
        saveAsTemplate();
    });

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Function to add a new reference context input field
function addReferenceContextInput() {
    const container = document.getElementById('reference-context-container');
    const inputGroup = document.createElement('div');
    inputGroup.className = 'input-group mb-2';
    
    inputGroup.innerHTML = `
        <input type="text" class="form-control reference-context-input" placeholder="Enter file path or URL">
        <button class="btn btn-outline-danger remove-context-btn" type="button">Remove</button>
    `;
    
    container.appendChild(inputGroup);
    
    // Add event listener for the "Remove" button
    inputGroup.querySelector('.remove-context-btn').addEventListener('click', function() {
        container.removeChild(inputGroup);
    });
}

// Additional subcategories to show when "More" is clicked
const additionalSubcategories = [
    { value: 'cs.IR', label: 'cs.IR - Information Retrieval' },
    { value: 'cs.RO', label: 'cs.RO - Robotics' },
    { value: 'cs.SE', label: 'cs.SE - Software Engineering' },
    { value: 'cs.DB', label: 'cs.DB - Databases' },
    { value: 'cs.DC', label: 'cs.DC - Distributed Computing' },
    { value: 'cs.HC', label: 'cs.HC - Human-Computer Interaction' },
    { value: 'cs.CY', label: 'cs.CY - Computers and Society' },
    { value: 'cs.CR', label: 'cs.CR - Cryptography and Security' }
];

// Function to show more subcategories
function showMoreSubcategories() {
    const moreBtn = document.getElementById('more-subcategories-btn');
    const parentElement = moreBtn.parentElement.parentElement;
    
    // Add additional subcategories
    additionalSubcategories.forEach(function(subcategory) {
        const div = document.createElement('div');
        div.className = 'form-check';
        
        div.innerHTML = `
            <input class="form-check-input" type="checkbox" value="${subcategory.value}" id="subcategory-${subcategory.value.toLowerCase().replace('.', '-')}">
            <label class="form-check-label" for="subcategory-${subcategory.value.toLowerCase().replace('.', '-')}">${subcategory.label}</label>
        `;
        
        parentElement.insertBefore(div, moreBtn.parentElement);
    });
    
    // Hide the "More" button after showing all subcategories
    moreBtn.parentElement.style.display = 'none';
}

// Function to start ArXiv mining
function startArxivMining() {
    // Get form values
    const focus = document.getElementById('arxiv-focus').value;
    const description = document.getElementById('arxiv-description').value;
    
    // Validate required fields
    if (!focus) {
        alert('Please enter a focus for your ArXiv search');
        return;
    }
    
    // Get reference context inputs
    const referenceContexts = [];
    document.querySelectorAll('.reference-context-input').forEach(function(input) {
        if (input.value.trim()) {
            referenceContexts.push(input.value.trim());
        }
    });
    
    // Get selected categories
    const categories = [];
    document.querySelectorAll('input[id^="category-"]:checked').forEach(function(checkbox) {
        categories.push(checkbox.value);
    });
    
    // Get selected subcategories
    const subcategories = [];
    document.querySelectorAll('input[id^="subcategory-"]:checked').forEach(function(checkbox) {
        subcategories.push(checkbox.value);
    });
    
    // Get time range
    const timeRange = document.getElementById('arxiv-time-range').value;
    
    // Get max papers
    const maxPapers = document.getElementById('arxiv-max-papers').value;
    
    // Get processing options
    const processingOptions = [];
    document.querySelectorAll('input[id^="process-"]:checked').forEach(function(checkbox) {
        processingOptions.push(checkbox.value);
    });
    
    // Get parallel workers
    const parallelWorkers = document.getElementById('arxiv-parallel-workers').value;
    
    // Get advanced options
    const advancedOptions = [];
    document.querySelectorAll('input[id^="advanced-"]:checked').forEach(function(checkbox) {
        advancedOptions.push(checkbox.value);
    });
    
    // Create configuration object
    const config = {
        focus: focus,
        description: description,
        referenceContexts: referenceContexts,
        categories: categories,
        subcategories: subcategories,
        timeRange: timeRange,
        maxPapers: maxPapers,
        processingOptions: processingOptions,
        parallelWorkers: parallelWorkers,
        advancedOptions: advancedOptions
    };
    
    // Send configuration to server
    fetch('/data-mining/api/arxiv/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('arxivConfigModal'));
            modal.hide();
            
            // Show success message
            alert('ArXiv mining started successfully!');
            
            // Refresh the task list
            if (typeof loadDataMiningTasks === 'function') {
                loadDataMiningTasks();
            }
        } else {
            alert('Error starting ArXiv mining: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error starting ArXiv mining:', error);
        alert('Error starting ArXiv mining. Please try again.');
    });
}

// Function to save configuration as a template
function saveAsTemplate() {
    // Get form values
    const focus = document.getElementById('arxiv-focus').value;
    
    // Validate required fields
    if (!focus) {
        alert('Please enter a focus for your template');
        return;
    }
    
    // Get all form values (same as startArxivMining function)
    // ...
    
    // Create template object
    const template = {
        name: focus,
        type: 'arxiv',
        config: {
            // Same configuration as in startArxivMining
            // ...
        }
    };
    
    // Send template to server
    fetch('/data-mining/api/templates/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(template)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Template saved successfully!');
        } else {
            alert('Error saving template: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error saving template:', error);
        alert('Error saving template. Please try again.');
    });
}

