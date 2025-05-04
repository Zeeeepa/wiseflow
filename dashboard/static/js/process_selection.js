/**
 * Process Selection Dialog
 * Handles the selection of data sources for new data mining tasks
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the process selection dialog
    initProcessSelection();
});

/**
 * Initialize the process selection dialog
 */
function initProcessSelection() {
    // Get all source cards
    const sourceCards = document.querySelectorAll('.source-card');
    
    // Add click event listeners to source cards
    sourceCards.forEach(card => {
        card.addEventListener('click', function() {
            // Remove selected class from all cards
            sourceCards.forEach(c => c.classList.remove('selected'));
            
            // Add selected class to clicked card
            this.classList.add('selected');
            
            // Get the selected source
            const source = this.getAttribute('data-source');
            
            // Redirect to the appropriate configuration page
            setTimeout(() => {
                switch(source) {
                    case 'github':
                        window.location.href = '/data-mining/github-config';
                        break;
                    case 'websearch':
                        window.location.href = '/data-mining/websearch-config';
                        break;
                    case 'youtube':
                        window.location.href = '/data-mining/youtube-config';
                        break;
                    case 'arxiv':
                        window.location.href = '/data-mining/arxiv-config';
                        break;
                    default:
                        console.error('Unknown source:', source);
                }
            }, 300);
        });
    });
    
    // Add event listener to cancel button
    const cancelBtn = document.getElementById('cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            window.location.href = '/data-mining';
        });
    }
    
    // Add event listener to help button
    const helpBtn = document.getElementById('help-btn');
    const helpModal = new bootstrap.Modal(document.getElementById('help-modal'));
    
    if (helpBtn) {
        helpBtn.addEventListener('click', function() {
            helpModal.show();
        });
    }
}

/**
 * Handle source selection
 * @param {string} source - The selected data source
 */
function selectSource(source) {
    // This function can be called from external scripts
    const sourceCard = document.getElementById(`${source}-source`);
    if (sourceCard) {
        // Trigger click event on the source card
        sourceCard.click();
    }
}
