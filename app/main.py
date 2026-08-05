from fastapi import FastAPI
from app.mcp_server import mcp

# Initialize the FastAPI Web Application
app = FastAPI(
    title="Qdrant MCP Gateway", 
    description="Web Gateway for Qdrant Rule Metadata"
)

@app.get("/")
async def root():
    """Simple health check endpoint to confirm the web service is alive."""
    return {
        "status": "active",
        "service": "Qdrant MCP Server Gateway"
    }

# Connect your MCP server tools to the FastAPI web layer via SSE
# Paste this correct line instead:
mcp.handle_sse(app, route="/mcp")
