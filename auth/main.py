# ABOUTME: FastAPI application for Google OAuth and token exchange.
# ABOUTME: Handles user authorization and Seren Gateway token exchange.

import logging
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urlencode

from databases import Database
from fastapi import FastAPI, HTTPException, Query, Header, Request
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx

from config import get_settings
from oauth import GoogleOAuth
from storage import TokenStorage

# Configure logging
settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Database connection
database = Database(settings.database_url)

# Token storage
token_storage = TokenStorage(database, settings.token_encryption_key)

# OAuth handler
oauth = GoogleOAuth()

# In-memory state storage (for CSRF protection)
# In production, use Redis or database
pending_states: dict[str, str] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Auth service starting...")
    await database.connect()
    await token_storage.initialize()
    yield
    await database.disconnect()
    logger.info("Auth service shutting down...")


app = FastAPI(
    title="Google Auth Service",
    description="OAuth and token exchange for Gmail and Calendar publishers",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "google-auth"}


# --- OAuth Authorization Flow ---


@app.get("/auth/google")
async def auth_google(
    seren_token: Optional[str] = Query(None, description="Seren API key for user identification"),
):
    """
    Initiate Google OAuth flow.

    The seren_token parameter identifies which Seren user is authorizing.
    After authorization, the refresh token will be stored for this user.
    """
    if not seren_token:
        raise HTTPException(
            status_code=400,
            detail="Missing seren_token parameter. Include your Seren API key to link authorization.",
        )

    # Generate state with embedded seren_token
    state = oauth.generate_state()
    pending_states[state] = seren_token

    # Redirect to Google
    auth_url = oauth.get_authorization_url(state)
    return RedirectResponse(url=auth_url)


@app.get("/auth/google/callback")
async def auth_google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """
    Handle Google OAuth callback.

    Exchanges the authorization code for tokens and stores the refresh token.
    """
    # Handle errors from Google
    if error:
        logger.error(f"OAuth error from Google: {error}")
        return HTMLResponse(
            content=f"""
            <html>
            <body>
                <h1>Authorization Failed</h1>
                <p>Error: {error}</p>
                <p>Please try again.</p>
            </body>
            </html>
            """,
            status_code=400,
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    # Validate state (CSRF protection)
    seren_token = pending_states.pop(state, None)
    if not seren_token:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    try:
        # Exchange code for tokens
        tokens = await oauth.exchange_code_for_tokens(code)
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        if not refresh_token:
            logger.error("No refresh token received from Google")
            return HTMLResponse(
                content="""
                <html>
                <body>
                    <h1>Authorization Failed</h1>
                    <p>No refresh token received. Please try again and ensure you grant all permissions.</p>
                </body>
                </html>
                """,
                status_code=400,
            )

        # Get user info for email
        user_info = await oauth.get_user_info(access_token)
        email = user_info.get("email")

        # Extract user ID from Seren token
        # The seren_token format is: seren_{key_id}_{secret}
        # We use the full token as the user identifier for simplicity
        seren_user_id = seren_token

        # Store the refresh token
        await token_storage.store_token(
            seren_user_id=seren_user_id,
            refresh_token=refresh_token,
            email=email,
            scopes=settings.google_scopes,
        )

        logger.info(f"Stored refresh token for user: {email}")

        return HTMLResponse(
            content=f"""
            <html>
            <body>
                <h1>Authorization Successful</h1>
                <p>Your Google account ({email}) has been connected.</p>
                <p>You can now use Gmail and Calendar through Seren.</p>
                <p>You may close this window.</p>
            </body>
            </html>
            """
        )

    except httpx.HTTPStatusError as e:
        logger.error(f"Token exchange failed: {e.response.text}")
        return HTMLResponse(
            content=f"""
            <html>
            <body>
                <h1>Authorization Failed</h1>
                <p>Failed to exchange authorization code: {e.response.status_code}</p>
                <p>Please try again.</p>
            </body>
            </html>
            """,
            status_code=400,
        )


# --- Token Exchange Endpoint (called by Seren Gateway) ---


@app.post("/token/exchange")
async def token_exchange(
    authorization: Optional[str] = Header(None),
    x_agent_wallet: Optional[str] = Header(None, alias="X-Agent-Wallet"),
):
    """
    Exchange Seren API key for Google access token.

    This endpoint is called by the Seren Gateway when an agent makes a request
    to the Gmail or Calendar publisher. The Gateway passes the agent's Seren
    API key, and we return a fresh Google access token.

    Headers:
        Authorization: Bearer {seren_api_key}
        X-Agent-Wallet: {agent_wallet_address} (optional)

    Returns:
        {"access_token": "...", "expires_in": 3500}
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # Extract the Seren API key from Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
        )

    seren_token = parts[1]

    # Use the seren_token as the user identifier
    # (same as what we stored during OAuth authorization)
    seren_user_id = seren_token

    # Look up the stored refresh token
    refresh_token = await token_storage.get_refresh_token(seren_user_id)

    if not refresh_token:
        # User hasn't authorized yet - return helpful error
        auth_url = f"{settings.google_redirect_uri.rsplit('/callback', 1)[0]}?{urlencode({'seren_token': seren_token})}"
        raise HTTPException(
            status_code=401,
            detail={
                "error": "not_authorized",
                "message": "Google account not connected. Please authorize first.",
                "authorization_url": auth_url,
            },
        )

    try:
        # Get a fresh access token
        tokens = await oauth.refresh_access_token(refresh_token)
        access_token = tokens.get("access_token")
        expires_in = tokens.get("expires_in", settings.access_token_lifetime)

        return {
            "access_token": access_token,
            "expires_in": expires_in,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Token refresh failed: {e.response.text}")

        # If refresh fails, the token may be revoked
        if e.response.status_code == 400:
            # Delete the invalid token
            await token_storage.delete_token(seren_user_id)

            auth_url = f"{settings.google_redirect_uri.rsplit('/callback', 1)[0]}?{urlencode({'seren_token': seren_token})}"
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "token_revoked",
                    "message": "Google authorization was revoked. Please re-authorize.",
                    "authorization_url": auth_url,
                },
            )

        raise HTTPException(
            status_code=502,
            detail=f"Failed to refresh Google access token: {e.response.status_code}",
        )


# --- Token Management ---


@app.get("/token/status")
async def token_status(
    authorization: Optional[str] = Header(None),
):
    """Check if a user has connected their Google account."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    seren_token = parts[1]
    seren_user_id = seren_token

    token_info = await token_storage.get_token_info(seren_user_id)

    if not token_info:
        return {
            "connected": False,
            "message": "Google account not connected",
        }

    return {
        "connected": True,
        "email": token_info.get("email"),
        "scopes": token_info.get("scopes"),
        "connected_at": token_info.get("created_at"),
    }


@app.delete("/token/revoke")
async def token_revoke(
    authorization: Optional[str] = Header(None),
):
    """Disconnect Google account (delete stored refresh token)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    seren_token = parts[1]
    seren_user_id = seren_token

    deleted = await token_storage.delete_token(seren_user_id)

    if deleted:
        return {"status": "disconnected", "message": "Google account disconnected"}
    else:
        return {"status": "not_found", "message": "No Google account was connected"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
