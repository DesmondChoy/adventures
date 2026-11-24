/**
 * State Manager
 * Handles adventure state operations and management
 */

import { AdventureStateManager } from './adventureStateManager.js';

// Create a global state manager instance
const stateManager = new AdventureStateManager();

export function manageState(action, data) {
    switch (action) {
        case 'initialize':
            // Initialize state with selected category and lesson
            const initialState = {
                storyCategory: data.storyCategory,
                lessonTopic: data.lessonTopic,
                story_length: window.appConfig?.defaultStoryLength || 10, // Use configurable story length
                current_chapter_id: 'start',
                chapters: [],
                selected_narrative_elements: {},
                selected_sensory_details: {},
                selected_theme: '',
                selected_moral_teaching: '',
                selected_plot_twist: '',
                metadata: {},
                current_storytelling_phase: 'Exposition'
            };
            stateManager.saveState(initialState);
            return initialState;

        case 'update':
            const existingState = stateManager.loadState() || {};
            const updatedState = { ...existingState, ...data };
            stateManager.saveState(updatedState);
            return updatedState;

        case 'reset':
            stateManager.clearState();
            return null;

        default:
            console.error('Unknown state action:', action);
            return null;
    }
}

export { stateManager };
