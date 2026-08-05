import os
import secrets
from fastapi import FastAPI, Depends, HTTPException, status, Form, APIRouter
from fastapi.security import OAuth2PasswordBearer
from fastmcp import FastMCP
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

# 3. BUILD THE ENGINE AND INJECT IT TO THE APP LIFESPAN CONSTUCTOR
# Passing path="/" removes the extra /mcp folder entirely
mcp_engine = mcp.http_app(path="/")

app = FastAPI(
    title="Qdrant Secure MCP Gateway",
    lifespan=mcp_engine.lifespan
)

# 4. OAUTH 2.0 TOKEN GENERATION ROUTE
@app.post("/oauth/token", dependencies=[])
async def generate_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="Unsupported grant_type. Use 'client_credentials'.")
        
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

# 5. SECURE ROUTER BARRIER
# This locks your underlying tools while leaving the token endpoint public
secured_router = APIRouter(dependencies=[Depends(verify_mcp_access_token)])
app.include_router(secured_router)

# 6. MOUNT THE ENGINE DIRECTLY TO THE ROOT
# No /mcp needed!
app.mount("/", mcp_engine)
