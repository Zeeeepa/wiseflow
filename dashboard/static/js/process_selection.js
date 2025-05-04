/**
 * Process Selection Dialog JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const sourceOptions = document.querySelectorAll('.source-option');
    const cancelButton = document.getElementById('cancel-button');
    const helpButton = document.getElementById('help-button');
    
    // Track selected source
    let selectedSource = null;
    
    // Source option selection
    sourceOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected class from all options
            sourceOptions.forEach(opt => opt.classList.remove('selected'));
            
            // Add selected class to clicked option
            this.classList.add('selected');
            
            // Store selected source
            selectedSource = this.getAttribute('data-source');
            
            // Navigate to appropriate configuration page
            setTimeout(() => {
                navigateToConfig(selectedSource);
            }, 300);
        });
    });
    
    // Cancel button
    cancelButton.addEventListener('click', function() {
        window.location.href = '/dashboard';
    });
    
    // Help button
    helpButton.addEventListener('click', function() {
        showHelp();
    });
    
    // Navigate to configuration page based on selected source
    function navigateToConfig(source) {
        switch (source) {
            case 'github':
                window.location.href = '/github-config';
                break;
            case 'websearch':
                window.location.href = '/websearch-config';
                break;
            case 'youtube':
                window.location.href = '/youtube-config';
                break;
            case 'arxiv':
                window.location.href = '/arxiv-config';
                break;
            default:
                console.error('Invalid source selected');
        }
    }
    
    // Show help information
    function showHelp() {
        const helpContent = {
            github: 'GitHub data mining allows you to extract information from repositories, code, issues, and pull requests.',
            websearch: 'WebSearch data mining enables you to gather information from various web sources including articles, blogs, and documentation.',
            youtube: 'YouTube data mining helps you extract information from videos, playlists, and comments.',
            arxiv: 'ArXiv data mining allows you to extract information from research papers and academic publications.'
        };
        
        let helpMessage = 'Data Source Information:\n\n';
        
        for (const [source, description] of Object.entries(helpContent)) {
            helpMessage += `${source.charAt(0).toUpperCase() + source.slice(1)}:\n${description}\n\n`;
        }
        
        alert(helpMessage);
    }
});

