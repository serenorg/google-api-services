# ABOUTME: Token storage for Google OAuth refresh tokens.
# ABOUTME: Encrypts tokens at rest and associates them with Seren users.

import base64
import secrets
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet
from databases import Database

from config import get_settings


# SQL statements for creating the tokens table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS google_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seren_user_id TEXT NOT NULL UNIQUE,
    refresh_token_encrypted TEXT NOT NULL,
    email TEXT,
    scopes TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
)
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_google_tokens_seren_user_id
ON google_tokens(seren_user_id)
"""


class TokenStorage:
    """Encrypted storage for Google OAuth refresh tokens."""

    def __init__(self, database: Database, encryption_key: str):
        self.database = database
        # Derive Fernet key from the provided key
        key_bytes = encryption_key.encode()
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'\0')
        else:
            key_bytes = key_bytes[:32]
        self.fernet = Fernet(base64.urlsafe_b64encode(key_bytes))

    def _encrypt(self, plaintext: str) -> str:
        """Encrypt a string."""
        return self.fernet.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        return self.fernet.decrypt(ciphertext.encode()).decode()

    async def store_token(
        self,
        seren_user_id: str,
        refresh_token: str,
        email: Optional[str],
        scopes: str,
    ) -> None:
        """Store or update a user's refresh token."""
        encrypted_token = self._encrypt(refresh_token)

        # Upsert: insert or update on conflict
        query = """
        INSERT INTO google_tokens (seren_user_id, refresh_token_encrypted, email, scopes, updated_at)
        VALUES (:seren_user_id, :refresh_token_encrypted, :email, :scopes, :updated_at)
        ON CONFLICT (seren_user_id)
        DO UPDATE SET
            refresh_token_encrypted = :refresh_token_encrypted,
            email = :email,
            scopes = :scopes,
            updated_at = :updated_at
        """
        await self.database.execute(
            query,
            {
                "seren_user_id": seren_user_id,
                "refresh_token_encrypted": encrypted_token,
                "email": email,
                "scopes": scopes,
                "updated_at": datetime.now(timezone.utc),
            },
        )

    async def get_refresh_token(self, seren_user_id: str) -> Optional[str]:
        """Retrieve a user's refresh token."""
        query = """
        SELECT refresh_token_encrypted
        FROM google_tokens
        WHERE seren_user_id = :seren_user_id
        """
        row = await self.database.fetch_one(query, {"seren_user_id": seren_user_id})
        if row is None:
            return None
        return self._decrypt(row["refresh_token_encrypted"])

    async def get_token_info(self, seren_user_id: str) -> Optional[dict]:
        """Get token metadata (without the actual token)."""
        query = """
        SELECT seren_user_id, email, scopes, created_at, updated_at
        FROM google_tokens
        WHERE seren_user_id = :seren_user_id
        """
        row = await self.database.fetch_one(query, {"seren_user_id": seren_user_id})
        if row is None:
            return None
        return dict(row)

    async def delete_token(self, seren_user_id: str) -> bool:
        """Delete a user's stored token."""
        query = "DELETE FROM google_tokens WHERE seren_user_id = :seren_user_id"
        result = await self.database.execute(query, {"seren_user_id": seren_user_id})
        return result > 0

    async def initialize(self) -> None:
        """Create the tokens table if it doesn't exist."""
        await self.database.execute(CREATE_TABLE_SQL)
        await self.database.execute(CREATE_INDEX_SQL)
