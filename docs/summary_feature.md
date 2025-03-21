# Summary Chapter Feature Documentation

## Overview

The Summary Chapter is a React application that provides a visual recap of a completed Learning Odyssey adventure. It displays:

- Chapter summaries in a timeline format
- Educational questions encountered during the adventure
- Statistics about the adventure (chapters completed, questions answered, etc.)

## Route Configuration

The Summary Chapter is integrated into the main FastAPI application with the following route configuration:

### Main Routes

- `/adventure/summary`: Serves the React app for the Summary Chapter
- `/adventure/api/adventure-summary`: API endpoint that provides the summary data

### Static Assets

- `/adventure/assets/*`: Serves static assets (CSS, JS, images) for the React app

## Implementation Details

### FastAPI Integration

The Summary Chapter is integrated into the main FastAPI application using the following components:

1. **Summary Router** (`app/routers/summary_router.py`):
   - Defines routes for serving the React app and API endpoints
   - Included in the main application with the `/adventure` prefix
   - Handles fallback to a test HTML file if the React app is not built

2. **Static Asset Mounting** (`app/main.py`):
   - Mounts static assets from `app/static/summary-chapter/assets` at `/adventure/assets`
   - Ensures CSS, JS, and other assets are properly served

### React App

The React app is built using Vite and is configured with the following:

1. **Base URL** (`vite.config.ts`):
   - Sets the base URL to `/adventure/` to match the FastAPI router prefix
   - Ensures all relative paths in the React app are correctly resolved

2. **React Router** (`src/App.tsx`):
   - Configures the router with the base URL from Vite's configuration
   - Defines routes for the summary page and other pages

3. **API Integration** (`src/pages/AdventureSummary.tsx`):
   - Fetches data from the `/adventure/api/adventure-summary` endpoint
   - Displays the data in a visually appealing format

## Build Process

The React app is built using the `tools/build_summary_app.py` script, which:

1. Builds the React app from the source code
2. Copies the build output to `app/static/summary-chapter/`
3. Ensures the app is correctly configured for production

## Testing

The routes can be tested using the `tools/test_summary_routes.py` script, which:

1. Checks if the main routes are accessible
2. Verifies that static assets are being served correctly
3. Tests API endpoints with expected responses

## Maintenance

When maintaining the Summary Chapter feature, keep the following in mind:

1. **React App Updates**:
   - Make changes to the React app in the source code
   - Rebuild the app using the build script
   - Test the changes to ensure they work correctly

2. **Route Configuration Updates**:
   - Update the summary router if new routes are needed
   - Update the static asset mounting if new asset types are added
   - Test all routes after making changes

3. **API Updates**:
   - Update the API endpoint in the summary router
   - Update the corresponding fetch logic in the React app
   - Test the API with various data scenarios

## Troubleshooting

If you encounter issues with the Summary Chapter feature, check the following:

1. **404 Errors for Static Assets**:
   - Ensure the assets are correctly built and placed in `app/static/summary-chapter/assets`
   - Check the static asset mounting in `app/main.py`

2. **React App Not Loading**:
   - Verify that the React app is built and placed in `app/static/summary-chapter/`
   - Check the summary router in `app/routers/summary_router.py`

3. **API Errors**:
   - Check the API endpoint in the summary router
   - Verify that the adventure state is correctly formatted for the React app
