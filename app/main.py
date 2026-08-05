import os
import secrets
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer
from fastmcp import FastMCP
from app.mcp_server import mcp

# 1. Initialize the FastAPI Web Application
app = FastAPI(title="Qdrant Secure MCP Gateway")

# Read credentials safely out of Render's Environment panel
RENDER_CLIENT_ID = os.getenv("CLIENT_ID", "pega-mcp-client")
RENDER_CLIENT_SECRET = os.getenv("CLIENT_SECRET", "change-me-in-production")

# A simple in-memory store for active tokens
ACTIVE_TOKENS = {}

# 2. EXPOSE THE OAUTH 2.0 TOKEN ENDPOINT FOR PEGA
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
    
    access_token = secrets.token_hex(32)
    expiry = datetime.utcnow() + timedelta(hours=1)
    ACTIVE_TOKENS[access_token] = expiry
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600
    }

# 3. BEARER TOKEN AUTHENTICATION CHECK
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="oauth/token")

async def verify_mcp_access_token(token: str = Depends(oauth2_scheme)):
    """Interceptors that validate the incoming token passed from Pega."""
    if token not in ACTIVE_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid access token.")
        
    if datetime.utcnow() > ACTIVE_TOKENS[token]:
        del ACTIVE_TOKENS[token]
        raise HTTPException(status_code=401, detail="Token has expired.")
    return token

@app.get("/")
async def root():
    return {"status": "active", "auth": "OAuth 2.0 Protected"}

# 4. CORRECT MOUNT METHOD
# This securely protects your MCP endpoints using your token validation logic automatically
mcp_asgi = FastMCP.from_fastapi(app, dependencies=[Depends(verify_mcp_access_token)])
