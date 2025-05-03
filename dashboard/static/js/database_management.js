// Database Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Add event listeners for collection items
    const collectionItems = document.querySelectorAll('.list-group-item');
    collectionItems.forEach(item => {
        item.addEventListener('click', function() {
            // Toggle active class
            collectionItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            
            // In a real application, this would filter the findings
            // For demonstration, we'll just show an alert
            const collectionName = this.querySelector('span').textContent.trim();
            console.log(`Filtering by collection: ${collectionName}`);
            
            // Simulate API call to filter findings
            simulateFilterByCollection(collectionName);
        });
    });

    // Add event listeners for search
    const searchInput = document.querySelector('input[placeholder="Search findings..."]');
    const searchButton = searchInput.nextElementSibling;
    
    searchButton.addEventListener('click', function() {
        const searchTerm = searchInput.value.trim();
        if (searchTerm) {
            console.log(`Searching for: ${searchTerm}`);
            // Simulate API call to search findings
            simulateSearch(searchTerm);
        }
    });
    
    // Add event listener for Enter key in search input
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const searchTerm = searchInput.value.trim();
            if (searchTerm) {
                console.log(`Searching for: ${searchTerm}`);
                // Simulate API call to search findings
                simulateSearch(searchTerm);
            }
        }
    });

    // Add event listeners for filter dropdowns
    const filterDropdowns = document.querySelectorAll('.form-select');
    filterDropdowns.forEach(dropdown => {
        dropdown.addEventListener('change', function() {
            const filterType = this.options[0].text;
            const filterValue = this.value;
            console.log(`Filtering by ${filterType}: ${filterValue}`);
            
            // Simulate API call to filter findings
            simulateFilter(filterType, filterValue);
        });
    });

    // Add event listeners for action buttons
    const viewButtons = document.querySelectorAll('button:contains("View")');
    viewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const findingTitle = this.closest('.card-body').querySelector('.card-title').textContent;
            console.log(`Viewing finding: ${findingTitle}`);
            
            // In a real application, this would open a modal or navigate to a detail page
            alert(`Viewing details for: ${findingTitle}`);
        });
    });

    const editTagsButtons = document.querySelectorAll('button:contains("Edit Tags")');
    editTagsButtons.forEach(button => {
        button.addEventListener('click', function() {
            const findingTitle = this.closest('.card-body').querySelector('.card-title').textContent;
            console.log(`Editing tags for finding: ${findingTitle}`);
            
            // In a real application, this would open a modal for tag editing
            alert(`Editing tags for: ${findingTitle}`);
        });
    });

    const addToCollectionButtons = document.querySelectorAll('button:contains("Add to Collection")');
    addToCollectionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const findingTitle = this.closest('.card-body').querySelector('.card-title').textContent;
            console.log(`Adding finding to collection: ${findingTitle}`);
            
            // In a real application, this would open a modal for collection selection
            alert(`Adding to collection: ${findingTitle}`);
        });
    });

    // Add event listeners for action buttons at the bottom
    const actionButtons = document.querySelectorAll('.d-flex.justify-content-center button');
    actionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const actionText = this.textContent.trim();
            console.log(`Performing action: ${actionText}`);
            
            // In a real application, this would trigger the corresponding action
            alert(`Performing action: ${actionText}`);
        });
    });
});

// Helper function to find buttons by text content
HTMLElement.prototype.contains = function(text) {
    return this.textContent.includes(text);
};

// Simulate API call to filter findings by collection
function simulateFilterByCollection(collectionName) {
    // In a real application, this would be an API call
    // For demonstration, we'll just log to console
    console.log(`API call: GET /api/findings?collection=${encodeURIComponent(collectionName)}`);
    
    // Simulate loading state
    const findingsContainer = document.querySelector('.col-md-9');
    findingsContainer.innerHTML = '<div class="text-center my-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Loading findings...</p></div>';
    
    // Simulate API response delay
    setTimeout(() => {
        // For demonstration, we'll just reload the page
        window.location.reload();
    }, 1000);
}

// Simulate API call to search findings
function simulateSearch(searchTerm) {
    // In a real application, this would be an API call
    // For demonstration, we'll just log to console
    console.log(`API call: GET /api/findings?search=${encodeURIComponent(searchTerm)}`);
    
    // Simulate loading state
    const findingsContainer = document.querySelector('.col-md-9');
    findingsContainer.innerHTML = '<div class="text-center my-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Searching...</p></div>';
    
    // Simulate API response delay
    setTimeout(() => {
        // For demonstration, we'll just reload the page
        window.location.reload();
    }, 1000);
}

// Simulate API call to filter findings
function simulateFilter(filterType, filterValue) {
    // In a real application, this would be an API call
    // For demonstration, we'll just log to console
    console.log(`API call: GET /api/findings?${filterType.toLowerCase()}=${encodeURIComponent(filterValue)}`);
    
    // Simulate loading state
    const findingsContainer = document.querySelector('.col-md-9');
    findingsContainer.innerHTML = '<div class="text-center my-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Filtering...</p></div>';
    
    // Simulate API response delay
    setTimeout(() => {
        // For demonstration, we'll just reload the page
        window.location.reload();
    }, 1000);
}

