import os
from enum import Enum

from dotenv import load_dotenv

load_dotenv()

# DB configuration values (from Parameter Store or .env)
db_username = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")


class DatabaseType(str, Enum):
    POSTGRESQL = "PostgreSQL"
    MYSQL = "MySQL"
    CSV = "CSV"
    MSSQL = "Microsoft SQL Server"
    ORACLE = "Oracle"
    MONGODB = "MongoDB"
    SQLITE = "SQLite"
    MARIADB = "MariaDB"
    AMAZON_RDS = "Amazon RDS"
    AMAZON_REDSHIFT = "Amazon Redshift"
    AMAZON_AURORA = "Amazon Aurora"

    @classmethod
    def get_all_values(cls) -> list[str]:
        return [member.value for member in cls]

    @classmethod
    def get_all_names(cls) -> list[str]:
        return [member.name for member in cls]

    @property
    def metabase_engine(self) -> str:
        """
        Maps the database type to Metabase engine type
        """
        mapping = {
            self.POSTGRESQL: "postgres",
            self.MYSQL: "mysql",
            self.MARIADB: "mysql",
            self.MSSQL: "sqlserver",
            self.MONGODB: "mongo",
            self.SQLITE: "sqlite",
            self.ORACLE: "oracle",
            self.AMAZON_REDSHIFT: "redshift",
            self.AMAZON_RDS: "postgres",  # Assuming PostgreSQL-compatible RDS
            self.AMAZON_AURORA: "postgres",  # Assuming PostgreSQL-compatible Aurora
            self.CSV: "csv",
        }
        return mapping.get(self, "unknown")

    def __str__(self) -> str:
        return self.value
