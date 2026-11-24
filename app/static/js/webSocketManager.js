import { AdventureStateManager } from './adventureStateManager.js';

const LOADER_STEP_CRAFTING_STORY = 2;

export class WebSocketManager {
    constructor(authManager) {
        this.authManager = authManager;
        this.stateManager = new AdventureStateManager();
        this.connection = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.baseDelayMs = 1000;
        this.maxDelayMs = 30000;
        this.adventureId = null;
        this.adventureIdToResume = null;
    }

    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

        let storyCategory = 'unknown';
        let lessonTopic = 'unknown';

        if (this.adventureIdToResume) {
            storyCategory = sessionStorage.getItem('resume_story_category') || 'unknown';
            lessonTopic = sessionStorage.getItem('resume_lesson_topic') || 'unknown';
        } else {
            const storyCategoryEl = document.getElementById('storyCategory');
            const lessonTopicEl = document.getElementById('lessonTopic');
            storyCategory = storyCategoryEl ? storyCategoryEl.value : 'unknown';
            lessonTopic = lessonTopicEl ? lessonTopicEl.value : 'unknown';
        }

        const clientUuid = this.stateManager.getClientUuid();

        const encodedStoryCategory = encodeURIComponent(storyCategory);
        const encodedLessonTopic = encodeURIComponent(lessonTopic);
        const encodedClientUuid = encodeURIComponent(clientUuid);

        let url = `${protocol}//${window.location.host}/ws/story/${encodedStoryCategory}/${encodedLessonTopic}?client_uuid=${encodedClientUuid}`;

        if (this.authManager.accessToken) {
            url += `&token=${encodeURIComponent(this.authManager.accessToken)}`;
        }

        if (this.adventureIdToResume) {
            url += `&resume_adventure_id=${encodeURIComponent(this.adventureIdToResume)}`;
        }

        // First-touch UTM/referrer tags (set by attribution.js) for new-adventure telemetry
        if (typeof window.getAttributionQuery === 'function') {
            url += window.getAttributionQuery();
        }

        return url;
    }

    setAdventureId(id) {
        this.adventureId = id;
    }

    getAdventureId() {
        return this.adventureId;
    }

    async handleDisconnect() {
        if (this.connection?.readyState === WebSocket.CLOSED) {
            await this.reconnect();
        }
    }

    calculateBackoff() {
        return Math.min(
            this.baseDelayMs * Math.pow(2, this.reconnectAttempts),
            this.maxDelayMs
        );
    }

    async reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            const { appendStoryText } = await import('./uiManager.js');
            appendStoryText('\n\nUnable to reconnect after multiple attempts. Please refresh the page.');
            return;
        }

        const savedState = this.stateManager.loadState();
        if (!savedState && !this.adventureIdToResume) {
            const { appendStoryText } = await import('./uiManager.js');
            appendStoryText('\n\nUnable to recover story state. Please refresh the page.');
            return;
        }

        const delay = this.calculateBackoff();
        await new Promise(resolve => setTimeout(resolve, delay));

        const websocketUrl = this.getWebSocketUrl();
        try {
            this.connection = new WebSocket(websocketUrl);
            if (window.appState) {
                window.appState.storyWebSocket = this.connection;
            }
            this.setupConnectionHandlers();
            this.reconnectAttempts++;
        } catch (e) {
            console.error("Error creating WebSocket during reconnect:", e);
            const { hideLoader } = await import('./uiManager.js');
            hideLoader();
        }
    }

    setupConnectionHandlers() {
        const savedState = this.stateManager.loadState();
        const connection = this.connection;
        const uiModulePromise = import('./uiManager.js');
        const stateModulePromise = import('./stateManager.js');

        connection.onopen = async () => {
            this.reconnectAttempts = 0;

            try {
                const uiModule = await uiModulePromise;
                const { manageState } = await stateModulePromise;
                const loaderFns = window.loaderFunctions || {};
                const setLoaderStep = uiModule.setLoaderStep || loaderFns.setLoaderStep || (() => {});

                setLoaderStep(LOADER_STEP_CRAFTING_STORY);

                if (this.adventureIdToResume) {
                    connection.send(JSON.stringify({
                        choice: 'resume_specific_adventure',
                        adventure_id_to_resume: this.adventureIdToResume
                    }));
                } else if (savedState) {
                    connection.send(JSON.stringify({
                        state: savedState,
                        choice: 'start'
                    }));
                } else {
                    const storyCategoryEl = document.getElementById('storyCategory');
                    const lessonTopicEl = document.getElementById('lessonTopic');
                    const initialState = manageState('initialize', {
                        storyCategory: storyCategoryEl ? storyCategoryEl.value : (sessionStorage.getItem('resume_story_category') || ''),
                        lessonTopic: lessonTopicEl ? lessonTopicEl.value : (sessionStorage.getItem('resume_lesson_topic') || '')
                    });
                    connection.send(JSON.stringify({
                        state: initialState,
                        choice: 'start'
                    }));
                }
            } catch (error) {
                console.error('WebSocket open handler failed:', error);
                const uiModule = await uiModulePromise.catch(() => ({}));
                const loaderFns = window.loaderFunctions || {};
                const showLoaderError = uiModule.showLoaderError || loaderFns.showLoaderError || (() => {});
                showLoaderError('Unable to start the adventure. Please try again.');
            }
        };

        connection.onclose = async (event) => {
            if (!event.wasClean) {
                console.error('WebSocket connection died unexpectedly. Code:', event.code, 'Reason:', event.reason);
                this.handleDisconnect();
            } else {
                const uiModule = await uiModulePromise.catch(() => ({}));
                const hideLoader = uiModule.hideLoader || (() => {});
                hideLoader();
            }
        };

        connection.onerror = async (error) => {
            console.error('WebSocket Error: ', error);
            const uiModule = await uiModulePromise.catch(() => ({}));
            const loaderFns = window.loaderFunctions || {};
            const showLoaderError = uiModule.showLoaderError || loaderFns.showLoaderError || (() => {});
            showLoaderError('Unable to connect. Please check your internet connection.');
        };

        connection.onmessage = async (event) => {
            const uiModule = await uiModulePromise;
            uiModule.handleMessage(event);
        };
    }

    sendMessage(message) {
        if (this.connection && this.connection.readyState === WebSocket.OPEN) {
            this.connection.send(JSON.stringify(message));
        } else {
            console.error('WebSocket is not open. Message not sent:', message);
        }
    }
}
