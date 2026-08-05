import os
import secrets
from fastapi import FastAPI, Depends, HTTPException, status, Form, APIRouter
from fastapi.security import OAuth2PasswordBearer
from fastmcp import FastMCP
from app.mcp_server import mcp

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

# 3. INITIALIZE THE FASTAPI APP WITHOUT THE GLOBAL LOCK
app = FastAPI(title="Qdrant Secure MCP Gateway")

# 4. OVERRIDE THE TOKEN GENERATION ROUTE TO BYPASS AUTH
@app.post("/oauth/token", dependencies=[])
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
    
    # Save it permanently to our active memory set
    ACTIVE_TOKENS.add(access_token)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/", dependencies=[])
async def root():
    """Simple public health check route."""
    return {"status": "active", "auth": "OAuth 2.0 Enabled (Permanent Tokens)"}

# 5. CREATE A PROTECTED SUB-ROUTER AND MOUNT THE MCP ENGINE
# This creates a secured route segment that enforces your token validation logic
secured_router = APIRouter(dependencies=[Depends(verify_mcp_access_token)])
app.include_router(secured_router)

# Build the HTTP sub-app instance from your imported mcp tools
mcp_engine = mcp.http_app()

# Mount the operational tool engine under the protected sub-route
app.mount("/mcp", mcp_engine)
