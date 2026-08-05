import os
import secrets
from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer

# IMPORT YOUR SERVER INSTANCE FROM YOUR MCP_SERVER.PY FILE
from app.mcp_server import mcp

# 1. SETUP CREDENTIALS AND PERMANENT TOKEN CONTAINER
RENDER_CLIENT_ID = os.getenv("CLIENT_ID", "pega-mcp-client")
RENDER_CLIENT_SECRET = os.getenv("CLIENT_SECRET", "change-me-in-production")

ACTIVE_TOKENS = set()

# 2. BEARER TOKEN AUTHENTICATION CHECK
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="oauth/token")

async def verify_mcp_access_token(token: str = Depends(oauth2_scheme)):
    if token not in ACTIVE_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid access token.")
    return token

# 3. INITIALIZE FASTAPI APP (No global master lock)
app = FastAPI(title="Qdrant Secure MCP Gateway")

# 4. OAUTH 2.0 TOKEN GENERATION ROUTE
@app.post("/oauth/token")
async def generate_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="Unsupported grant_type.")
        
    if client_id != RENDER_CLIENT_ID or client_secret != RENDER_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Client ID or Client Secret.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = secrets.token_hex(32)
    ACTIVE_TOKENS.add(access_token)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# 5. MOUNT THE IMPORTED FASTMCP ROUTER NATIVELY AS AN ASGI APP
# FastMCP instances natively behave as ASGI sub-apps when passed to mount()
app.mount("/mcp", mcp, dependencies=[Depends(verify_mcp_access_token)])

# 6. PUBLIC HEALTH CHECK ROUTE
@app.get("/")
async def root():
    return {"status": "active", "auth": "OAuth 2.0 Enabled", "mcp_endpoint": "/mcp"}
