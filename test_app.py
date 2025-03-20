"""
Minimal FastAPI application to test routing without middleware.

This script:
1. Creates a minimal FastAPI application without middleware
2. Adds a simple test route
3. Runs the application with uvicorn

Usage:
    python test_app.py
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# Create a minimal FastAPI application without middleware
app = FastAPI()


# Add a simple test route
@app.get("/")
async def root():
    """Root route that returns a simple HTML page."""
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Test FastAPI App</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                }
                p {
                    color: #666;
                }
                ul {
                    list-style-type: none;
                    padding: 0;
                }
                li {
                    margin-bottom: 10px;
                }
                a {
                    color: #007bff;
                    text-decoration: none;
                }
                a:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Test FastAPI App</h1>
                <p>This is a minimal FastAPI application to test routing without middleware.</p>
                <h2>Available Routes:</h2>
                <ul>
                    <li><a href="/">/</a> - This page</li>
                    <li><a href="/test">/test</a> - A simple test route</li>
                    <li><a href="/test-html">/test-html</a> - A route that returns HTML</li>
                    <li><a href="/test-json">/test-json</a> - A route that returns JSON</li>
                    <li><a href="/test/nested">/test/nested</a> - A nested route</li>
                </ul>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/test")
async def test():
    """Simple test route that returns a message."""
    return {"message": "This is a test route"}


@app.get("/test-html")
async def test_html():
    """Test route that returns HTML."""
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Test HTML</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                }
                p {
                    color: #666;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Test HTML</h1>
                <p>This is a test HTML page.</p>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/test-json")
async def test_json():
    """Test route that returns JSON."""
    return JSONResponse(content={"message": "This is a test JSON response"})


@app.get("/test/nested")
async def test_nested():
    """Nested test route that returns a message."""
    return {"message": "This is a nested test route"}


# Create a router
from fastapi import APIRouter

test_router = APIRouter()


@test_router.get("/router-test")
async def router_test():
    """Test route in a router that returns a message."""
    return {"message": "This is a test route in a router"}


# Include the router with a prefix
app.include_router(test_router, prefix="/test-router")

if __name__ == "__main__":
    # Run the application with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
