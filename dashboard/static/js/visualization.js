/**
 * Visualization Interface
 * Handles the data visualization functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the visualization interface
    initVisualization();
});

/**
 * Initialize the visualization interface
 */
function initVisualization() {
    // Hide loading indicator
    setTimeout(() => {
        document.getElementById('graph-loading').style.display = 'none';
        
        // Create the graph
        createNetworkGraph();
    }, 1000);
    
    // Add event listeners to the filter controls
    document.getElementById('apply-filters').addEventListener('click', function() {
        updateVisualization();
    });
    
    // Add event listeners to the view type, grouping, and node size controls
    document.getElementById('view-type').addEventListener('change', function() {
        updateVisualization();
    });
    
    document.getElementById('grouping').addEventListener('change', function() {
        updateVisualization();
    });
    
    document.getElementById('node-size').addEventListener('change', function() {
        updateVisualization();
    });
    
    // Add event listener to the export graph button
    document.getElementById('export-graph-btn').addEventListener('click', function() {
        exportGraph();
    });
    
    // Add event listener to the save view button
    document.getElementById('save-view-btn').addEventListener('click', function() {
        showSaveViewModal();
    });
    
    // Add event listener to the share button
    document.getElementById('share-btn').addEventListener('click', function() {
        showShareModal();
    });
    
    // Add event listener to the confirm save view button
    document.getElementById('confirm-save-view-btn').addEventListener('click', function() {
        saveView();
    });
    
    // Add event listener to the copy link button
    document.getElementById('copy-link-btn').addEventListener('click', function() {
        copyShareLink();
    });
    
    // Add event listener to the view isolated topics button
    document.getElementById('view-isolated-topics').addEventListener('click', function() {
        viewIsolatedTopics();
    });
    
    // Load visualization settings from URL if present
    loadSettingsFromUrl();
}

/**
 * Create a network graph visualization
 */
function createNetworkGraph() {
    // Get the container dimensions
    const container = document.getElementById('graph-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Sample data for the network graph
    const nodes = [
        { id: 'RAG', group: 1, size: 25 },
        { id: 'Embeddings', group: 1, size: 20 },
        { id: 'Retrieval', group: 1, size: 20 },
        { id: 'Vector DB', group: 2, size: 22 },
        { id: 'Text', group: 2, size: 15 },
        { id: 'Semantic', group: 3, size: 18 },
        { id: 'Keyword', group: 3, size: 15 },
        { id: 'Hybrid Methods', group: 4, size: 17 },
        { id: 'LLM Integration', group: 4, size: 16 },
        { id: 'Evaluation', group: 5, size: 14 },
        { id: 'Benchmarks', group: 5, size: 13 },
        { id: 'Isolated Topic 1', group: 6, size: 10 },
        { id: 'Isolated Topic 2', group: 6, size: 10 },
        { id: 'Isolated Topic 3', group: 6, size: 10 }
    ];
    
    const links = [
        { source: 'RAG', target: 'Embeddings', value: 5 },
        { source: 'RAG', target: 'Retrieval', value: 5 },
        { source: 'Embeddings', target: 'Vector DB', value: 4 },
        { source: 'Embeddings', target: 'Text', value: 3 },
        { source: 'Retrieval', target: 'Semantic', value: 4 },
        { source: 'Retrieval', target: 'Keyword', value: 3 },
        { source: 'Semantic', target: 'Hybrid Methods', value: 3 },
        { source: 'Vector DB', target: 'LLM Integration', value: 3 },
        { source: 'LLM Integration', target: 'Evaluation', value: 2 },
        { source: 'Evaluation', target: 'Benchmarks', value: 2 }
    ];
    
    // Create the SVG container
    const svg = d3.select('#graph-container')
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // Create a group for the graph
    const g = svg.append('g');
    
    // Create a zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });
    
    // Apply zoom behavior to the SVG
    svg.call(zoom);
    
    // Create a force simulation
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => d.size + 10));
    
    // Create the links
    const link = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(links)
        .enter()
        .append('line')
        .attr('class', 'link')
        .attr('stroke-width', d => Math.sqrt(d.value));
    
    // Create the nodes
    const node = g.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
    
    // Add circles to the nodes
    node.append('circle')
        .attr('r', d => d.size)
        .attr('fill', d => getColorByGroup(d.group));
    
    // Add labels to the nodes
    node.append('text')
        .attr('dy', 4)
        .attr('text-anchor', 'middle')
        .text(d => d.id)
        .attr('fill', '#333')
        .attr('font-size', d => Math.min(2 * d.size / 3, 12))
        .attr('pointer-events', 'none');
    
    // Add tooltips
    node.append('title')
        .text(d => d.id);
    
    // Update the positions on each tick of the simulation
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        node
            .attr('transform', d => `translate(${d.x},${d.y})`);
    });
    
    // Drag functions
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
    
    // Helper function to get color by group
    function getColorByGroup(group) {
        const colors = [
            '#4e79a7', '#f28e2c', '#e15759', '#76b7b2', 
            '#59a14f', '#edc949', '#af7aa1', '#ff9da7', 
            '#9c755f', '#bab0ab'
        ];
        return colors[(group - 1) % colors.length];
    }
}

/**
 * Update the visualization based on current settings
 */
function updateVisualization() {
    // Get the current settings
    const sourceFilter = document.getElementById('source-filter').value;
    const timeRange = document.getElementById('time-range').value;
    const viewType = document.getElementById('view-type').value;
    const grouping = document.getElementById('grouping').value;
    const nodeSize = document.getElementById('node-size').value;
    
    // Clear the current visualization
    const container = document.getElementById('graph-container');
    container.innerHTML = '';
    
    // Show loading indicator
    const loading = document.createElement('div');
    loading.className = 'text-center py-5';
    loading.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-2">Updating visualization...</p>
    `;
    container.appendChild(loading);
    
    // Simulate loading time
    setTimeout(() => {
        // Remove loading indicator
        container.innerHTML = '';
        
        // Create the appropriate visualization based on view type
        switch (viewType) {
            case 'network':
                createNetworkGraph();
                break;
            case 'tree':
                // Placeholder for tree view
                createPlaceholderVisualization('Tree View');
                break;
            case 'chord':
                // Placeholder for chord diagram
                createPlaceholderVisualization('Chord Diagram');
                break;
            case 'sankey':
                // Placeholder for sankey diagram
                createPlaceholderVisualization('Sankey Diagram');
                break;
            default:
                createNetworkGraph();
        }
        
        // Update the URL with the current settings
        updateUrl();
    }, 1000);
}

/**
 * Create a placeholder visualization
 * @param {string} title - The title of the visualization
 */
function createPlaceholderVisualization(title) {
    const container = document.getElementById('graph-container');
    const placeholder = document.createElement('div');
    placeholder.className = 'd-flex flex-column justify-content-center align-items-center h-100';
    placeholder.innerHTML = `
        <h4>${title}</h4>
        <p class="text-muted">This visualization type is coming soon.</p>
    `;
    container.appendChild(placeholder);
}

/**
 * Export the current graph
 */
function exportGraph() {
    // Get the SVG element
    const svg = document.querySelector('#graph-container svg');
    
    if (!svg) {
        alert('No visualization to export.');
        return;
    }
    
    // Create a copy of the SVG
    const svgCopy = svg.cloneNode(true);
    
    // Set the width and height attributes
    svgCopy.setAttribute('width', svg.clientWidth);
    svgCopy.setAttribute('height', svg.clientHeight);
    
    // Convert the SVG to a data URL
    const svgData = new XMLSerializer().serializeToString(svgCopy);
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const svgUrl = URL.createObjectURL(svgBlob);
    
    // Create a link to download the SVG
    const downloadLink = document.createElement('a');
    downloadLink.href = svgUrl;
    downloadLink.download = 'wiseflow_visualization.svg';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

/**
 * Show the save view modal
 */
function showSaveViewModal() {
    const modal = new bootstrap.Modal(document.getElementById('save-view-modal'));
    modal.show();
}

/**
 * Show the share modal
 */
function showShareModal() {
    // Generate the share link
    const shareLink = generateShareLink();
    
    // Set the share link in the input field
    document.getElementById('share-link').value = shareLink;
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('share-modal'));
    modal.show();
}

/**
 * Generate a share link with the current settings
 * @returns {string} The share link
 */
function generateShareLink() {
    // Get the current settings
    const sourceFilter = document.getElementById('source-filter').value;
    const timeRange = document.getElementById('time-range').value;
    const viewType = document.getElementById('view-type').value;
    const grouping = document.getElementById('grouping').value;
    const nodeSize = document.getElementById('node-size').value;
    
    // Create the URL parameters
    const params = new URLSearchParams();
    
    // Add the settings to the parameters if they should be included
    if (document.getElementById('include-filters').checked) {
        params.set('source', sourceFilter);
        params.set('time', timeRange);
    }
    
    if (document.getElementById('include-view-settings').checked) {
        params.set('view', viewType);
        params.set('grouping', grouping);
        params.set('nodeSize', nodeSize);
    }
    
    // Generate the full URL
    const url = new URL(window.location.href);
    url.search = params.toString();
    
    return url.toString();
}

/**
 * Copy the share link to the clipboard
 */
function copyShareLink() {
    const shareLink = document.getElementById('share-link');
    shareLink.select();
    document.execCommand('copy');
    
    // Show a success message
    const copyBtn = document.getElementById('copy-link-btn');
    const originalText = copyBtn.innerHTML;
    copyBtn.innerHTML = '<i class="bi bi-check"></i> Copied!';
    
    // Reset the button text after a delay
    setTimeout(() => {
        copyBtn.innerHTML = originalText;
    }, 2000);
}

/**
 * Save the current view
 */
function saveView() {
    // Get the view name and description
    const viewName = document.getElementById('view-name').value.trim();
    const viewDescription = document.getElementById('view-description').value.trim();
    
    if (!viewName) {
        alert('Please enter a name for the view.');
        return;
    }
    
    // Get the current settings
    const sourceFilter = document.getElementById('source-filter').value;
    const timeRange = document.getElementById('time-range').value;
    const viewType = document.getElementById('view-type').value;
    const grouping = document.getElementById('grouping').value;
    const nodeSize = document.getElementById('node-size').value;
    
    // Create the view data
    const viewData = {
        name: viewName,
        description: viewDescription,
        settings: {
            source: sourceFilter,
            time: timeRange,
            view: viewType,
            grouping: grouping,
            nodeSize: nodeSize
        },
        created: new Date().toISOString()
    };
    
    // Save the view (in a real application, this would be sent to the server)
    console.log('Saving view:', viewData);
    
    // Show a success message
    alert('View saved successfully!');
    
    // Hide the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('save-view-modal'));
    modal.hide();
}

/**
 * View isolated topics
 */
function viewIsolatedTopics() {
    // In a real application, this would filter the visualization to show only isolated topics
    alert('Isolated topics: Isolated Topic 1, Isolated Topic 2, Isolated Topic 3');
}

/**
 * Update the URL with the current settings
 */
function updateUrl() {
    // Get the current settings
    const sourceFilter = document.getElementById('source-filter').value;
    const timeRange = document.getElementById('time-range').value;
    const viewType = document.getElementById('view-type').value;
    const grouping = document.getElementById('grouping').value;
    const nodeSize = document.getElementById('node-size').value;
    
    // Create the URL parameters
    const params = new URLSearchParams();
    params.set('source', sourceFilter);
    params.set('time', timeRange);
    params.set('view', viewType);
    params.set('grouping', grouping);
    params.set('nodeSize', nodeSize);
    
    // Update the URL without reloading the page
    const url = new URL(window.location.href);
    url.search = params.toString();
    window.history.replaceState({}, '', url.toString());
}

/**
 * Load settings from the URL
 */
function loadSettingsFromUrl() {
    // Get the URL parameters
    const params = new URLSearchParams(window.location.search);
    
    // Set the source filter
    if (params.has('source')) {
        document.getElementById('source-filter').value = params.get('source');
    }
    
    // Set the time range
    if (params.has('time')) {
        document.getElementById('time-range').value = params.get('time');
    }
    
    // Set the view type
    if (params.has('view')) {
        document.getElementById('view-type').value = params.get('view');
    }
    
    // Set the grouping
    if (params.has('grouping')) {
        document.getElementById('grouping').value = params.get('grouping');
    }
    
    // Set the node size
    if (params.has('nodeSize')) {
        document.getElementById('node-size').value = params.get('nodeSize');
    }
}

