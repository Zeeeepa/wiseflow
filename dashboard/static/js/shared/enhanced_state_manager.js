/**
 * Enhanced State Manager - Centralized state management for Wiseflow UI components
 * 
 * This module provides an enhanced state management system for sharing data
 * between different UI components in the Wiseflow application. It implements
 * a Redux-like pattern with actions, reducers, and selectors.
 */

const EnhancedStateManager = (function() {
    // Private state object
    let state = {
        // Tasks
        tasks: [],
        
        // Templates by type
        templates: {
            github: [],
            arxiv: [],
            youtube: [],
            web: []
        },
        
        // Current active task
        activeTask: null,
        
        // UI state
        ui: {
            currentView: 'dashboard',
            filters: {
                date: null,
                source: null,
                relevance: null
            },
            theme: {
                darkMode: false,
                highContrast: false,
                fontSize: 'medium',
                reducedMotion: false
            },
            notifications: []
        },
        
        // API state
        api: {
            loading: {},
            errors: {},
            cache: {}
        }
    };
    
    // Subscribers
    const subscribers = [];
    
    // Action types
    const ActionTypes = {
        // Task actions
        ADD_TASK: 'ADD_TASK',
        UPDATE_TASK: 'UPDATE_TASK',
        REMOVE_TASK: 'REMOVE_TASK',
        SET_ACTIVE_TASK: 'SET_ACTIVE_TASK',
        
        // Template actions
        ADD_TEMPLATE: 'ADD_TEMPLATE',
        UPDATE_TEMPLATE: 'UPDATE_TEMPLATE',
        REMOVE_TEMPLATE: 'REMOVE_TEMPLATE',
        
        // UI actions
        SET_CURRENT_VIEW: 'SET_CURRENT_VIEW',
        SET_FILTER: 'SET_FILTER',
        CLEAR_FILTERS: 'CLEAR_FILTERS',
        SET_THEME_SETTING: 'SET_THEME_SETTING',
        ADD_NOTIFICATION: 'ADD_NOTIFICATION',
        REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
        
        // API actions
        API_REQUEST: 'API_REQUEST',
        API_SUCCESS: 'API_SUCCESS',
        API_ERROR: 'API_ERROR',
        API_CACHE: 'API_CACHE'
    };
    
    // Reducers
    const reducers = {
        // Tasks reducer
        tasks: function(state = [], action) {
            switch (action.type) {
                case ActionTypes.ADD_TASK:
                    return [...state, action.payload];
                    
                case ActionTypes.UPDATE_TASK:
                    return state.map(task => 
                        task.id === action.payload.id 
                            ? { ...task, ...action.payload.updates } 
                            : task
                    );
                    
                case ActionTypes.REMOVE_TASK:
                    return state.filter(task => task.id !== action.payload);
                    
                default:
                    return state;
            }
        },
        
        // Templates reducer
        templates: function(state = {}, action) {
            switch (action.type) {
                case ActionTypes.ADD_TEMPLATE:
                    return {
                        ...state,
                        [action.payload.type]: [
                            ...state[action.payload.type],
                            action.payload.template
                        ]
                    };
                    
                case ActionTypes.UPDATE_TEMPLATE:
                    return {
                        ...state,
                        [action.payload.type]: state[action.payload.type].map(template => 
                            template.id === action.payload.id 
                                ? { ...template, ...action.payload.updates } 
                                : template
                        )
                    };
                    
                case ActionTypes.REMOVE_TEMPLATE:
                    return {
                        ...state,
                        [action.payload.type]: state[action.payload.type].filter(
                            template => template.id !== action.payload.id
                        )
                    };
                    
                default:
                    return state;
            }
        },
        
        // Active task reducer
        activeTask: function(state = null, action) {
            switch (action.type) {
                case ActionTypes.SET_ACTIVE_TASK:
                    return action.payload;
                    
                default:
                    return state;
            }
        },
        
        // UI reducer
        ui: function(state = {}, action) {
            switch (action.type) {
                case ActionTypes.SET_CURRENT_VIEW:
                    return {
                        ...state,
                        currentView: action.payload
                    };
                    
                case ActionTypes.SET_FILTER:
                    return {
                        ...state,
                        filters: {
                            ...state.filters,
                            [action.payload.name]: action.payload.value
                        }
                    };
                    
                case ActionTypes.CLEAR_FILTERS:
                    return {
                        ...state,
                        filters: {
                            date: null,
                            source: null,
                            relevance: null
                        }
                    };
                    
                case ActionTypes.SET_THEME_SETTING:
                    return {
                        ...state,
                        theme: {
                            ...state.theme,
                            [action.payload.name]: action.payload.value
                        }
                    };
                    
                case ActionTypes.ADD_NOTIFICATION:
                    return {
                        ...state,
                        notifications: [...state.notifications, action.payload]
                    };
                    
                case ActionTypes.REMOVE_NOTIFICATION:
                    return {
                        ...state,
                        notifications: state.notifications.filter(
                            notification => notification.id !== action.payload
                        )
                    };
                    
                default:
                    return state;
            }
        },
        
        // API reducer
        api: function(state = {}, action) {
            switch (action.type) {
                case ActionTypes.API_REQUEST:
                    return {
                        ...state,
                        loading: {
                            ...state.loading,
                            [action.payload.key]: true
                        }
                    };
                    
                case ActionTypes.API_SUCCESS:
                    return {
                        ...state,
                        loading: {
                            ...state.loading,
                            [action.payload.key]: false
                        },
                        errors: {
                            ...state.errors,
                            [action.payload.key]: null
                        }
                    };
                    
                case ActionTypes.API_ERROR:
                    return {
                        ...state,
                        loading: {
                            ...state.loading,
                            [action.payload.key]: false
                        },
                        errors: {
                            ...state.errors,
                            [action.payload.key]: action.payload.error
                        }
                    };
                    
                case ActionTypes.API_CACHE:
                    return {
                        ...state,
                        cache: {
                            ...state.cache,
                            [action.payload.key]: {
                                data: action.payload.data,
                                timestamp: Date.now()
                            }
                        }
                    };
                    
                default:
                    return state;
            }
        }
    };
    
    // Action creators
    const actions = {
        // Task actions
        addTask: function(task) {
            return {
                type: ActionTypes.ADD_TASK,
                payload: task
            };
        },
        
        updateTask: function(id, updates) {
            return {
                type: ActionTypes.UPDATE_TASK,
                payload: { id, updates }
            };
        },
        
        removeTask: function(id) {
            return {
                type: ActionTypes.REMOVE_TASK,
                payload: id
            };
        },
        
        setActiveTask: function(taskId) {
            return {
                type: ActionTypes.SET_ACTIVE_TASK,
                payload: taskId
            };
        },
        
        // Template actions
        addTemplate: function(type, template) {
            return {
                type: ActionTypes.ADD_TEMPLATE,
                payload: { type, template }
            };
        },
        
        updateTemplate: function(type, id, updates) {
            return {
                type: ActionTypes.UPDATE_TEMPLATE,
                payload: { type, id, updates }
            };
        },
        
        removeTemplate: function(type, id) {
            return {
                type: ActionTypes.REMOVE_TEMPLATE,
                payload: { type, id }
            };
        },
        
        // UI actions
        setCurrentView: function(view) {
            return {
                type: ActionTypes.SET_CURRENT_VIEW,
                payload: view
            };
        },
        
        setFilter: function(name, value) {
            return {
                type: ActionTypes.SET_FILTER,
                payload: { name, value }
            };
        },
        
        clearFilters: function() {
            return {
                type: ActionTypes.CLEAR_FILTERS
            };
        },
        
        setThemeSetting: function(name, value) {
            return {
                type: ActionTypes.SET_THEME_SETTING,
                payload: { name, value }
            };
        },
        
        addNotification: function(notification) {
            return {
                type: ActionTypes.ADD_NOTIFICATION,
                payload: {
                    id: notification.id || Date.now().toString(),
                    ...notification,
                    timestamp: Date.now()
                }
            };
        },
        
        removeNotification: function(id) {
            return {
                type: ActionTypes.REMOVE_NOTIFICATION,
                payload: id
            };
        },
        
        // API actions
        apiRequest: function(key) {
            return {
                type: ActionTypes.API_REQUEST,
                payload: { key }
            };
        },
        
        apiSuccess: function(key) {
            return {
                type: ActionTypes.API_SUCCESS,
                payload: { key }
            };
        },
        
        apiError: function(key, error) {
            return {
                type: ActionTypes.API_ERROR,
                payload: { key, error }
            };
        },
        
        apiCache: function(key, data) {
            return {
                type: ActionTypes.API_CACHE,
                payload: { key, data }
            };
        }
    };
    
    // Selectors
    const selectors = {
        // Task selectors
        getTasks: function(state) {
            return state.tasks;
        },
        
        getTaskById: function(state, id) {
            return state.tasks.find(task => task.id === id);
        },
        
        getActiveTask: function(state) {
            if (!state.activeTask) return null;
            return state.tasks.find(task => task.id === state.activeTask);
        },
        
        // Template selectors
        getTemplates: function(state, type) {
            return state.templates[type] || [];
        },
        
        getTemplateById: function(state, type, id) {
            const templates = state.templates[type] || [];
            return templates.find(template => template.id === id);
        },
        
        // UI selectors
        getCurrentView: function(state) {
            return state.ui.currentView;
        },
        
        getFilters: function(state) {
            return state.ui.filters;
        },
        
        getThemeSettings: function(state) {
            return state.ui.theme;
        },
        
        getNotifications: function(state) {
            return state.ui.notifications;
        },
        
        // API selectors
        isLoading: function(state, key) {
            return !!state.api.loading[key];
        },
        
        getError: function(state, key) {
            return state.api.errors[key];
        },
        
        getCachedData: function(state, key, maxAge = 5 * 60 * 1000) {
            const cached = state.api.cache[key];
            
            if (!cached) return null;
            
            // Check if cache is still valid
            const now = Date.now();
            if (now - cached.timestamp > maxAge) {
                return null;
            }
            
            return cached.data;
        }
    };
    
    // Combine reducers
    function combineReducers(state, action) {
        return {
            tasks: reducers.tasks(state.tasks, action),
            templates: reducers.templates(state.templates, action),
            activeTask: reducers.activeTask(state.activeTask, action),
            ui: reducers.ui(state.ui, action),
            api: reducers.api(state.api, action)
        };
    }
    
    // Middleware for logging
    function loggingMiddleware(action) {
        console.log('Dispatching action:', action);
        return action;
    }
    
    // Middleware for persistence
    function persistenceMiddleware(action) {
        // Process action
        const result = action;
        
        // Save state to localStorage after update
        setTimeout(() => {
            try {
                const currentState = EnhancedStateManager.getState();
                
                // Only persist certain parts of the state
                const persistedState = {
                    ui: {
                        theme: currentState.ui.theme
                    }
                };
                
                localStorage.setItem('wiseflow_state', JSON.stringify(persistedState));
            } catch (error) {
                console.error('Error persisting state:', error);
            }
        }, 0);
        
        return result;
    }
    
    // Apply middleware
    function applyMiddleware(action) {
        return [loggingMiddleware, persistenceMiddleware].reduce(
            (acc, middleware) => middleware(acc),
            action
        );
    }
    
    // Load persisted state
    function loadPersistedState() {
        try {
            const persistedState = localStorage.getItem('wiseflow_state');
            
            if (persistedState) {
                const parsed = JSON.parse(persistedState);
                
                // Merge with initial state
                state = {
                    ...state,
                    ui: {
                        ...state.ui,
                        theme: {
                            ...state.ui.theme,
                            ...(parsed.ui && parsed.ui.theme)
                        }
                    }
                };
            }
        } catch (error) {
            console.error('Error loading persisted state:', error);
        }
    }
    
    // Initialize
    loadPersistedState();
    
    return {
        /**
         * Get the current state
         * @returns {Object} Current state
         */
        getState: function() {
            return { ...state };
        },
        
        /**
         * Dispatch an action
         * @param {Object} action - Action to dispatch
         * @returns {Object} The action
         */
        dispatch: function(action) {
            // Apply middleware
            const processedAction = applyMiddleware(action);
            
            // Apply reducers
            const nextState = combineReducers(state, processedAction);
            
            // Update state
            state = nextState;
            
            // Notify subscribers
            subscribers.forEach(callback => {
                try {
                    callback(state);
                } catch (error) {
                    console.error('Error in subscriber:', error);
                }
            });
            
            return action;
        },
        
        /**
         * Subscribe to state changes
         * @param {Function} callback - Function to call when state changes
         * @returns {Function} Unsubscribe function
         */
        subscribe: function(callback) {
            subscribers.push(callback);
            
            // Return unsubscribe function
            return function unsubscribe() {
                const index = subscribers.indexOf(callback);
                if (index !== -1) {
                    subscribers.splice(index, 1);
                }
            };
        },
        
        /**
         * Select data from state using a selector
         * @param {Function} selector - Selector function
         * @param {...*} args - Additional arguments for the selector
         * @returns {*} Selected data
         */
        select: function(selector, ...args) {
            return selector(state, ...args);
        },
        
        // Action creators
        actions: actions,
        
        // Action types
        ActionTypes: ActionTypes,
        
        // Selectors
        selectors: selectors
    };
})();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnhancedStateManager;
} else {
    window.EnhancedStateManager = EnhancedStateManager;
}

