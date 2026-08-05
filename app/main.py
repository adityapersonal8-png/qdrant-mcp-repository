import os
import secrets
from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer
from fastmcp import FastMCP

# 1. SETUP CREDENTIALS AND PERMANENT TOKEN CONTAINER
RENDER_CLIENT_ID = os.getenv("CLIENT_ID", "pega-mcp-client")
RENDER_CLIENT_SECRET = os.getenv("CLIENT_SECRET", "change-me-in-production")

# A set tracks active valid tokens permanently in-memory
ACTIVE_TOKENS = set()

# 2. BEARER TOKEN AUTHENTICATION CHECK (NO EXPIRY CHECK)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="oauth/token")

async def verify_mcp_access_token(token: str = Depends(oauth2_scheme)):
    """Validates that the token exists in our permanent security block."""
    if token not in ACTIVE_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid access token.")
    return token

# 3. INITIALIZE THE FASTAPI APP (NO Global master lock here)
app = FastAPI(title="Qdrant Secure MCP Gateway")

# 4. INITIALIZE THE FASTMCP SERVER INSTANCE
mcp = FastMCP("Qdrant Secure MCP Gateway")

# 5. OAUTH 2.0 TOKEN GENERATION ROUTE (Public)
@app.post("/oauth/token")
async def generate_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    """Exposes the OAuth 2.0 Client Credentials token generator endpoint for Pega."""
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="Unsupported grant_type. Use 'client_credentials'.")
        
    if client_id != RENDER_CLIENT_ID or client_secret != RENDER_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Client ID or Client Secret.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate a unique string token
    access_token = secrets.token_hex(32)
    ACTIVE_TOKENS.add(access_token)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# 6. SECURED OPERATIONAL ENDPOINTS FOR PEGA
# This mounts the FastMCP server onto your FastAPI application under a dedicated path,
# protecting all underlying Qdrant tools using your security dependency barrier.
app.mount("/mcp", mcp.as_asgi(), dependencies=[Depends(verify_mcp_access_token)])

# 7. PUBLIC HEALTH CHECK ROUTE
@app.get("/")
async def root():
    """Simple public health check route."""
    return {"status": "active", "auth": "OAuth 2.0 Enabled", "mcp_endpoint": "/mcp"}
