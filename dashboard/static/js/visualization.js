/**
 * Data Visualization Page JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const dataSourceSelect = document.getElementById('data-source');
    const timeRangeSelect = document.getElementById('time-range');
    const viewTypeSelect = document.getElementById('view-type');
    const groupingSelect = document.getElementById('grouping');
    const nodeSizeSelect = document.getElementById('node-size');
    const exportButton = document.getElementById('export-graph-btn');
    const saveViewButton = document.getElementById('save-view-btn');
    const shareButton = document.getElementById('share-btn');
    const viewIsolatedLink = document.querySelector('.view-isolated');
    
    // Initialize visualization
    let visualization = null;
    
    // Load initial visualization data
    loadVisualizationData();
    
    // Event listeners for controls
    dataSourceSelect.addEventListener('change', updateVisualization);
    timeRangeSelect.addEventListener('change', updateVisualization);
    viewTypeSelect.addEventListener('change', updateVisualization);
    groupingSelect.addEventListener('change', updateVisualization);
    nodeSizeSelect.addEventListener('change', updateVisualization);
    
    // Export graph button
    exportButton.addEventListener('click', exportGraph);
    
    // Save view button
    saveViewButton.addEventListener('click', saveView);
    
    // Share button
    shareButton.addEventListener('click', shareVisualization);
    
    // View isolated topics
    viewIsolatedLink.addEventListener('click', function(e) {
        e.preventDefault();
        viewIsolatedTopics();
    });
    
    // Load visualization data from server
    function loadVisualizationData() {
        const params = new URLSearchParams({
            source: dataSourceSelect.value,
            timeRange: timeRangeSelect.value
        });
        
        fetch(`/api/visualization/data?${params}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                renderVisualization(data);
                updateInsights(data.insights);
            })
            .catch(error => {
                console.error('Error loading visualization data:', error);
                showError('Failed to load visualization data. Please try again later.');
            });
    }
    
    // Update visualization based on control changes
    function updateVisualization() {
        const params = new URLSearchParams({
            source: dataSourceSelect.value,
            timeRange: timeRangeSelect.value,
            viewType: viewTypeSelect.value,
            grouping: groupingSelect.value,
            nodeSize: nodeSizeSelect.value
        });
        
        fetch(`/api/visualization/data?${params}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                renderVisualization(data);
                updateInsights(data.insights);
            })
            .catch(error => {
                console.error('Error updating visualization:', error);
                showError('Failed to update visualization. Please try again later.');
            });
    }
    
    // Render visualization based on data and selected view type
    function renderVisualization(data) {
        const canvas = document.getElementById('visualization-canvas');
        
        // Clear previous visualization
        while (canvas.firstChild) {
            canvas.removeChild(canvas.firstChild);
        }
        
        // Create visualization based on view type
        const viewType = viewTypeSelect.value;
        
        switch (viewType) {
            case 'network':
                renderNetworkGraph(canvas, data);
                break;
            case 'tree':
                renderTreeView(canvas, data);
                break;
            case 'chord':
                renderChordDiagram(canvas, data);
                break;
            case 'sankey':
                renderSankeyDiagram(canvas, data);
                break;
            case 'heatmap':
                renderHeatmap(canvas, data);
                break;
            default:
                renderNetworkGraph(canvas, data);
        }
    }
    
    // Render network graph visualization
    function renderNetworkGraph(container, data) {
        // This is a placeholder for actual visualization rendering
        // In a real implementation, this would use a library like D3.js or Vis.js
        
        const placeholder = document.createElement('div');
        placeholder.className = 'placeholder-visualization';
        
        // Create a simple placeholder visualization
        const mainNode = document.createElement('div');
        mainNode.className = 'node main-node';
        mainNode.textContent = 'RAG';
        placeholder.appendChild(mainNode);
        
        const leftConnection = document.createElement('div');
        leftConnection.className = 'connection left-connection';
        placeholder.appendChild(leftConnection);
        
        const rightConnection = document.createElement('div');
        rightConnection.className = 'connection right-connection';
        placeholder.appendChild(rightConnection);
        
        const subNodeLeft = document.createElement('div');
        subNodeLeft.className = 'node sub-node-left';
        subNodeLeft.textContent = 'Embeddings';
        placeholder.appendChild(subNodeLeft);
        
        const subNodeRight = document.createElement('div');
        subNodeRight.className = 'node sub-node-right';
        subNodeRight.textContent = 'Retrieval';
        placeholder.appendChild(subNodeRight);
        
        // Add more nodes and connections
        const subLeftConnection1 = document.createElement('div');
        subLeftConnection1.className = 'connection sub-left-connection-1';
        placeholder.appendChild(subLeftConnection1);
        
        const subLeftConnection2 = document.createElement('div');
        subLeftConnection2.className = 'connection sub-left-connection-2';
        placeholder.appendChild(subLeftConnection2);
        
        const subRightConnection1 = document.createElement('div');
        subRightConnection1.className = 'connection sub-right-connection-1';
        placeholder.appendChild(subRightConnection1);
        
        const subRightConnection2 = document.createElement('div');
        subRightConnection2.className = 'connection sub-right-connection-2';
        placeholder.appendChild(subRightConnection2);
        
        const leafNode1 = document.createElement('div');
        leafNode1.className = 'node leaf-node-1';
        leafNode1.textContent = 'Vector DB';
        placeholder.appendChild(leafNode1);
        
        const leafNode2 = document.createElement('div');
        leafNode2.className = 'node leaf-node-2';
        leafNode2.textContent = 'Text';
        placeholder.appendChild(leafNode2);
        
        const leafNode3 = document.createElement('div');
        leafNode3.className = 'node leaf-node-3';
        leafNode3.textContent = 'Semantic';
        placeholder.appendChild(leafNode3);
        
        const leafNode4 = document.createElement('div');
        leafNode4.className = 'node leaf-node-4';
        leafNode4.textContent = 'Keyword';
        placeholder.appendChild(leafNode4);
        
        container.appendChild(placeholder);
    }
    
    // Render tree view visualization
    function renderTreeView(container, data) {
        // Placeholder for tree view implementation
        renderNetworkGraph(container, data); // Fallback to network graph for now
    }
    
    // Render chord diagram visualization
    function renderChordDiagram(container, data) {
        // Placeholder for chord diagram implementation
        renderNetworkGraph(container, data); // Fallback to network graph for now
    }
    
    // Render sankey diagram visualization
    function renderSankeyDiagram(container, data) {
        // Placeholder for sankey diagram implementation
        renderNetworkGraph(container, data); // Fallback to network graph for now
    }
    
    // Render heatmap visualization
    function renderHeatmap(container, data) {
        // Placeholder for heatmap implementation
        renderNetworkGraph(container, data); // Fallback to network graph for now
    }
    
    // Update insights based on visualization data
    function updateInsights(insights) {
        const insightsList = document.getElementById('insights-list');
        
        // Clear previous insights
        insightsList.innerHTML = '';
        
        // Add new insights
        if (insights && insights.length > 0) {
            insights.forEach(insight => {
                const li = document.createElement('li');
                li.innerHTML = insight;
                insightsList.appendChild(li);
            });
        } else {
            // Default insights if none provided
            insightsList.innerHTML = `
                <li>Most connected topic: <strong>Vector Databases</strong></li>
                <li>Strongest relationship: <strong>RAG ↔ Embeddings</strong></li>
                <li>Emerging cluster: <strong>Hybrid Retrieval Methods</strong></li>
                <li>Isolated topics: <strong>3</strong> <a href="#" class="view-isolated">click to view</a></li>
            `;
            
            // Re-attach event listener to new link
            document.querySelector('.view-isolated').addEventListener('click', function(e) {
                e.preventDefault();
                viewIsolatedTopics();
            });
        }
    }
    
    // Export graph as image or data
    function exportGraph() {
        const format = prompt('Select export format (png, svg, json, csv):', 'png');
        
        if (!format) return;
        
        const params = new URLSearchParams({
            source: dataSourceSelect.value,
            timeRange: timeRangeSelect.value,
            viewType: viewTypeSelect.value,
            format: format.toLowerCase()
        });
        
        fetch(`/api/visualization/export?${params}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                if (format.toLowerCase() === 'json' || format.toLowerCase() === 'csv') {
                    return response.blob();
                } else {
                    return response.blob();
                }
            })
            .then(blob => {
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `visualization.${format.toLowerCase()}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
            })
            .catch(error => {
                console.error('Error exporting graph:', error);
                alert('Failed to export graph. Please try again later.');
            });
    }
    
    // Save current view configuration
    function saveView() {
        const viewName = prompt('Enter a name for this view:', 'My Visualization');
        
        if (!viewName) return;
        
        const data = {
            name: viewName,
            config: {
                source: dataSourceSelect.value,
                timeRange: timeRangeSelect.value,
                viewType: viewTypeSelect.value,
                grouping: groupingSelect.value,
                nodeSize: nodeSizeSelect.value
            }
        };
        
        fetch('/api/visualization/save-view', {
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
            alert('View saved successfully!');
        })
        .catch(error => {
            console.error('Error saving view:', error);
            alert('Failed to save view. Please try again later.');
        });
    }
    
    // Share visualization
    function shareVisualization() {
        const params = new URLSearchParams({
            source: dataSourceSelect.value,
            timeRange: timeRangeSelect.value,
            viewType: viewTypeSelect.value,
            grouping: groupingSelect.value,
            nodeSize: nodeSizeSelect.value
        });
        
        const shareUrl = `${window.location.origin}${window.location.pathname}?${params.toString()}`;
        
        // Copy to clipboard
        navigator.clipboard.writeText(shareUrl)
            .then(() => {
                alert('Visualization link copied to clipboard!');
            })
            .catch(err => {
                console.error('Error copying to clipboard:', err);
                // Fallback
                prompt('Copy this link to share your visualization:', shareUrl);
            });
    }
    
    // View isolated topics
    function viewIsolatedTopics() {
        const params = new URLSearchParams({
            source: dataSourceSelect.value,
            timeRange: timeRangeSelect.value,
            isolated: true
        });
        
        fetch(`/api/visualization/isolated-topics?${params}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Display isolated topics in a modal or update the visualization
                alert(`Isolated Topics:\n${data.topics.join('\n')}`);
            })
            .catch(error => {
                console.error('Error fetching isolated topics:', error);
                alert('Failed to fetch isolated topics. Please try again later.');
            });
    }
    
    // Show error message
    function showError(message) {
        const canvas = document.getElementById('visualization-canvas');
        
        // Clear previous content
        while (canvas.firstChild) {
            canvas.removeChild(canvas.firstChild);
        }
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'visualization-error';
        errorDiv.textContent = message;
        
        canvas.appendChild(errorDiv);
    }
    
    // Check for URL parameters to restore a shared view
    function checkUrlParams() {
        const urlParams = new URLSearchParams(window.location.search);
        
        if (urlParams.has('source')) {
            dataSourceSelect.value = urlParams.get('source');
        }
        
        if (urlParams.has('timeRange')) {
            timeRangeSelect.value = urlParams.get('timeRange');
        }
        
        if (urlParams.has('viewType')) {
            viewTypeSelect.value = urlParams.get('viewType');
        }
        
        if (urlParams.has('grouping')) {
            groupingSelect.value = urlParams.get('grouping');
        }
        
        if (urlParams.has('nodeSize')) {
            nodeSizeSelect.value = urlParams.get('nodeSize');
        }
        
        // If any parameters were found, update the visualization
        if (urlParams.has('source') || urlParams.has('timeRange') || 
            urlParams.has('viewType') || urlParams.has('grouping') || 
            urlParams.has('nodeSize')) {
            updateVisualization();
        }
    }
    
    // Check URL parameters on load
    checkUrlParams();
});

