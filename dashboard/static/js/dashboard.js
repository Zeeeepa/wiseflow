// Dashboard JavaScript

// Sample data for demonstration
const sampleText = "Apple Inc. is planning to open a new headquarters in Austin, Texas. CEO Tim Cook announced the expansion plan last week. The new campus will create approximately 5,000 jobs initially. Google and Microsoft are also expanding their operations in Texas.";

// Dashboard component definition
const DashboardComponent = {
    // Component data
    data: {
        tasks: [],
        findings: [],
        filters: {
            dateRange: 'last7',
            source: 'all',
            relevance: 0
        },
        view: 'list',
        analysisResults: null
    },
    
    // Initialize the component
    init: function() {
        console.log('Initializing Dashboard component...');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Load initial data
        this.loadTasks();
        this.loadFindings();
        
        // Initialize charts
        this.initCharts();
        
        console.log('Dashboard component initialized');
    },
    
    // Set up event listeners
    setupEventListeners: function() {
        // Date range filter
        const dateRangeSelect = document.getElementById('date-range');
        if (dateRangeSelect) {
            dateRangeSelect.addEventListener('change', (e) => {
                this.data.filters.dateRange = e.target.value;
                
                // Show/hide custom date range inputs
                const customDateRange = document.getElementById('custom-date-range');
                if (customDateRange) {
                    customDateRange.style.display = e.target.value === 'custom' ? 'block' : 'none';
                }
            });
        }
        
        // Apply filters button
        const applyFiltersBtn = document.getElementById('apply-filters-btn');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => {
                this.applyFilters();
            });
        }
        
        // View toggle buttons
        const viewGridBtn = document.getElementById('view-grid-btn');
        const viewListBtn = document.getElementById('view-list-btn');
        
        if (viewGridBtn && viewListBtn) {
            viewGridBtn.addEventListener('click', () => {
                this.setView('grid');
                viewGridBtn.classList.add('active');
                viewListBtn.classList.remove('active');
            });
            
            viewListBtn.addEventListener('click', () => {
                this.setView('list');
                viewListBtn.classList.add('active');
                viewGridBtn.classList.remove('active');
            });
        }
        
        // Global search form
        const globalSearchForm = document.getElementById('global-search-form');
        if (globalSearchForm) {
            globalSearchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const searchInput = document.getElementById('global-search-input');
                if (searchInput && searchInput.value.trim()) {
                    this.searchFindings(searchInput.value.trim());
                }
            });
        }
        
        // Subscribe to events
        if (window.EventBus) {
            EventBus.on(EVENTS.TASK_UPDATED, this.handleTaskUpdated.bind(this));
            EventBus.on(EVENTS.DATA_LOADED, this.handleDataLoaded.bind(this));
        }
    },
    
    // Load tasks from API
    loadTasks: function() {
        console.log('Loading tasks...');
        
        const taskList = document.getElementById('task-list');
        if (!taskList) return;
        
        // In a real application, this would be an API call
        // For demonstration, we'll use mock data
        setTimeout(() => {
            const tasks = [
                { id: 1, name: 'GitHub Research', source: 'github', status: 'active', progress: 75 },
                { id: 2, name: 'ArXiv Papers Analysis', source: 'arxiv', status: 'paused', progress: 45 },
                { id: 3, name: 'YouTube Tech Trends', source: 'youtube', status: 'completed', progress: 100 },
                { id: 4, name: 'Web Research on AI', source: 'web', status: 'active', progress: 30 }
            ];
            
            this.data.tasks = tasks;
            this.renderTasks();
            
            // Emit event
            if (window.EventBus) {
                EventBus.emit(EVENTS.DATA_LOADED, { type: 'tasks', data: tasks });
            }
        }, 1000);
    },
    
    // Render tasks to the DOM
    renderTasks: function() {
        const taskList = document.getElementById('task-list');
        if (!taskList) return;
        
        // Clear loading indicator
        taskList.innerHTML = '';
        
        if (this.data.tasks.length === 0) {
            taskList.innerHTML = '<div class="text-center py-3">No tasks found</div>';
            return;
        }
        
        // Create task items
        this.data.tasks.forEach(task => {
            const taskItem = document.createElement('a');
            taskItem.href = '#';
            taskItem.className = 'list-group-item list-group-item-action';
            taskItem.setAttribute('aria-current', 'false');
            
            const sourceIcon = Utils.getSourceIcon(task.source);
            const progressClass = Utils.getProgressClass(task.progress);
            
            taskItem.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">
                        <i class="${sourceIcon} me-2" aria-hidden="true"></i>
                        ${task.name}
                    </h6>
                    <small>${task.status}</small>
                </div>
                <div class="progress mt-2" style="height: 5px;">
                    <div class="progress-bar ${progressClass}" role="progressbar" style="width: ${task.progress}%;" 
                        aria-valuenow="${task.progress}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            `;
            
            taskItem.addEventListener('click', (e) => {
                e.preventDefault();
                this.selectTask(task.id);
            });
            
            taskList.appendChild(taskItem);
        });
    },
    
    // Load findings from API
    loadFindings: function() {
        console.log('Loading findings...');
        
        const findingsContainer = document.getElementById('findings-container');
        if (!findingsContainer) return;
        
        // In a real application, this would be an API call
        // For demonstration, we'll use mock data
        setTimeout(() => {
            const findings = [
                {
                    id: 1,
                    title: 'Tech Companies Expanding in Texas',
                    summary: 'Multiple tech companies including Apple, Google, and Microsoft are expanding operations in Texas.',
                    source: 'web',
                    date: '2023-05-15',
                    relevance: 0.92,
                    tags: ['tech', 'expansion', 'jobs']
                },
                {
                    id: 2,
                    title: 'Apple\'s New Campus in Austin',
                    summary: 'Apple is building a new campus in Austin that will create 5,000 jobs initially.',
                    source: 'github',
                    date: '2023-05-14',
                    relevance: 0.88,
                    tags: ['apple', 'campus', 'jobs']
                },
                {
                    id: 3,
                    title: 'Job Growth in Tech Sector',
                    summary: 'The tech sector continues to show strong job growth despite economic concerns.',
                    source: 'arxiv',
                    date: '2023-05-12',
                    relevance: 0.75,
                    tags: ['jobs', 'economy', 'growth']
                },
                {
                    id: 4,
                    title: 'Tim Cook Announces Expansion Plans',
                    summary: 'Apple CEO Tim Cook announced expansion plans for the company in multiple states.',
                    source: 'youtube',
                    date: '2023-05-10',
                    relevance: 0.95,
                    tags: ['apple', 'expansion', 'tim cook']
                }
            ];
            
            this.data.findings = findings;
            this.renderFindings();
            
            // Emit event
            if (window.EventBus) {
                EventBus.emit(EVENTS.DATA_LOADED, { type: 'findings', data: findings });
            }
        }, 1500);
    },
    
    // Render findings to the DOM
    renderFindings: function() {
        const findingsContainer = document.getElementById('findings-container');
        if (!findingsContainer) return;
        
        // Clear loading indicator
        findingsContainer.innerHTML = '';
        
        if (this.data.findings.length === 0) {
            findingsContainer.innerHTML = '<div class="text-center py-3">No findings found</div>';
            return;
        }
        
        if (this.data.view === 'grid') {
            this.renderFindingsGrid(findingsContainer);
        } else {
            this.renderFindingsList(findingsContainer);
        }
    },
    
    // Render findings in list view
    renderFindingsList: function(container) {
        const listGroup = document.createElement('div');
        listGroup.className = 'list-group';
        
        this.data.findings.forEach(finding => {
            const findingItem = document.createElement('a');
            findingItem.href = '#';
            findingItem.className = 'list-group-item list-group-item-action';
            findingItem.setAttribute('aria-current', 'false');
            
            const sourceIcon = Utils.getSourceIcon(finding.source);
            const relevanceClass = finding.relevance >= 0.8 ? 'text-success' : (finding.relevance >= 0.5 ? 'text-warning' : 'text-danger');
            
            findingItem.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">${finding.title}</h5>
                    <small class="${relevanceClass}">${Math.round(finding.relevance * 100)}% relevant</small>
                </div>
                <p class="mb-1">${finding.summary}</p>
                <div class="d-flex justify-content-between align-items-center">
                    <small>
                        <i class="${sourceIcon} me-1" aria-hidden="true"></i>
                        ${finding.source} | ${finding.date}
                    </small>
                    <div>
                        ${finding.tags.map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('')}
                    </div>
                </div>
            `;
            
            findingItem.addEventListener('click', (e) => {
                e.preventDefault();
                this.showFindingDetails(finding.id);
            });
            
            listGroup.appendChild(findingItem);
        });
        
        container.appendChild(listGroup);
    },
    
    // Render findings in grid view
    renderFindingsGrid: function(container) {
        const row = document.createElement('div');
        row.className = 'row g-3';
        
        this.data.findings.forEach(finding => {
            const col = document.createElement('div');
            col.className = 'col-md-6 col-lg-4';
            
            const card = document.createElement('div');
            card.className = 'card h-100';
            
            const sourceIcon = Utils.getSourceIcon(finding.source);
            const relevanceClass = finding.relevance >= 0.8 ? 'text-success' : (finding.relevance >= 0.5 ? 'text-warning' : 'text-danger');
            
            card.innerHTML = `
                <div class="card-body">
                    <h5 class="card-title">${finding.title}</h5>
                    <h6 class="card-subtitle mb-2 text-muted">
                        <i class="${sourceIcon} me-1" aria-hidden="true"></i>
                        ${finding.source} | ${finding.date}
                    </h6>
                    <p class="card-text">${finding.summary}</p>
                </div>
                <div class="card-footer d-flex justify-content-between align-items-center">
                    <div>
                        ${finding.tags.map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('')}
                    </div>
                    <small class="${relevanceClass}">${Math.round(finding.relevance * 100)}% relevant</small>
                </div>
            `;
            
            card.addEventListener('click', () => {
                this.showFindingDetails(finding.id);
            });
            
            col.appendChild(card);
            row.appendChild(col);
        });
        
        container.appendChild(row);
    },
    
    // Show finding details in modal
    showFindingDetails: function(findingId) {
        const finding = this.data.findings.find(f => f.id === findingId);
        if (!finding) return;
        
        const modalContent = document.getElementById('expanded-finding-content');
        if (!modalContent) return;
        
        const sourceIcon = Utils.getSourceIcon(finding.source);
        const relevanceClass = finding.relevance >= 0.8 ? 'text-success' : (finding.relevance >= 0.5 ? 'text-warning' : 'text-danger');
        
        modalContent.innerHTML = `
            <div class="expanded-finding">
                <div class="finding-header">
                    <h4>${finding.title}</h4>
                    <div class="finding-meta">
                        <span class="source">
                            <i class="${sourceIcon} me-1" aria-hidden="true"></i>
                            ${finding.source}
                        </span>
                        <span class="date">${finding.date}</span>
                        <span class="relevance ${relevanceClass}">${Math.round(finding.relevance * 100)}% relevant</span>
                    </div>
                    <div class="tags mt-2">
                        ${finding.tags.map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('')}
                    </div>
                </div>
                <div class="finding-body mt-3">
                    <h5>Summary</h5>
                    <p>${finding.summary}</p>
                    
                    <h5 class="mt-3">Details</h5>
                    <p>This is a placeholder for the full content of the finding. In a real application, this would contain the complete text, data, or other information associated with this finding.</p>
                    
                    <h5 class="mt-3">Related Findings</h5>
                    <ul class="list-group">
                        ${this.data.findings.filter(f => f.id !== findingId).slice(0, 3).map(f => `
                            <li class="list-group-item">
                                <div class="d-flex w-100 justify-content-between">
                                    <h6 class="mb-1">${f.title}</h6>
                                    <small>${f.date}</small>
                                </div>
                                <small>${f.summary.substring(0, 100)}...</small>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            </div>
        `;
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('expanded-finding-modal'));
        modal.show();
    },
    
    // Initialize charts
    initCharts: function() {
        // In a real application, this would use D3.js to create charts
        // For demonstration, we'll use placeholder elements
        
        // Source distribution chart
        const sourceChartEl = document.getElementById('source-chart');
        if (sourceChartEl) {
            sourceChartEl.innerHTML = '<div class="placeholder-chart">Source Distribution Chart</div>';
        }
        
        // Relevance distribution chart
        const relevanceChartEl = document.getElementById('relevance-chart');
        if (relevanceChartEl) {
            relevanceChartEl.innerHTML = '<div class="placeholder-chart">Relevance Distribution Chart</div>';
        }
        
        // Time chart
        const timeChartEl = document.getElementById('time-chart');
        if (timeChartEl) {
            timeChartEl.innerHTML = '<div class="placeholder-chart">Findings Over Time Chart</div>';
        }
    },
    
    // Apply filters to findings
    applyFilters: function() {
        console.log('Applying filters...');
        
        // Get filter values
        const dateRange = document.getElementById('date-range').value;
        const source = document.getElementById('source-filter').value;
        const relevance = parseFloat(document.getElementById('relevance-filter').value);
        
        // Update filter data
        this.data.filters = {
            dateRange,
            source,
            relevance
        };
        
        // In a real application, this would make an API call with the filters
        // For demonstration, we'll just reload the findings
        const findingsContainer = document.getElementById('findings-container');
        if (findingsContainer) {
            findingsContainer.innerHTML = `
                <div class="text-center py-3">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Filtering findings...</p>
                </div>
            `;
            
            setTimeout(() => {
                this.renderFindings();
            }, 1000);
        }
    },
    
    // Set view mode (list or grid)
    setView: function(view) {
        if (view !== 'list' && view !== 'grid') return;
        
        this.data.view = view;
        this.renderFindings();
    },
    
    // Select a task
    selectTask: function(taskId) {
        console.log(`Selected task: ${taskId}`);
        
        // In a real application, this would load task details
        // For demonstration, we'll just highlight the selected task
        const taskItems = document.querySelectorAll('#task-list .list-group-item');
        taskItems.forEach((item, index) => {
            if (index === taskId - 1) {
                item.classList.add('active');
                item.setAttribute('aria-current', 'true');
            } else {
                item.classList.remove('active');
                item.setAttribute('aria-current', 'false');
            }
        });
    },
    
    // Search findings
    searchFindings: function(query) {
        console.log(`Searching for: ${query}`);
        
        // In a real application, this would make an API call
        // For demonstration, we'll use the existing findings
        const searchResults = this.data.findings.filter(finding => 
            finding.title.toLowerCase().includes(query.toLowerCase()) || 
            finding.summary.toLowerCase().includes(query.toLowerCase()) ||
            finding.tags.some(tag => tag.toLowerCase().includes(query.toLowerCase()))
        );
        
        // Display search results in modal
        const searchResultsContainer = document.getElementById('search-results-container');
        if (!searchResultsContainer) return;
        
        if (searchResults.length === 0) {
            searchResultsContainer.innerHTML = `
                <div class="alert alert-info">
                    No results found for "${query}".
                </div>
            `;
        } else {
            const listGroup = document.createElement('div');
            listGroup.className = 'list-group';
            
            searchResults.forEach(finding => {
                const resultItem = document.createElement('a');
                resultItem.href = '#';
                resultItem.className = 'list-group-item list-group-item-action';
                
                const sourceIcon = Utils.getSourceIcon(finding.source);
                
                resultItem.innerHTML = `
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">${finding.title}</h5>
                        <small>${finding.date}</small>
                    </div>
                    <p class="mb-1">${finding.summary}</p>
                    <small>
                        <i class="${sourceIcon} me-1" aria-hidden="true"></i>
                        ${finding.source}
                    </small>
                `;
                
                resultItem.addEventListener('click', (e) => {
                    e.preventDefault();
                    
                    // Hide search modal
                    const searchModal = bootstrap.Modal.getInstance(document.getElementById('search-results-modal'));
                    if (searchModal) {
                        searchModal.hide();
                    }
                    
                    // Show finding details
                    this.showFindingDetails(finding.id);
                });
                
                listGroup.appendChild(resultItem);
            });
            
            searchResultsContainer.innerHTML = '';
            searchResultsContainer.appendChild(listGroup);
        }
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('search-results-modal'));
        modal.show();
    },
    
    // Handle task updated event
    handleTaskUpdated: function(task) {
        console.log('Task updated:', task);
        
        // Update task in data
        const index = this.data.tasks.findIndex(t => t.id === task.id);
        if (index !== -1) {
            this.data.tasks[index] = task;
            this.renderTasks();
        }
    },
    
    // Handle data loaded event
    handleDataLoaded: function(data) {
        console.log('Data loaded:', data);
        
        // Update UI based on loaded data
        if (data.type === 'tasks') {
            // Tasks already updated in loadTasks
        } else if (data.type === 'findings') {
            // Findings already updated in loadFindings
        }
    },
    
    // Destroy the component
    destroy: function() {
        console.log('Destroying Dashboard component...');
        
        // Unsubscribe from events
        if (window.EventBus) {
            EventBus.off(EVENTS.TASK_UPDATED);
            EventBus.off(EVENTS.DATA_LOADED);
        }
        
        console.log('Dashboard component destroyed');
    }
};

// Register the Dashboard component with the ComponentLoader
document.addEventListener('DOMContentLoaded', function() {
    if (window.ComponentLoader) {
        ComponentLoader.register('dashboard', DashboardComponent);
        console.log('Dashboard component registered');
    } else {
        console.error('ComponentLoader not found. Dashboard component not registered.');
    }
});

// Analyze text function (for backward compatibility)
async function analyzeText() {
    // This function is kept for backward compatibility
    // In the new architecture, this functionality is handled by the DashboardComponent
    if (window.DashboardComponent && typeof DashboardComponent.analyzeText === 'function') {
        DashboardComponent.analyzeText();
    } else {
        console.warn('DashboardComponent.analyzeText not available. Using fallback implementation.');
        
        const text = document.getElementById('text-input').value;
        const analyzerType = document.getElementById('analyzer-type').value;
        
        if (!text) {
            alert('Please enter text to analyze');
            return;
        }
        
        try {
            // Show loading indicator
            document.getElementById('analysis-results').textContent = 'Analyzing...';
            
            // Mock data for demonstration
            let analysisResults;
            
            if (analyzerType === 'entity') {
                analysisResults = {
                    entities: [
                        { text: "Apple Inc.", type: "ORGANIZATION", confidence: 0.95 },
                        { text: "Austin", type: "LOCATION", confidence: 0.92 },
                        { text: "Texas", type: "LOCATION", confidence: 0.98 },
                        { text: "Tim Cook", type: "PERSON", confidence: 0.96 },
                        { text: "Google", type: "ORGANIZATION", confidence: 0.97 },
                        { text: "Microsoft", type: "ORGANIZATION", confidence: 0.98 }
                    ],
                    relationships: [
                        { source: "Apple Inc.", target: "Austin", type: "LOCATION_OF", confidence: 0.85 },
                        { source: "Tim Cook", target: "Apple Inc.", type: "WORKS_FOR", confidence: 0.92 },
                        { source: "Google", target: "Texas", type: "LOCATION_OF", confidence: 0.78 },
                        { source: "Microsoft", target: "Texas", type: "LOCATION_OF", confidence: 0.76 }
                    ]
                };
            } else {
                analysisResults = {
                    trends: [
                        {
                            name: "Tech Companies in Texas",
                            data: [
                                { time: "2020-01", value: 1 },
                                { time: "2020-02", value: 1 },
                                { time: "2020-03", value: 2 },
                                { time: "2020-04", value: 2 },
                                { time: "2020-05", value: 3 }
                            ]
                        },
                        {
                            name: "Job Creation",
                            data: [
                                { time: "2020-01", value: 1000 },
                                { time: "2020-02", value: 2000 },
                                { time: "2020-03", value: 3000 },
                                { time: "2020-04", value: 4000 },
                                { time: "2020-05", value: 5000 }
                            ]
                        }
                    ],
                    patterns: [
                        {
                            trend_name: "Tech Companies in Texas",
                            pattern_type: "upward_trend",
                            description: "Increasing number of tech companies in Texas",
                            confidence: 0.92
                        },
                        {
                            trend_name: "Job Creation",
                            pattern_type: "upward_trend",
                            description: "Steady increase in job creation",
                            confidence: 0.95
                        }
                    ]
                };
            }
            
            // Display results
            document.getElementById('analysis-results').textContent = JSON.stringify(analysisResults, null, 2);
            
        } catch (error) {
            console.error('Error analyzing text:', error);
            document.getElementById('analysis-results').textContent = 'Error analyzing text: ' + error.message;
        }
    }
}

// Visualize results function (for backward compatibility)
async function visualizeResults() {
    // This function is kept for backward compatibility
    // In the new architecture, this functionality is handled by the DashboardComponent
    if (window.DashboardComponent && typeof DashboardComponent.visualizeResults === 'function') {
        DashboardComponent.visualizeResults();
    } else {
        console.warn('DashboardComponent.visualizeResults not available. Using fallback implementation.');
        
        if (!window.analysisResults) {
            alert('Please analyze text first');
            return;
        }
        
        const analyzerType = document.getElementById('analyzer-type').value;
        
        try {
            if (analyzerType === 'entity') {
                const knowledgeGraphContainer = document.getElementById('knowledge-graph-container');
                knowledgeGraphContainer.innerHTML = '<img src="https://via.placeholder.com/500x300?text=Knowledge+Graph+Visualization" class="visualization-image" alt="Knowledge Graph">';
            } else {
                const trendContainer = document.getElementById('trend-container');
                trendContainer.innerHTML = '<img src="https://via.placeholder.com/500x300?text=Trend+Analysis+Visualization" class="visualization-image" alt="Trend Analysis">';
            }
        } catch (error) {
            console.error('Error visualizing results:', error);
            alert('Error visualizing results: ' + error.message);
        }
    }
}
