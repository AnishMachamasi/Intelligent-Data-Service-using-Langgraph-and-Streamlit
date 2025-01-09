import os

import requests
from dotenv import load_dotenv
from fastapi import status
from sqlalchemy import Column

from config.logger import logger
from utils.custom_exception import CustomHTTPException

load_dotenv()

METABASE_URL = os.getenv("METABASE_URL")
METABASE_USERNAME = os.getenv("METABASE_USERNAME")
METABASE_PASSWORD = os.getenv("METABASE_PASSWORD")

CONTENT_TYPE = "application/json"
METABASE_SESSION_URL = f"{METABASE_URL}/api/session"
METABASE_DATASET_URL = f"{METABASE_URL}/api/dataset"
METABASE_DATABASE_URL = f"{METABASE_URL}/api/database"
METABASE_COLLECTION_URL = f"{METABASE_URL}/api/collection"


class MetabaseService:
    def __init__(
        self,
    ):
        pass

    @staticmethod
    def generate_session_id() -> str:
        """
        Generates session id for metabase
        """
        try:
            response = requests.post(
                METABASE_SESSION_URL,
                json={
                    "username": METABASE_USERNAME,
                    "password": METABASE_PASSWORD,
                },
            )
            response.raise_for_status()

            session_id = response.json()["id"]
            logger.info("Metabase session created")
            return session_id

        except requests.exceptions.HTTPError:
            logger.exception("Metabase session creation error")
            raise CustomHTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Metabase session creation error",
            )

        except Exception:
            logger.exception("Metabase error")
            raise CustomHTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Metabase session creation error",
            )

    @staticmethod
    def create_metabase_collection(
        collectionName: str,
        headers: dict[str, str],
        parentCollectionId: Column[int] | int | None = None,
    ) -> None:
        """
        Creates metabase collection
        """
        payload_collection = {
            "parent_id": parentCollectionId,
            "color": "#509EE3",
            "name": collectionName,
        }

        try:
            response = requests.post(
                METABASE_COLLECTION_URL,
                headers=headers,
                json=payload_collection,
            )
            response.raise_for_status()

            collectionId = response.json()["id"]
            logger.info(f"Created collection in Metabase with id {collectionId}")

            return collectionId

        except Exception as err:
            logger.exception(f"Error creating collection: {str(err)}")
            raise CustomHTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(err))

    @classmethod
    def create_database(cls, database_info, headers, client_name) -> None:
        """
        Creates metabase dataset
        """

        engine_type = database_info.database_config.db_type.metabase_engine
        
        if engine_type == "unknown":
            raise CustomHTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Unsupported database type for Metabase: {database_info.database_config.db_type}"
            )

        try:
            db_details = {}
            if database_info.database_config.db_type == "CSV":
                # db_details = {
                #         "access_key": db_details.access_key,
                #         "catalog": db_details.catalog,
                #         "region": db_details.region,
                #         "s3_staging_dir": db_details.s3_staging_dir,
                #         "secret_key": db_details.secret_key,
                #         "workgroup": db_details.workgroup,
                #     }
                pass
            else:
                db_details = {
                    "host": str(database_info.database_config.db_host),
                    "dbname": str(database_info.database_config.db_name),
                    "port": str(database_info.database_config.db_port),
                    "user": str(database_info.database_config.db_username),
                    "password": str(database_info.database_config.db_password),
                    "ssl": False,
                    "tunnel-enabled": False,
                    "advanced-options": False,
                }

            payload = {
                "engine": str(engine_type),
                "details": db_details,
                "name": f"{client_name} - {database_info.database_config.db_name}",
            }

            print(f"PAYLOAD: {payload}")

            response = requests.post(
                METABASE_DATABASE_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            metabaseDbId = response.json()["id"]

            logger.info(
                f"Metabase Database {database_info.database_config.db_name} created with id {metabaseDbId}"
            )

            return metabaseDbId

        except Exception as err:
            logger.exception(f"Error creating dataset: {str(err)}")
            raise CustomHTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(err))
