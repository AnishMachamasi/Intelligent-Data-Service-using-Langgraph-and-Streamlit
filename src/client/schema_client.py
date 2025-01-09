import aiohttp


# database_client.py
class SchemaClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def process_sql_file(
        self,
        client_name: str,
        client_email: str,
        database_name: str,
        files: list[dict[str, str]],
    ):
        """Send SQL file to backend for processing"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/process_sql",
                    json={
                        "client_name": client_name,
                        "client_email": client_email,
                        "database_name": database_name,
                        "files": files,
                    },
                ) as response:
                    return await response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def process_excel_file(
        self,
        client_name: str,
        client_email: str,
        database_name: str,
        files: list[dict[str, str]],
    ):
        """Send Excel file to backend for processing"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/process_excel",
                    json={
                        "client_name": client_name,
                        "client_email": client_email,
                        "database_name": database_name,
                        "files": files,
                    },
                ) as response:
                    return await response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
