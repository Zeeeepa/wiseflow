/**
 * WebSearch Configuration Dialog JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const form = document.getElementById('websearch-config-form');
    const addReferenceBtn = document.getElementById('add-reference');
    const referenceContainer = document.getElementById('reference-context-container');
    const cancelButton = document.getElementById('cancel-button');
    const saveTemplateButton = document.getElementById('save-template-button');
    const customEngineCheckbox = document.getElementById('engine-custom');
    const customEngineUrl = document.getElementById('custom-engine-url');
    
    // Initialize custom engine URL field
    customEngineUrl.disabled = !customEngineCheckbox.checked;
    
    // Toggle custom engine URL field
    customEngineCheckbox.addEventListener('change', function() {
        customEngineUrl.disabled = !this.checked;
        if (this.checked) {
            customEngineUrl.focus();
        }
    });
    
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
        
        // Validate custom engine URL if selected
        if (customEngineCheckbox.checked && !customEngineUrl.value.trim()) {
            alert('Please enter a URL for the custom search engine.');
            customEngineUrl.focus();
            return;
        }
        
        // Collect form data
        const formData = new FormData(form);
        const data = {
            focus: formData.get('focus'),
            description: formData.get('description'),
            references: Array.from(formData.getAll('reference-context[]')).filter(ref => ref.trim() !== ''),
            searchEngines: {
                google: formData.has('engine-google'),
                bing: formData.has('engine-bing'),
                duckduckgo: formData.has('engine-duckduckgo'),
                baidu: formData.has('engine-baidu'),
                custom: formData.has('engine-custom') ? formData.get('custom-engine-url') : null
            },
            contentTypes: {
                articles: formData.has('content-articles'),
                blogs: formData.has('content-blogs'),
                docs: formData.has('content-docs'),
                forums: formData.has('content-forums'),
                news: formData.has('content-news'),
                academic: formData.has('content-academic')
            },
            timeRange: formData.get('time-range'),
            maxResults: parseInt(formData.get('max-results'), 10),
            searchDepth: formData.get('search-depth'),
            parallelWorkers: parseInt(formData.get('parallel-workers'), 10),
            advancedOptions: {
                extractCode: formData.has('extract-code'),
                followLinks: formData.has('follow-links'),
                saveFindings: formData.has('save-findings'),
                useProxy: formData.has('use-proxy')
            }
        };
        
        // Send data to server
        fetch('/api/data-mining/websearch/start', {
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
            console.error('Error starting WebSearch data mining:', error);
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
        
        // Validate custom engine URL if selected
        if (customEngineCheckbox.checked && !customEngineUrl.value.trim()) {
            alert('Please enter a URL for the custom search engine.');
            customEngineUrl.focus();
            return;
        }
        
        // Collect form data
        const formData = new FormData(form);
        const data = {
            name: focus,
            type: 'websearch',
            config: {
                focus: formData.get('focus'),
                description: formData.get('description'),
                references: Array.from(formData.getAll('reference-context[]')).filter(ref => ref.trim() !== ''),
                searchEngines: {
                    google: formData.has('engine-google'),
                    bing: formData.has('engine-bing'),
                    duckduckgo: formData.has('engine-duckduckgo'),
                    baidu: formData.has('engine-baidu'),
                    custom: formData.has('engine-custom') ? formData.get('custom-engine-url') : null
                },
                contentTypes: {
                    articles: formData.has('content-articles'),
                    blogs: formData.has('content-blogs'),
                    docs: formData.has('content-docs'),
                    forums: formData.has('content-forums'),
                    news: formData.has('content-news'),
                    academic: formData.has('content-academic')
                },
                timeRange: formData.get('time-range'),
                maxResults: parseInt(formData.get('max-results'), 10),
                searchDepth: formData.get('search-depth'),
                parallelWorkers: parseInt(formData.get('parallel-workers'), 10),
                advancedOptions: {
                    extractCode: formData.has('extract-code'),
                    followLinks: formData.has('follow-links'),
                    saveFindings: formData.has('save-findings'),
                    useProxy: formData.has('use-proxy')
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

