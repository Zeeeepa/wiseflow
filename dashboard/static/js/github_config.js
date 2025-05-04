/**
 * GitHub Configuration Dialog JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const form = document.getElementById('github-config-form');
    const addReferenceBtn = document.getElementById('add-reference');
    const referenceContainer = document.getElementById('reference-context-container');
    const cancelButton = document.getElementById('cancel-button');
    const saveTemplateButton = document.getElementById('save-template-button');
    
    // Add more reference context fields
    addReferenceBtn.addEventListener('click', function() {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'reference-context full-width';
        input.name = 'reference-context[]';
        referenceContainer.appendChild(input);
    });
    
    // Form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate form
        const focus = document.getElementById('focus').value.trim();
        if (!focus) {
            alert('Please enter a focus for your data mining task.');
            return;
        }
        
        // Collect form data
        const formData = new FormData(form);
        const data = {
            focus: formData.get('focus'),
            description: formData.get('description'),
            references: Array.from(formData.getAll('reference-context[]')).filter(ref => ref.trim() !== ''),
            searchScheme: formData.get('search-scheme'),
            options: {
                searchRepos: formData.has('search-repos'),
                searchCode: formData.has('search-code'),
                searchIssues: formData.has('search-issues'),
                searchPRs: formData.has('search-prs')
            },
            goal: formData.get('goal'),
            parallelWorkers: parseInt(formData.get('parallel-workers'), 10),
            advancedOptions: {
                cloneRepos: formData.has('clone-repos'),
                followLinks: formData.has('follow-links'),
                includeForks: formData.has('include-forks'),
                saveFindings: formData.has('save-findings')
            }
        };
        
        // Send data to server
        fetch('/api/data-mining/github/start', {
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
            // Handle successful response
            window.location.href = '/dashboard';
        })
        .catch(error => {
            console.error('Error starting GitHub data mining:', error);
            alert('There was an error starting the data mining process. Please try again.');
        });
    });
    
    // Save as template
    saveTemplateButton.addEventListener('click', function() {
        // Validate form
        const focus = document.getElementById('focus').value.trim();
        if (!focus) {
            alert('Please enter a focus for your template.');
            return;
        }
        
        // Collect form data
        const formData = new FormData(form);
        const data = {
            name: focus,
            type: 'github',
            config: {
                focus: formData.get('focus'),
                description: formData.get('description'),
                references: Array.from(formData.getAll('reference-context[]')).filter(ref => ref.trim() !== ''),
                searchScheme: formData.get('search-scheme'),
                options: {
                    searchRepos: formData.has('search-repos'),
                    searchCode: formData.has('search-code'),
                    searchIssues: formData.has('search-issues'),
                    searchPRs: formData.has('search-prs')
                },
                goal: formData.get('goal'),
                parallelWorkers: parseInt(formData.get('parallel-workers'), 10),
                advancedOptions: {
                    cloneRepos: formData.has('clone-repos'),
                    followLinks: formData.has('follow-links'),
                    includeForks: formData.has('include-forks'),
                    saveFindings: formData.has('save-findings')
                }
            }
        };
        
        // Send data to server
        fetch('/api/templates/save', {
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
            alert('Template saved successfully!');
        })
        .catch(error => {
            console.error('Error saving template:', error);
            alert('There was an error saving the template. Please try again.');
        });
    });
    
    // Cancel button
    cancelButton.addEventListener('click', function() {
        window.location.href = '/dashboard';
    });
});

