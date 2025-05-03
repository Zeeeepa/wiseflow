/**
 * Main Application - Initializes all shared services and components
 * 
 * This module serves as the entry point for the Wiseflow application,
 * initializing all shared services and components.
 */

// Wiseflow Application
const WiseflowApp = (function() {
    // Application state
    let isInitialized = false;
    
    // Initialize shared services
    function initSharedServices() {
        console.log('Initializing shared services...');
        
        // Initialize theme manager
        if (window.ThemeManager) {
            ThemeManager.init();
        }
        
        // Initialize state manager (already initialized as a singleton)
        if (window.StateManager) {
            console.log('State Manager ready');
        }
        
        // Initialize event bus (already initialized as a singleton)
        if (window.EventBus) {
            console.log('Event Bus ready');
        }
        
        // Initialize API service (already initialized as a singleton)
        if (window.ApiService) {
            console.log('API Service ready');
        }
        
        console.log('Shared services initialized');
    }
    
    // Initialize components based on current page
    function initPageComponents() {
        console.log('Initializing page components...');
        
        // Determine current page
        const path = window.location.pathname;
        
        // Initialize components based on path
        if (path === '/' || path === '/dashboard') {
            initDashboardPage();
        } else if (path === '/data-mining') {
            initDataMiningPage();
        } else if (path === '/search') {
            initSearchPage();
        } else if (path === '/templates') {
            initTemplatesPage();
        } else if (path === '/database') {
            initDatabasePage();
        } else if (path === '/plugins') {
            initPluginsPage();
        } else if (path === '/monitor') {
            initMonitorPage();
        }
        
        console.log('Page components initialized');
    }
    
    // Initialize dashboard page components
    function initDashboardPage() {
        console.log('Initializing dashboard page components...');
        
        // Initialize all registered components for the dashboard page
        if (window.ComponentLoader) {
            const dashboardComponents = ComponentLoader.getComponentNames().filter(name => 
                name.startsWith('dashboard.') || name === 'dashboard'
            );
            
            dashboardComponents.forEach(name => {
                ComponentLoader.initialize(name);
            });
        }
    }
    
    // Initialize data mining page components
    function initDataMiningPage() {
        console.log('Initializing data mining page components...');
        
        // Initialize all registered components for the data mining page
        if (window.ComponentLoader) {
            const dataMiningComponents = ComponentLoader.getComponentNames().filter(name => 
                name.startsWith('dataMining.') || name === 'dataMining'
            );
            
            dataMiningComponents.forEach(name => {
                ComponentLoader.initialize(name);
            });
        }
    }
    
    // Initialize search page components
    function initSearchPage() {
        console.log('Initializing search page components...');
        
        // Initialize all registered components for the search page
        if (window.ComponentLoader) {
            const searchComponents = ComponentLoader.getComponentNames().filter(name => 
                name.startsWith('search.') || name === 'search'
            );
            
            searchComponents.forEach(name => {
                ComponentLoader.initialize(name);
            });
        }
    }
    
    // Initialize templates page components
    function initTemplatesPage() {
        console.log('Initializing templates page components...');
        
        // Initialize all registered components for the templates page
        if (window.ComponentLoader) {
            const templatesComponents = ComponentLoader.getComponentNames().filter(name => 
                name.startsWith('templates.') || name === 'templates'
            );
            
            templatesComponents.forEach(name => {
                ComponentLoader.initialize(name);
            });
        }
    }
    
    // Initialize database page components
    function initDatabasePage() {
        console.log('Initializing database page components...');
        
        // Initialize all registered components for the database page
        if (window.ComponentLoader) {
            const databaseComponents = ComponentLoader.getComponentNames().filter(name => 
                name.startsWith('database.') || name === 'database'
            );
            
            databaseComponents.forEach(name => {
                ComponentLoader.initialize(name);
            });
        }
    }
    
    // Initialize plugins page components
    function initPluginsPage() {
        console.log('Initializing plugins page components...');
        
        // Initialize all registered components for the plugins page
        if (window.ComponentLoader) {
            const pluginsComponents = ComponentLoader.getComponentNames().filter(name => 
                name.startsWith('plugins.') || name === 'plugins'
            );
            
            pluginsComponents.forEach(name => {
                ComponentLoader.initialize(name);
            });
        }
    }
    
    // Initialize monitor page components
    function initMonitorPage() {
        console.log('Initializing monitor page components...');
        
        // Initialize all registered components for the monitor page
        if (window.ComponentLoader) {
            const monitorComponents = ComponentLoader.getComponentNames().filter(name => 
                name.startsWith('monitor.') || name === 'monitor'
            );
            
            monitorComponents.forEach(name => {
                ComponentLoader.initialize(name);
            });
        }
    }
    
    // Setup global event listeners
    function setupGlobalEvents() {
        console.log('Setting up global events...');
        
        // Handle navigation events
        document.addEventListener('click', function(event) {
            // Handle navigation links
            if (event.target.tagName === 'A' && event.target.getAttribute('href') && 
                event.target.getAttribute('href').startsWith('/') && 
                !event.target.getAttribute('target')) {
                
                // Prevent default navigation
                event.preventDefault();
                
                // Get the href
                const href = event.target.getAttribute('href');
                
                // Navigate to the new page
                navigateTo(href);
            }
        });
        
        // Handle popstate events (browser back/forward)
        window.addEventListener('popstate', function(event) {
            // Reinitialize components for the new page
            initPageComponents();
        });
        
        // Handle errors
        window.addEventListener('error', function(event) {
            console.error('Global error:', event.error);
            
            // Show error toast
            if (window.Utils) {
                Utils.showToast(`An error occurred: ${event.error.message}`, 'error');
            }
        });
        
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', function(event) {
            console.error('Unhandled promise rejection:', event.reason);
            
            // Show error toast
            if (window.Utils) {
                Utils.showToast(`An error occurred: ${event.reason.message}`, 'error');
            }
        });
        
        console.log('Global events set up');
    }
    
    // Navigate to a new page
    function navigateTo(url) {
        console.log(`Navigating to: ${url}`);
        
        // Update browser history
        window.history.pushState({}, '', url);
        
        // Reinitialize components for the new page
        initPageComponents();
    }
    
    return {
        /**
         * Initialize the application
         */
        init: function() {
            if (isInitialized) {
                console.warn('Application already initialized');
                return;
            }
            
            console.log('Initializing Wiseflow application...');
            
            // Initialize shared services
            initSharedServices();
            
            // Initialize components for the current page
            initPageComponents();
            
            // Setup global event listeners
            setupGlobalEvents();
            
            isInitialized = true;
            console.log('Wiseflow application initialized');
            
            // Emit application ready event
            if (window.EventBus) {
                EventBus.emit('app:ready');
            }
        },
        
        /**
         * Navigate to a new page
         * @param {string} url - URL to navigate to
         */
        navigateTo: navigateTo,
        
        /**
         * Check if the application is initialized
         * @returns {boolean} Whether the application is initialized
         */
        isInitialized: function() {
            return isInitialized;
        },
        
        /**
         * Reset the application
         */
        reset: function() {
            if (!isInitialized) {
                return;
            }
            
            console.log('Resetting Wiseflow application...');
            
            // Reset component loader
            if (window.ComponentLoader) {
                ComponentLoader.reset();
            }
            
            // Reset state manager
            if (window.StateManager) {
                StateManager.resetState();
            }
            
            // Reset event bus
            if (window.EventBus) {
                EventBus.clearAll();
            }
            
            isInitialized = false;
            console.log('Wiseflow application reset');
        }
    };
})();

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    WiseflowApp.init();
});

