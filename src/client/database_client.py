from typing import Optional

import aiohttp
import requests
import streamlit as st


class DatabaseClient:
    """Client for interacting with Database."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float | None = None,
    ):
        self.base_url = base_url
        self.timeout = 30.0

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> dict | None:
        """
        Make an HTTP request to the API.
        """
        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        st.error(f"API request failed: {await response.text()}")
                        return None
        except Exception as e:
            st.error(f"Error making API request: {str(e)}")
            return None

    async def store_client(self, name: str, email: str) -> dict | None:
        """
        Store client information in the database.

        Args:
            name: Client's name
            email: Client's email

        Returns:
            dict containing client information if successful, None otherwise
        """
        return await self._make_request(
            "POST", "/store_client", json={"client_name": name, "client_email": email}
        )

    async def add_database(self, client_email: str, database_info: dict) -> dict | None:
        """
        Add a new database for a client.

        Args:
            client_id: ID of the client
            database_info: Dictionary containing database information
                (db_name, db_endpoint, db_username, db_password)

        Returns:
            dict containing database information if successful, None otherwise
        """
        return await self._make_request(
            "POST",
            "/add_databases",
            json={"client_email": client_email, "database_config": database_info},
        )

    async def get_databases(self, email: str) -> dict | None:
        """
        Get all databases for a client.

        Args:
            client_id: ID of the client

        Returns:
            dict containing list of databases if successful, None otherwise
        """
        return await self._make_request(
            "GET", "/get_databases", json={"client_email": email}
        )
