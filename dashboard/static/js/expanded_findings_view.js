// Expanded Findings View Dialog Implementation

/**
 * Initialize the expanded findings view dialog
 */
function initExpandedFindingsView() {
    // Create the modal if it doesn't exist
    createExpandedFindingsModal();
    
    // Add event listeners for the expanded findings view actions
    setupExpandedFindingsEventListeners();
}

/**
 * Create the expanded findings view modal
 */
function createExpandedFindingsModal() {
    // Check if modal already exists
    let modal = document.getElementById('expandedFindingsModal');
    if (modal) return;
    
    // Create modal element
    modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'expandedFindingsModal';
    modal.tabIndex = '-1';
    modal.setAttribute('aria-labelledby', 'expandedFindingsModalLabel');
    modal.setAttribute('aria-hidden', 'true');
    
    // Set modal content
    modal.innerHTML = `
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="expandedFindingsModalLabel">Findings: WebSearch - Best Ways to create codebase RAG</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="findings-container">
                        <div class="findings-header d-flex justify-content-between align-items-center mb-3">
                            <div class="filter-container">
                                <label for="findings-filter" class="me-2">Filter:</label>
                                <input type="text" id="findings-filter" class="form-control form-control-sm d-inline-block" style="width: 250px;">
                            </div>
                            <div class="sort-container">
                                <label for="findings-sort" class="me-2">Sort By:</label>
                                <select id="findings-sort" class="form-select form-select-sm d-inline-block" style="width: 150px;">
                                    <option value="relevance">Relevance</option>
                                    <option value="date">Date</option>
                                    <option value="source">Source</option>
                                    <option value="title">Title</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="findings-list">
                            <div class="findings-item card mb-3">
                                <div class="card-body">
                                    <h5 class="card-title">Building Effective RAG Systems for Codebases</h5>
                                    <h6 class="card-subtitle mb-2 text-muted">URL: <a href="#" class="article-url">ArticleURL1</a></h6>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span class="badge bg-primary">Relevance: 95%</span>
                                        <div class="btn-group">
                                            <button class="btn btn-sm btn-outline-primary view-btn">View</button>
                                            <button class="btn btn-sm btn-outline-success save-btn">Save</button>
                                            <button class="btn btn-sm btn-outline-secondary export-btn">Export</button>
                                        </div>
                                    </div>
                                    <p class="card-text">This article discusses techniques for implementing RAG systems specifically for code repositories, focusing on embedding methods and retrieval strategies optimized for source code.</p>
                                </div>
                            </div>
                            
                            <div class="findings-item card mb-3">
                                <div class="card-body">
                                    <h5 class="card-title">Vector Databases for Code Search</h5>
                                    <h6 class="card-subtitle mb-2 text-muted">URL: <a href="#" class="article-url">ArticleURL2</a></h6>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span class="badge bg-primary">Relevance: 92%</span>
                                        <div class="btn-group">
                                            <button class="btn btn-sm btn-outline-primary view-btn">View</button>
                                            <button class="btn btn-sm btn-outline-success save-btn">Save</button>
                                            <button class="btn btn-sm btn-outline-secondary export-btn">Export</button>
                                        </div>
                                    </div>
                                    <p class="card-text">Comprehensive comparison of vector databases for code search applications, with benchmarks on different programming languages and repository sizes.</p>
                                </div>
                            </div>
                            
                            <div class="findings-item card mb-3">
                                <div class="card-body">
                                    <h5 class="card-title">Hybrid Retrieval Methods for Source Code</h5>
                                    <h6 class="card-subtitle mb-2 text-muted">URL: <a href="#" class="article-url">ArticleURL3</a></h6>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span class="badge bg-primary">Relevance: 88%</span>
                                        <div class="btn-group">
                                            <button class="btn btn-sm btn-outline-primary view-btn">View</button>
                                            <button class="btn btn-sm btn-outline-success save-btn">Save</button>
                                            <button class="btn btn-sm btn-outline-secondary export-btn">Export</button>
                                        </div>
                                    </div>
                                    <p class="card-text">Analysis of hybrid retrieval methods combining semantic search with traditional code search techniques like AST parsing and symbol analysis.</p>
                                </div>
                            </div>
                            
                            <div class="findings-item card mb-3">
                                <div class="card-body">
                                    <h5 class="card-title">Optimizing RAG for Large Codebases</h5>
                                    <h6 class="card-subtitle mb-2 text-muted">URL: <a href="#" class="article-url">ArticleURL4</a></h6>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span class="badge bg-primary">Relevance: 85%</span>
                                        <div class="btn-group">
                                            <button class="btn btn-sm btn-outline-primary view-btn">View</button>
                                            <button class="btn btn-sm btn-outline-success save-btn">Save</button>
                                            <button class="btn btn-sm btn-outline-secondary export-btn">Export</button>
                                        </div>
                                    </div>
                                    <p class="card-text">Strategies for scaling RAG systems to handle very large codebases with millions of lines of code, including chunking strategies and hierarchical retrieval approaches.</p>
                                </div>
                            </div>
                            
                            <div class="findings-item card mb-3">
                                <div class="card-body">
                                    <h5 class="card-title">Code-Specific Embedding Models</h5>
                                    <h6 class="card-subtitle mb-2 text-muted">URL: <a href="#" class="article-url">ArticleURL5</a></h6>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span class="badge bg-primary">Relevance: 82%</span>
                                        <div class="btn-group">
                                            <button class="btn btn-sm btn-outline-primary view-btn">View</button>
                                            <button class="btn btn-sm btn-outline-success save-btn">Save</button>
                                            <button class="btn btn-sm btn-outline-secondary export-btn">Export</button>
                                        </div>
                                    </div>
                                    <p class="card-text">Overview of embedding models trained specifically for code, comparing their performance against general-purpose text embeddings when used in RAG systems.</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="findings-pagination d-flex justify-content-between align-items-center mt-4">
                            <button class="btn btn-sm btn-outline-secondary" id="prev-page-btn" disabled>Previous</button>
                            <span>Page 1 of 4</span>
                            <button class="btn btn-sm btn-outline-secondary" id="next-page-btn">Next</button>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <div class="actions-container d-flex justify-content-between w-100">
                        <div>
                            <button type="button" class="btn btn-outline-primary" id="export-all-btn">Export All</button>
                            <button type="button" class="btn btn-outline-success" id="create-report-btn">Create Report</button>
                            <button type="button" class="btn btn-outline-info" id="visualize-btn">Visualize</button>
                        </div>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Append modal to body
    document.body.appendChild(modal);
}

/**
 * Setup event listeners for the expanded findings view
 */
function setupExpandedFindingsEventListeners() {
    // Filter input event listener
    document.addEventListener('input', function(e) {
        if (e.target && e.target.id === 'findings-filter') {
            filterFindings(e.target.value);
        }
    });
    
    // Sort select event listener
    document.addEventListener('change', function(e) {
        if (e.target && e.target.id === 'findings-sort') {
            sortFindings(e.target.value);
        }
    });
    
    // Pagination buttons
    document.addEventListener('click', function(e) {
        if (e.target && e.target.id === 'prev-page-btn') {
            navigateFindings('prev');
        } else if (e.target && e.target.id === 'next-page-btn') {
            navigateFindings('next');
        }
    });
    
    // Action buttons
    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('view-btn')) {
            viewFinding(e.target.closest('.findings-item'));
        } else if (e.target && e.target.classList.contains('save-btn')) {
            saveFinding(e.target.closest('.findings-item'));
        } else if (e.target && e.target.classList.contains('export-btn')) {
            exportFinding(e.target.closest('.findings-item'));
        } else if (e.target && e.target.id === 'export-all-btn') {
            exportAllFindings();
        } else if (e.target && e.target.id === 'create-report-btn') {
            createReport();
        } else if (e.target && e.target.id === 'visualize-btn') {
            visualizeFindings();
        }
    });
}

/**
 * Show the expanded findings view for a specific task
 * @param {string} taskId - The ID of the task to show findings for
 */
function showExpandedFindings(taskId) {
    // Fetch findings data for the task
    fetchTaskFindings(taskId)
        .then(findings => {
            // Update modal title
            const modalTitle = document.getElementById('expandedFindingsModalLabel');
            if (modalTitle && findings.task) {
                modalTitle.textContent = `Findings: ${findings.task.task_type} - ${findings.task.name}`;
            }
            
            // Populate findings list
            populateFindingsList(findings.items || []);
            
            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('expandedFindingsModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error fetching findings:', error);
            alert('Error loading findings. Please try again.');
        });
}

/**
 * Fetch findings data for a task
 * @param {string} taskId - The ID of the task to fetch findings for
 * @returns {Promise} - Promise resolving to findings data
 */
function fetchTaskFindings(taskId) {
    // This would be replaced with an actual API call
    return new Promise((resolve, reject) => {
        // Mock data for demonstration
        setTimeout(() => {
            // Simulate successful response
            if (taskId) {
                resolve({
                    task: {
                        task_id: taskId,
                        name: 'Best Ways to create codebase RAG',
                        task_type: 'WebSearch',
                        status: 'active'
                    },
                    items: [
                        {
                            id: '1',
                            title: 'Building Effective RAG Systems for Codebases',
                            url: 'ArticleURL1',
                            relevance: 95,
                            summary: 'This article discusses techniques for implementing RAG systems specifically for code repositories, focusing on embedding methods and retrieval strategies optimized for source code.'
                        },
                        {
                            id: '2',
                            title: 'Vector Databases for Code Search',
                            url: 'ArticleURL2',
                            relevance: 92,
                            summary: 'Comprehensive comparison of vector databases for code search applications, with benchmarks on different programming languages and repository sizes.'
                        },
                        {
                            id: '3',
                            title: 'Hybrid Retrieval Methods for Source Code',
                            url: 'ArticleURL3',
                            relevance: 88,
                            summary: 'Analysis of hybrid retrieval methods combining semantic search with traditional code search techniques like AST parsing and symbol analysis.'
                        },
                        {
                            id: '4',
                            title: 'Optimizing RAG for Large Codebases',
                            url: 'ArticleURL4',
                            relevance: 85,
                            summary: 'Strategies for scaling RAG systems to handle very large codebases with millions of lines of code, including chunking strategies and hierarchical retrieval approaches.'
                        },
                        {
                            id: '5',
                            title: 'Code-Specific Embedding Models',
                            url: 'ArticleURL5',
                            relevance: 82,
                            summary: 'Overview of embedding models trained specifically for code, comparing their performance against general-purpose text embeddings when used in RAG systems.'
                        }
                    ],
                    pagination: {
                        current_page: 1,
                        total_pages: 4,
                        total_items: 20
                    }
                });
            } else {
                // Simulate error response
                reject(new Error('Invalid task ID'));
            }
        }, 500);
    });
}

/**
 * Populate the findings list with data
 * @param {Array} findings - Array of finding items
 */
function populateFindingsList(findings) {
    const findingsList = document.querySelector('.findings-list');
    if (!findingsList) return;
    
    // Clear existing content
    findingsList.innerHTML = '';
    
    if (findings.length === 0) {
        findingsList.innerHTML = '<div class="alert alert-info">No findings available for this task.</div>';
        return;
    }
    
    // Add each finding to the list
    findings.forEach(finding => {
        const findingItem = document.createElement('div');
        findingItem.className = 'findings-item card mb-3';
        findingItem.dataset.id = finding.id;
        
        findingItem.innerHTML = `
            <div class="card-body">
                <h5 class="card-title">${finding.title}</h5>
                <h6 class="card-subtitle mb-2 text-muted">URL: <a href="#" class="article-url">${finding.url}</a></h6>
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="badge bg-primary">Relevance: ${finding.relevance}%</span>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-primary view-btn">View</button>
                        <button class="btn btn-sm btn-outline-success save-btn">Save</button>
                        <button class="btn btn-sm btn-outline-secondary export-btn">Export</button>
                    </div>
                </div>
                <p class="card-text">${finding.summary}</p>
            </div>
        `;
        
        findingsList.appendChild(findingItem);
    });
    
    // Update pagination
    updatePagination(1, 4);
}

/**
 * Update pagination controls
 * @param {number} currentPage - Current page number
 * @param {number} totalPages - Total number of pages
 */
function updatePagination(currentPage, totalPages) {
    const paginationContainer = document.querySelector('.findings-pagination');
    if (!paginationContainer) return;
    
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const pageInfo = paginationContainer.querySelector('span');
    
    if (prevBtn) {
        prevBtn.disabled = currentPage <= 1;
    }
    
    if (nextBtn) {
        nextBtn.disabled = currentPage >= totalPages;
    }
    
    if (pageInfo) {
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    }
}

/**
 * Filter findings based on search text
 * @param {string} filterText - Text to filter by
 */
function filterFindings(filterText) {
    const findingItems = document.querySelectorAll('.findings-item');
    const lowerFilterText = filterText.toLowerCase();
    
    findingItems.forEach(item => {
        const title = item.querySelector('.card-title').textContent.toLowerCase();
        const summary = item.querySelector('.card-text').textContent.toLowerCase();
        
        if (title.includes(lowerFilterText) || summary.includes(lowerFilterText)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

/**
 * Sort findings based on selected criteria
 * @param {string} sortBy - Criteria to sort by (relevance, date, source, title)
 */
function sortFindings(sortBy) {
    const findingsList = document.querySelector('.findings-list');
    const findingItems = Array.from(document.querySelectorAll('.findings-item'));
    
    findingItems.sort((a, b) => {
        if (sortBy === 'relevance') {
            const relevanceA = parseInt(a.querySelector('.badge').textContent.match(/\d+/)[0] || '0');
            const relevanceB = parseInt(b.querySelector('.badge').textContent.match(/\d+/)[0] || '0');
            return relevanceB - relevanceA; // Higher relevance first
        } else if (sortBy === 'title') {
            const titleA = a.querySelector('.card-title').textContent;
            const titleB = b.querySelector('.card-title').textContent;
            return titleA.localeCompare(titleB);
        } else if (sortBy === 'source') {
            const sourceA = a.querySelector('.article-url').textContent;
            const sourceB = b.querySelector('.article-url').textContent;
            return sourceA.localeCompare(sourceB);
        }
        // Default to relevance sorting
        return 0;
    });
    
    // Clear and re-append sorted items
    findingsList.innerHTML = '';
    findingItems.forEach(item => {
        findingsList.appendChild(item);
    });
}

/**
 * Navigate to previous or next page of findings
 * @param {string} direction - Direction to navigate ('prev' or 'next')
 */
function navigateFindings(direction) {
    const paginationSpan = document.querySelector('.findings-pagination span');
    if (!paginationSpan) return;
    
    const pageInfo = paginationSpan.textContent.match(/Page (\d+) of (\d+)/);
    if (!pageInfo) return;
    
    let currentPage = parseInt(pageInfo[1]);
    const totalPages = parseInt(pageInfo[2]);
    
    if (direction === 'prev' && currentPage > 1) {
        currentPage--;
    } else if (direction === 'next' && currentPage < totalPages) {
        currentPage++;
    } else {
        return;
    }
    
    // Update pagination display
    updatePagination(currentPage, totalPages);
    
    // In a real implementation, this would fetch the new page of findings
    // For this demo, we'll just show a loading message
    const findingsList = document.querySelector('.findings-list');
    if (findingsList) {
        findingsList.innerHTML = '<div class="text-center p-5"><i class="bi bi-arrow-repeat spin me-2"></i> Loading findings...</div>';
        
        // Simulate loading new page
        setTimeout(() => {
            // This would be replaced with actual data fetching
            populateFindingsList([
                {
                    id: `${currentPage}1`,
                    title: `Page ${currentPage} - Finding 1`,
                    url: `ArticleURL${currentPage}1`,
                    relevance: 95 - (currentPage - 1) * 5,
                    summary: 'Example finding for pagination demonstration.'
                },
                {
                    id: `${currentPage}2`,
                    title: `Page ${currentPage} - Finding 2`,
                    url: `ArticleURL${currentPage}2`,
                    relevance: 92 - (currentPage - 1) * 5,
                    summary: 'Example finding for pagination demonstration.'
                },
                {
                    id: `${currentPage}3`,
                    title: `Page ${currentPage} - Finding 3`,
                    url: `ArticleURL${currentPage}3`,
                    relevance: 88 - (currentPage - 1) * 5,
                    summary: 'Example finding for pagination demonstration.'
                },
                {
                    id: `${currentPage}4`,
                    title: `Page ${currentPage} - Finding 4`,
                    url: `ArticleURL${currentPage}4`,
                    relevance: 85 - (currentPage - 1) * 5,
                    summary: 'Example finding for pagination demonstration.'
                },
                {
                    id: `${currentPage}5`,
                    title: `Page ${currentPage} - Finding 5`,
                    url: `ArticleURL${currentPage}5`,
                    relevance: 82 - (currentPage - 1) * 5,
                    summary: 'Example finding for pagination demonstration.'
                }
            ]);
        }, 800);
    }
}

/**
 * View a specific finding
 * @param {Element} findingItem - The finding item element
 */
function viewFinding(findingItem) {
    if (!findingItem) return;
    
    const title = findingItem.querySelector('.card-title').textContent;
    const url = findingItem.querySelector('.article-url').textContent;
    
    // In a real implementation, this would open a detailed view
    // For this demo, we'll just show an alert
    alert(`Viewing: ${title}\nURL: ${url}`);
}

/**
 * Save a specific finding
 * @param {Element} findingItem - The finding item element
 */
function saveFinding(findingItem) {
    if (!findingItem) return;
    
    const title = findingItem.querySelector('.card-title').textContent;
    
    // In a real implementation, this would save the finding
    // For this demo, we'll just show an alert
    alert(`Saved: ${title}`);
}

/**
 * Export a specific finding
 * @param {Element} findingItem - The finding item element
 */
function exportFinding(findingItem) {
    if (!findingItem) return;
    
    const title = findingItem.querySelector('.card-title').textContent;
    
    // In a real implementation, this would export the finding
    // For this demo, we'll just show an alert
    alert(`Exported: ${title}`);
}

/**
 * Export all findings
 */
function exportAllFindings() {
    // In a real implementation, this would export all findings
    // For this demo, we'll just show an alert
    alert('Exporting all findings...');
}

/**
 * Create a report from findings
 */
function createReport() {
    // In a real implementation, this would create a report
    // For this demo, we'll just show an alert
    alert('Creating report from findings...');
}

/**
 * Visualize findings
 */
function visualizeFindings() {
    // In a real implementation, this would show a visualization
    // For this demo, we'll just show an alert
    alert('Visualizing findings...');
}

// Initialize when the document is ready
document.addEventListener('DOMContentLoaded', function() {
    initExpandedFindingsView();
    
    // Note: View Findings button event listeners are already registered in addTaskButtonEventListeners()
});

