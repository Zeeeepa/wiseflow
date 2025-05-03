/**
 * State Manager for WiseFlow UI Components
 * 
 * This module provides centralized state management for the application.
 * It implements a simplified Redux-like pattern with:
 * - A single state store
 * - Actions to request state changes
 * - Reducers to handle state changes
 * - Subscribers to be notified of state changes
 */

// Create a singleton state manager
const StateManager = (function() {
    // Initial state
    const initialState = {
        tasks: [],
        templates: [],
        interconnections: [],
        activeTask: null,
        activeTemplate: null,
        ui: {
            currentTab: 'listings',
            isLoading: false,
            errors: {},
            notifications: []
        },
        filters: {
            taskType: 'all',
            status: 'all',
            searchText: ''
        }
    };
    
    // Current state
    let state = {...initialState};
    
    // Subscribers
    const subscribers = [];
    
    // Get the current state (immutable)
    function getState() {
        return {...state};
    }
    
    // Subscribe to state changes
    function subscribe(callback) {
        subscribers.push(callback);
        
        // Return unsubscribe function
        return function unsubscribe() {
            const index = subscribers.indexOf(callback);
            if (index !== -1) {
                subscribers.splice(index, 1);
            }
        };
    }
    
    // Notify all subscribers of state change
    function notifySubscribers() {
        subscribers.forEach(callback => {
            try {
                callback(state);
            } catch (error) {
                console.error('Error in state subscriber:', error);
            }
        });
    }
    
    // Dispatch an action to change state
    function dispatch(action) {
        // Apply the action to the state
        state = reducer(state, action);
        
        // Notify subscribers
        notifySubscribers();
        
        // If the action should be persisted, save to localStorage
        if (action.persist) {
            persistState();
        }
        
        // If the action should trigger an event, publish it
        if (action.event) {
            window.EventBus.publish(action.event, action.payload || {});
        }
        
        return state;
    }
    
    // Main reducer function
    function reducer(state, action) {
        switch (action.type) {
            case 'SET_TASKS':
                return {
                    ...state,
                    tasks: action.payload
                };
                
            case 'ADD_TASK':
                return {
                    ...state,
                    tasks: [...state.tasks, action.payload]
                };
                
            case 'UPDATE_TASK':
                return {
                    ...state,
                    tasks: state.tasks.map(task => 
                        task.task_id === action.payload.task_id ? {...task, ...action.payload} : task
                    )
                };
                
            case 'DELETE_TASK':
                return {
                    ...state,
                    tasks: state.tasks.filter(task => task.task_id !== action.payload.task_id)
                };
                
            case 'SET_ACTIVE_TASK':
                return {
                    ...state,
                    activeTask: action.payload
                };
                
            case 'SET_TEMPLATES':
                return {
                    ...state,
                    templates: action.payload
                };
                
            case 'ADD_TEMPLATE':
                return {
                    ...state,
                    templates: [...state.templates, action.payload]
                };
                
            case 'UPDATE_TEMPLATE':
                return {
                    ...state,
                    templates: state.templates.map(template => 
                        template.template_id === action.payload.template_id ? {...template, ...action.payload} : template
                    )
                };
                
            case 'DELETE_TEMPLATE':
                return {
                    ...state,
                    templates: state.templates.filter(template => template.template_id !== action.payload.template_id)
                };
                
            case 'SET_ACTIVE_TEMPLATE':
                return {
                    ...state,
                    activeTemplate: action.payload
                };
                
            case 'SET_INTERCONNECTIONS':
                return {
                    ...state,
                    interconnections: action.payload
                };
                
            case 'ADD_INTERCONNECTION':
                return {
                    ...state,
                    interconnections: [...state.interconnections, action.payload]
                };
                
            case 'DELETE_INTERCONNECTION':
                return {
                    ...state,
                    interconnections: state.interconnections.filter(
                        ic => ic.interconnection_id !== action.payload.interconnection_id
                    )
                };
                
            case 'SET_UI_STATE':
                return {
                    ...state,
                    ui: {
                        ...state.ui,
                        ...action.payload
                    }
                };
                
            case 'SET_CURRENT_TAB':
                return {
                    ...state,
                    ui: {
                        ...state.ui,
                        currentTab: action.payload
                    }
                };
                
            case 'SET_LOADING':
                return {
                    ...state,
                    ui: {
                        ...state.ui,
                        isLoading: action.payload
                    }
                };
                
            case 'ADD_ERROR':
                return {
                    ...state,
                    ui: {
                        ...state.ui,
                        errors: {
                            ...state.ui.errors,
                            [action.payload.key]: action.payload.message
                        }
                    }
                };
                
            case 'CLEAR_ERROR':
                const newErrors = {...state.ui.errors};
                delete newErrors[action.payload.key];
                return {
                    ...state,
                    ui: {
                        ...state.ui,
                        errors: newErrors
                    }
                };
                
            case 'ADD_NOTIFICATION':
                return {
                    ...state,
                    ui: {
                        ...state.ui,
                        notifications: [...state.ui.notifications, action.payload]
                    }
                };
                
            case 'REMOVE_NOTIFICATION':
                return {
                    ...state,
                    ui: {
                        ...state.ui,
                        notifications: state.ui.notifications.filter(n => n.id !== action.payload.id)
                    }
                };
                
            case 'SET_FILTERS':
                return {
                    ...state,
                    filters: {
                        ...state.filters,
                        ...action.payload
                    }
                };
                
            case 'RESET_STATE':
                return {...initialState};
                
            default:
                return state;
        }
    }
    
    // Persist state to localStorage
    function persistState() {
        try {
            const stateToSave = {
                filters: state.filters,
                ui: {
                    currentTab: state.ui.currentTab
                }
            };
            localStorage.setItem('wiseflow_state', JSON.stringify(stateToSave));
        } catch (error) {
            console.error('Error persisting state:', error);
        }
    }
    
    // Load persisted state from localStorage
    function loadPersistedState() {
        try {
            const savedState = localStorage.getItem('wiseflow_state');
            if (savedState) {
                const parsedState = JSON.parse(savedState);
                state = {
                    ...state,
                    filters: parsedState.filters || state.filters,
                    ui: {
                        ...state.ui,
                        currentTab: parsedState.ui?.currentTab || state.ui.currentTab
                    }
                };
                notifySubscribers();
            }
        } catch (error) {
            console.error('Error loading persisted state:', error);
        }
    }
    
    // Initialize state
    function init() {
        loadPersistedState();
    }
    
    // Public API
    return {
        getState,
        subscribe,
        dispatch,
        init
    };
})();

// Initialize the state manager
document.addEventListener('DOMContentLoaded', function() {
    StateManager.init();
});

// Make StateManager available globally
window.StateManager = StateManager;

