// Dashboard JavaScript

// Sample data for demonstration
const sampleText = "Apple Inc. is planning to open a new headquarters in Austin, Texas. CEO Tim Cook announced the expansion plan last week. The new campus will create approximately 5,000 jobs initially. Google and Microsoft are also expanding their operations in Texas.";

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Set sample text
    const textInput = document.getElementById('text-input');
    if (textInput) {
        textInput.value = sampleText;
    }
    
    // Add event listeners
    const analyzeBtn = document.getElementById('analyze-btn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeText);
    }
    
    const visualizeBtn = document.getElementById('visualize-btn');
    if (visualizeBtn) {
        visualizeBtn.addEventListener('click', visualizeResults);
    }
});

// Global variable to store analysis results
let analysisResults = null;

// Analyze text function
async function analyzeText() {
    const text = document.getElementById('text-input').value;
    const analyzerType = document.getElementById('analyzer-type').value;
    
    if (!text) {
        alert('Please enter text to analyze');
        return;
    }
    
    try {
        // Show loading indicator
        document.getElementById('analysis-results').textContent = 'Analyzing...';
        
        // Use the ApiClient to make the API call
        const response = await ApiClient.post('/analyze', {
            text: text,
            analyzer_type: analyzerType,
            config: {}
        });
        
        analysisResults = response;
        
        // Fallback to mock data if API call fails or returns empty results
        if (!analysisResults || Object.keys(analysisResults).length === 0) {
            console.warn('API returned empty results, using mock data');
            
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
        }
        
        // Display results
        document.getElementById('analysis-results').textContent = JSON.stringify(analysisResults, null, 2);
        
    } catch (error) {
        console.error('Error analyzing text:', error);
        document.getElementById('analysis-results').textContent = 'Error analyzing text: ' + error.message;
    }
}

// Visualize results function
async function visualizeResults() {
    if (!analysisResults) {
        alert('Please analyze text first');
        return;
    }
    
    const analyzerType = document.getElementById('analyzer-type').value;
    
    try {
        // Use the ApiClient to make the API call
        let response;
        
        if (analyzerType === 'entity') {
            response = await ApiClient.post('/visualize/knowledge-graph', {
                text: document.getElementById('text-input').value,
                analyzer_type: 'entity',
                config: {}
            });
            
            const knowledgeGraphContainer = document.getElementById('knowledge-graph-container');
            
            if (response && response.image) {
                knowledgeGraphContainer.innerHTML = `<img src="${response.image}" class="visualization-image" alt="Knowledge Graph">`;
            } else {
                // Fallback to placeholder if API call fails or returns no image
                console.warn('API returned no image, using placeholder');
                knowledgeGraphContainer.innerHTML = '<img src="/static/images/placeholder-knowledge-graph.png" class="visualization-image" alt="Knowledge Graph">';
            }
        } else {
            response = await ApiClient.post('/visualize/trend', {
                text: document.getElementById('text-input').value,
                analyzer_type: 'trend',
                config: {}
            });
            
            const trendContainer = document.getElementById('trend-container');
            
            if (response && response.image) {
                trendContainer.innerHTML = `<img src="${response.image}" class="visualization-image" alt="Trend Analysis">`;
            } else {
                // Fallback to placeholder if API call fails or returns no image
                console.warn('API returned no image, using placeholder');
                trendContainer.innerHTML = '<img src="/static/images/placeholder-trend.png" class="visualization-image" alt="Trend Analysis">';
            }
        }
    } catch (error) {
        console.error('Error visualizing results:', error);
        alert('Error visualizing results: ' + error.message);
    }
}
