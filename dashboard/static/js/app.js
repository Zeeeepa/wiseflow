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
    let initializationPromise = null;
    
    // Configuration
    const config = {
        // API configuration
        api: {
            baseUrl: '/api',
            version: 'v1',
            timeout: 30000 // 30 seconds
        },
        
        // Debug mode
        debug: false
    };
    
    // Initialize shared services
    function initSharedServices() {
        console.log('Initializing shared services...');
        
        return new Promise((resolve, reject) => {
            try {
                // Set API configuration
                window.API_BASE_URL = config.api.baseUrl;
                window.API_VERSION = config.api.version;
                
                // Set debug mode
                window.DEBUG_MODE = config.debug;
                
                // Initialize theme manager
                if (window.ThemeManager) {
                    ThemeManager.init();
                    console.log('Theme Manager initialized');
                } else {
                    console.warn('Theme Manager not found');
                }
                
                // Initialize state manager (already initialized as a singleton)
                if (window.StateManager) {
                    console.log('State Manager ready');
                } else {
                    console.warn('State Manager not found');
                }
                
                // Initialize event bus (already initialized as a singleton)
                if (window.EventBus) {
                    console.log('Event Bus ready');
                } else {
                    console.warn('Event Bus not found');
                }
                
                // Initialize API service (already initialized as a singleton)
                if (window.ApiService) {
                    console.log('API Service ready');
                } else {
                    console.warn('API Service not found');
                }
                
                console.log('Shared services initialized');
                resolve();
            } catch (error) {
                console.error('Error initializing shared services:', error);
                reject(error);
            }
        });
    }
    
    // Initialize components based on current page
    function initPageComponents() {
        console.log('Initializing page components...');
        
        return new Promise((resolve, reject) => {
            try {
                // Determine current page
                const path = window.location.pathname;
                
                // Initialize components based on path
                let initPromise;
                
                if (path === '/' || path === '/dashboard') {
                    initPromise = initDashboardPage();
                } else if (path === '/data-mining') {
                    initPromise = initDataMiningPage();
                } else if (path === '/search') {
                    initPromise = initSearchPage();
                } else if (path === '/templates') {
                    initPromise = initTemplatesPage();
                } else if (path === '/database') {
                    initPromise = initDatabasePage();
                } else if (path === '/plugins') {
                    initPromise = initPluginsPage();
                } else if (path === '/monitor') {
                    initPromise = initMonitorPage();
                } else {
                    // Default to dashboard for unknown paths
                    console.warn(`Unknown path: ${path}, defaulting to dashboard`);
                    initPromise = initDashboardPage();
                }
                
                initPromise.then(() => {
                    console.log('Page components initialized');
                    resolve();
                }).catch(error => {
                    console.error('Error initializing page components:', error);
                    reject(error);
                });
            } catch (error) {
                console.error('Error in initPageComponents:', error);
                reject(error);
            }
        });
    }
    
    // Initialize dashboard page components
    function initDashboardPage() {
        console.log('Initializing dashboard page components...');
        
        return new Promise((resolve, reject) => {
            try {
                // Check if ComponentLoader is available
                if (!window.ComponentLoader) {
                    console.error('ComponentLoader not found');
                    reject(new Error('ComponentLoader not found'));
                    return;
                }
                
                // Get dashboard components
                const dashboardComponents = ComponentLoader.getComponentNames().filter(name => 
                    name.startsWith('dashboard.') || name === 'dashboard'
                );
                
                if (dashboardComponents.length === 0) {
                    console.warn('No dashboard components found');
                }
                
                // Initialize each component
                const initPromises = dashboardComponents.map(name => {
                    return new Promise((resolveComponent, rejectComponent) => {
                        try {
                            const success = ComponentLoader.initialize(name);
                            if (success) {
                                console.log(`Component initialized: ${name}`);
                                resolveComponent();
                            } else {
                                console.error(`Failed to initialize component: ${name}`);
                                rejectComponent(new Error(`Failed to initialize component: ${name}`));
                            }
                        } catch (error) {
                            console.error(`Error initializing component ${name}:`, error);
                            rejectComponent(error);
                        }
                    });
                });
                
                // Wait for all components to initialize
                Promise.allSettled(initPromises).then(results => {
                    const failedComponents = results.filter(result => result.status === 'rejected');
                    
                    if (failedComponents.length > 0) {
                        console.warn(`${failedComponents.length} components failed to initialize`);
                    }
                    
                    console.log('Dashboard page components initialized');
                    resolve();
                });
            } catch (error) {
                console.error('Error in initDashboardPage:', error);
                reject(error);
            }
        });
    }
    
    // Initialize data mining page components
    function initDataMiningPage() {
        console.log('Initializing data mining page components...');
        
        return new Promise((resolve, reject) => {
            try {
                // Check if ComponentLoader is available
                if (!window.ComponentLoader) {
                    console.error('ComponentLoader not found');
                    reject(new Error('ComponentLoader not found'));
                    return;
                }
                
                // Get data mining components
                const dataMiningComponents = ComponentLoader.getComponentNames().filter(name => 
                    name.startsWith('dataMining.') || name === 'dataMining'
                );
                
                if (dataMiningComponents.length === 0) {
                    console.warn('No data mining components found');
                }
                
                // Initialize each component
                const initPromises = dataMiningComponents.map(name => {
                    return new Promise((resolveComponent, rejectComponent) => {
                        try {
                            const success = ComponentLoader.initialize(name);
                            if (success) {
                                console.log(`Component initialized: ${name}`);
                                resolveComponent();
                            } else {
                                console.error(`Failed to initialize component: ${name}`);
                                rejectComponent(new Error(`Failed to initialize component: ${name}`));
                            }
                        } catch (error) {
                            console.error(`Error initializing component ${name}:`, error);
                            rejectComponent(error);
                        }
                    });
                });
                
                // Wait for all components to initialize
                Promise.allSettled(initPromises).then(results => {
                    const failedComponents = results.filter(result => result.status === 'rejected');
                    
                    if (failedComponents.length > 0) {
                        console.warn(`${failedComponents.length} components failed to initialize`);
                    }
                    
                    console.log('Data mining page components initialized');
                    resolve();
                });
            } catch (error) {
                console.error('Error in initDataMiningPage:', error);
                reject(error);
            }
        });
    }
    
    // Initialize search page components
    function initSearchPage() {
        console.log('Initializing search page components...');
        
        return new Promise((resolve, reject) => {
            try {
                // Check if ComponentLoader is available
                if (!window.ComponentLoader) {
                    console.error('ComponentLoader not found');
                    reject(new Error('ComponentLoader not found'));
                    return;
                }
                
                // Get search components
                const searchComponents = ComponentLoader.getComponentNames().filter(name => 
                    name.startsWith('search.') || name === 'search'
                );
                
                if (searchComponents.length === 0) {
                    console.warn('No search components found');
                }
                
                // Initialize each component
                const initPromises = searchComponents.map(name => {
                    return new Promise((resolveComponent, rejectComponent) => {
                        try {
                            const success = ComponentLoader.initialize(name);
                            if (success) {
                                console.log(`Component initialized: ${name}`);
                                resolveComponent();
                            } else {
                                console.error(`Failed to initialize component: ${name}`);
                                rejectComponent(new Error(`Failed to initialize component: ${name}`));
                            }
                        } catch (error) {
                            console.error(`Error initializing component ${name}:`, error);
                            rejectComponent(error);
                        }
                    });
                });
                
                // Wait for all components to initialize
                Promise.allSettled(initPromises).then(results => {
                    const failedComponents = results.filter(result => result.status === 'rejected');
                    
                    if (failedComponents.length > 0) {
                        console.warn(`${failedComponents.length} components failed to initialize`);
                    }
                    
                    console.log('Search page components initialized');
                    resolve();
                });
            } catch (error) {
                console.error('Error in initSearchPage:', error);
                reject(error);
            }
        });
    }
    
    // Initialize templates page components
    function initTemplatesPage() {
        console.log('Initializing templates page components...');
        
        return new Promise((resolve, reject) => {
            try {
                // Check if ComponentLoader is available
                if (!window.ComponentLoader) {
                    console.error('ComponentLoader not found');
                    reject(new Error('ComponentLoader not found'));
                    return;
                }
                
                // Get templates components
                const templatesComponents = ComponentLoader.getComponentNames().filter(name => 
                    name.startsWith('templates.') || name === 'templates'
                );
                
                if (templatesComponents.length === 0) {
                    console.warn('No templates components found');
                }
                
                // Initialize each component
                const initPromises = templatesComponents.map(name => {
                    return new Promise((resolveComponent, rejectComponent) => {
                        try {
                            const success = ComponentLoader.initialize(name);
                            if (success) {
                                console.log(`Component initialized: ${name}`);
                                resolveComponent();
                            } else {
                                console.error(`Failed to initialize component: ${name}`);
                                rejectComponent(new Error(`Failed to initialize component: ${name}`));
                            }
                        } catch (error) {
                            console.error(`Error initializing component ${name}:`, error);
                            rejectComponent(error);
                        }
                    });
                });
                
                // Wait for all components to initialize
                Promise.allSettled(initPromises).then(results => {
                    const failedComponents = results.filter(result => result.status === 'rejected');
                    
                    if (failedComponents.length > 0) {
                        console.warn(`${failedComponents.length} components failed to initialize`);
                    }
                    
                    console.log('Templates page components initialized');
                    resolve();
                });
            } catch (error) {
                console.error('Error in initTemplatesPage:', error);
                reject(error);
            }
        });
    }
    
    // Initialize database page components
    function initDatabasePage() {
        console.log('Initializing database page components...');
        
        return new Promise((resolve, reject) => {
            try {
                // Check if ComponentLoader is available
                if (!window.ComponentLoader) {
                    console.error('ComponentLoader not found');
                    reject(new Error('ComponentLoader not found'));
                    return;
                }
                
                // Get database components
                const databaseComponents = ComponentLoader.getComponentNames().filter(name => 
                    name.startsWith('database.') || name === 'database'
                );
                
                if (databaseComponents.length === 0) {
                    console.warn('No database components found');
                }
                
                // Initialize each component
                const initPromises = databaseComponents.map(name => {
                    return new Promise((resolveComponent, rejectComponent) => {
                        try {
                            const success = ComponentLoader.initialize(name);
                            if (success) {
                                console.log(`Component initialized: ${name}`);
                                resolveComponent();
                            } else {
                                console.error(`Failed to initialize component: ${name}`);
                                rejectComponent(new Error(`Failed to initialize component: ${name}`));
                            }
                        } catch (error) {
                            console.error(`Error initializing component ${name}:`, error);
                            rejectComponent(error);
                        }
                    });
                });
                
                // Wait for all components to initialize
                Promise.allSettled(initPromises).then(results => {
                    const failedComponents = results.filter(result => result.status === 'rejected');
                    
                    if (failedComponents.length > 0) {
                        console.warn(`${failedComponents.length} components failed to initialize`);
                    }
                    
                    console.log('Database page components initialized');
                    resolve();
                });
            } catch (error) {
                console.error('Error in initDatabasePage:', error);
                reject(error);
            }
        });
    }
    
    // Initialize plugins page components
    function initPluginsPage() {
        console.log('Initializing plugins page components...');
        
        return new Promise((resolve, reject) => {
            try {
                // Check if ComponentLoader is available
                if (!window.ComponentLoader) {
                    console.error('ComponentLoader not found');
                    reject(new Error('ComponentLoader not found'));
                    return;
                }
                
                // Get plugins components
                const pluginsComponents = ComponentLoader.getComponentNames().filter(name => 
                    name.startsWith('plugins.') || name === 'plugins'
                );
                
                if (pluginsComponents.length === 0) {
                    console.warn('No plugins components found');
                }
                
                // Initialize each component
                const initPromises = pluginsComponents.map(name => {
                    return new Promise((resolveComponent, rejectComponent) => {
                        try {
                            const success = ComponentLoader.initialize(name);
                            if (success) {
                                console.log(`Component initialized: ${name}`);
                                resolveComponent();
                            } else {
                                console.error(`Failed to initialize component: ${name}`);
                                rejectComponent(new Error(`Failed to initialize component: ${name}`));
                            }
                        } catch (error) {
                            console.error(`Error initializing component ${name}:`, error);
                            rejectComponent(error);
                        }
                    });
                });
                
                // Wait for all components to initialize
                Promise.allSettled(initPromises).then(results => {
                    const failedComponents = results.filter(result => result.status === 'rejected');
                    
                    if (failedComponents.length > 0) {
                        console.warn(`${failedComponents.length} components failed to initialize`);
                    }
                    
                    console.log('Plugins page components initialized');
                    resolve();
                });
            } catch (error) {
                console.error('Error in initPluginsPage:', error);
                reject(error);
            }
        });
    }
    
    // Initialize monitor page components
    function initMonitorPage() {
        console.log('Initializing monitor page components...');
        
        return new Promise((resolve, reject) => {
            try {
                // Check if ComponentLoader is available
                if (!window.ComponentLoader) {
                    console.error('ComponentLoader not found');
                    reject(new Error('ComponentLoader not found'));
                    return;
                }
                
                // Get monitor components
                const monitorComponents = ComponentLoader.getComponentNames().filter(name => 
                    name.startsWith('monitor.') || name === 'monitor'
                );
                
                if (monitorComponents.length === 0) {
                    console.warn('No monitor components found');
                }
                
                // Initialize each component
                const initPromises = monitorComponents.map(name => {
                    return new Promise((resolveComponent, rejectComponent) => {
                        try {
                            const success = ComponentLoader.initialize(name);
                            if (success) {
                                console.log(`Component initialized: ${name}`);
                                resolveComponent();
                            } else {
                                console.error(`Failed to initialize component: ${name}`);
                                rejectComponent(new Error(`Failed to initialize component: ${name}`));
                            }
                        } catch (error) {
                            console.error(`Error initializing component ${name}:`, error);
                            rejectComponent(error);
                        }
                    });
                });
                
                // Wait for all components to initialize
                Promise.allSettled(initPromises).then(results => {
                    const failedComponents = results.filter(result => result.status === 'rejected');
                    
                    if (failedComponents.length > 0) {
                        console.warn(`${failedComponents.length} components failed to initialize`);
                    }
                    
                    console.log('Monitor page components initialized');
                    resolve();
                });
            } catch (error) {
                console.error('Error in initMonitorPage:', error);
                reject(error);
            }
        });
    }
    
    // Setup global event listeners
    function setupGlobalEvents() {
        console.log('Setting up global events...');
        
        return new Promise((resolve, reject) => {
            try {
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
                    initPageComponents().catch(error => {
                        console.error('Error reinitializing page components:', error);
                    });
                });
                
                // Handle errors
                window.addEventListener('error', function(event) {
                    console.error('Global error:', event.error);
                    
                    // Show error toast
                    if (window.Utils && typeof Utils.showToast === 'function') {
                        Utils.showToast(`An error occurred: ${event.error.message}`, 'error');
                    }
                });
                
                // Handle unhandled promise rejections
                window.addEventListener('unhandledrejection', function(event) {
                    console.error('Unhandled promise rejection:', event.reason);
                    
                    // Show error toast
                    if (window.Utils && typeof Utils.showToast === 'function') {
                        Utils.showToast(`An error occurred: ${event.reason.message}`, 'error');
                    }
                });
                
                console.log('Global events set up');
                resolve();
            } catch (error) {
                console.error('Error setting up global events:', error);
                reject(error);
            }
        });
    }
    
    // Navigate to a new page
    function navigateTo(url) {
        console.log(`Navigating to: ${url}`);
        
        // Update browser history
        window.history.pushState({}, '', url);
        
        // Reinitialize components for the new page
        initPageComponents().catch(error => {
            console.error('Error reinitializing page components:', error);
            
            // Show error toast
            if (window.Utils && typeof Utils.showToast === 'function') {
                Utils.showToast(`Navigation error: ${error.message}`, 'error');
            }
        });
    }
    
    return {
        /**
         * Initialize the application
         * @returns {Promise} Promise that resolves when initialization is complete
         */
        init: function() {
            if (isInitialized) {
                console.warn('Application already initialized');
                return Promise.resolve();
            }
            
            if (initializationPromise) {
                return initializationPromise;
            }
            
            console.log('Initializing Wiseflow application...');
            
            // Create initialization promise
            initializationPromise = new Promise((resolve, reject) => {
                // Initialize shared services
                initSharedServices()
                    .then(() => {
                        // Initialize components for the current page
                        return initPageComponents();
                    })
                    .then(() => {
                        // Setup global event listeners
                        return setupGlobalEvents();
                    })
                    .then(() => {
                        isInitialized = true;
                        console.log('Wiseflow application initialized');
                        
                        // Emit application ready event
                        if (window.EventBus) {
                            EventBus.emit('app:ready');
                        }
                        
                        resolve();
                    })
                    .catch(error => {
                        console.error('Error initializing application:', error);
                        
                        // Show error toast
                        if (window.Utils && typeof Utils.showToast === 'function') {
                            Utils.showToast(`Initialization error: ${error.message}`, 'error');
                        }
                        
                        reject(error);
                    });
            });
            
            return initializationPromise;
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
         * Get the application configuration
         * @returns {object} Application configuration
         */
        getConfig: function() {
            return { ...config };
        },
        
        /**
         * Set application configuration
         * @param {object} newConfig - New configuration
         */
        setConfig: function(newConfig) {
            if (isInitialized) {
                console.warn('Cannot change configuration after initialization');
                return;
            }
            
            Object.assign(config, newConfig);
        },
        
        /**
         * Reset the application
         * @returns {Promise} Promise that resolves when reset is complete
         */
        reset: function() {
            if (!isInitialized) {
                return Promise.resolve();
            }
            
            console.log('Resetting Wiseflow application...');
            
            return new Promise((resolve, reject) => {
                try {
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
                    initializationPromise = null;
                    
                    console.log('Wiseflow application reset');
                    resolve();
                } catch (error) {
                    console.error('Error resetting application:', error);
                    reject(error);
                }
            });
        }
    };
})();

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    WiseflowApp.init().catch(error => {
        console.error('Failed to initialize application:', error);
    });
});
