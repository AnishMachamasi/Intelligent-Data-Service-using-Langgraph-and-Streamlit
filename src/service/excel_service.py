import base64
import json
import logging
from io import BytesIO

import pandas as pd

from prompts.sql_converter import sql_to_excel_converter_prompt
from service.bedrock_service import BedrockAsync

# Configure logging
logger = logging.getLogger(__name__)

bedrock_async_service = BedrockAsync()


class ExcelGenerationError(Exception):
    """Custom exception for Excel generation related errors."""

    pass


class GenerateExcelService:
    """Service class for generating Excel files from SQL data."""

    @staticmethod
    async def get_excel_content(data: dict[str, str | list]) -> pd.DataFrame:
        """
        Convert structured data into a pandas DataFrame for Excel generation.

        Args:
            data: Dictionary containing table information and column data

        Returns:
            pd.DataFrame: Formatted DataFrame ready for Excel export

        Raises:
            KeyError: If required keys are missing in the input data
        """
        try:
            # Define standard table metadata fields
            metadata_fields = {
                "Table Name": data.get("Table Name"),
                "Primary Key": data.get("Primary Key"),
                "Additional Information": data.get("Additional Information"),
                "Relationships": data.get("Relationships"),
                "Constraints and Rules": data.get("Constraints and Rules"),
                "Potential Implications": data.get("Potential Implications"),
            }

            flat_data = {k: [v] for k, v in metadata_fields.items()}

            columns = data.get("Columns", [])
            foreign_keys = data.get("Foreign Keys", [])
            max_length = max(len(columns), len(foreign_keys))

            # Process columns
            for col in columns:
                for key, value in col.items():
                    column_key = f"Columns - {key}"
                    flat_data[column_key] = flat_data.get(column_key, []) + [value]

            flat_data["Comments"] = ""

            # Process foreign keys
            if isinstance(foreign_keys, list):
                for fk in foreign_keys:
                    for key, value in fk.items():
                        fk_key = f"Foreign Keys - {key}"
                        flat_data[fk_key] = flat_data.get(fk_key, []) + [value]

            # Normalize list lengths
            for key, value in flat_data.items():
                if isinstance(value, list):
                    flat_data[key] = value + [None] * (max_length - len(value))

            return pd.DataFrame(flat_data)

        except Exception as e:
            logger.error(f"Error in get_excel_content: {str(e)}")
            raise ExcelGenerationError(f"Failed to process data: {str(e)}")

    @staticmethod
    def create_excel(dfs: list[pd.DataFrame], table_names: list[str]) -> bytes:
        """
        Create Excel file and upload to S3.

        Args:
            dfs: List of DataFrames to write to Excel
            filename: Name of the output file
            table_names: List of sheet names

        Returns:
            str: Presigned URL for the uploaded file

        Raises:
            ExcelGenerationError: If Excel generation or upload fails
        """
        try:
            # Generate Excel in memory
            with BytesIO() as buffer:
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    for df, sheet_name in zip(dfs, table_names):
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                excel_content = buffer.getvalue()

            return excel_content

        except Exception as e:
            logger.error(f"Error in create_excel: {str(e)}")
            raise ExcelGenerationError(f"Failed to create Excel file: {str(e)}")

    @classmethod
    async def convert_to_excel(cls, sql_content: str) -> bytes:
        """
        Convert SQL script to Excel format.

        Args:
            file: Tuple containing filename and SQL script bytes

        Returns:
            str: Presigned URL for downloading the Excel file

        Raises:
            ExcelGenerationError: If conversion fails
        """
        try:
            dfs = []
            table_names = []

            # Process SQL scripts
            sql_scripts = [
                query.strip() for query in sql_content.split(";") if query.strip()
            ]

            system_prompt = "SQL Schema Analyzer: Convert CREATE TABLE statements to structured JSON. Extract complete schema details. Return valid JSON only."

            for script in sql_scripts:
                prompt = sql_to_excel_converter_prompt(script)
                response = await bedrock_async_service.invoke_model_async(
                    prompt=prompt, system=system_prompt
                )

                response = str(response).strip()

                # Extract and parse JSON response
                json_str = response[response.find("{") : response.rfind("}") + 1]
                json_str = json_str.replace("None", "null")
                table_data = json.loads(json_str.replace("\n", " "))

                table_names.append(table_data["Table Name"])

                df = await cls.get_excel_content(table_data)

                dfs.append(df)

            return cls.create_excel(dfs, table_names)

        except Exception as e:
            logger.error(f"Error in convert_to_excel: {str(e)}")
            raise ExcelGenerationError(f"Failed to convert SQL to Excel: {str(e)}")

    @staticmethod
    async def json_from_excel(file_content: str) -> list[dict]:
        binary_content = base64.b64decode(file_content)

        # Create BytesIO object from binary content
        excel_buffer = BytesIO(binary_content)
        excel_data = pd.read_excel(excel_buffer, sheet_name=None)

        all_data = []

        for _, df in excel_data.items():

            flat_data = df.to_dict(orient="records")

            data = {
                "Table Name": flat_data[0]["Table Name"],
                "Primary Key": flat_data[0]["Primary Key"],
                "Additional Information": flat_data[0]["Additional Information"],
                "Relationships": flat_data[0]["Relationships"],
                "Constraints and Rules": flat_data[0]["Constraints and Rules"],
                "Potential Implications": flat_data[0]["Potential Implications"],
            }

            columns = []
            for i in range(len(flat_data)):
                column = {
                    "Column Name": flat_data[i]["Columns - Column Name"],
                    "Data Type": flat_data[i]["Columns - Data Type"],
                    "Constraints": flat_data[i]["Columns - Constraints"],
                    "Description": flat_data[i]["Columns - Description"],
                    "Default Value": flat_data[i]["Columns - Default Value"],
                    "Comments": flat_data[i]["Comments"],
                }

                columns.append(column)

            data["Columns"] = columns

            fks = []

            if "Foreign Keys - Column Name" not in flat_data[0]:
                data["Foreign Keys"] = "Not Available"
            else:
                for i in range(len(flat_data)):
                    # Check if the value of "Foreign Keys - Column Name" in the first row is NaN

                    if isinstance(flat_data[i]["Foreign Keys - Column Name"], float):
                        break

                    fk = {
                        "Column Name": flat_data[i]["Foreign Keys - Column Name"],
                        "Referenced Table": flat_data[i][
                            "Foreign Keys - Referenced Table"
                        ],
                        "Referenced Column": flat_data[i][
                            "Foreign Keys - Referenced Column"
                        ],
                        "On Delete/Update Action": flat_data[i][
                            "Foreign Keys - On Delete/Update Action"
                        ],
                    }

                    fks.append(fk)

                data["Foreign Keys"] = fks

            all_data.append(data)

        return all_data
