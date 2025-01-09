import json
import os

import pandas as pd
import requests
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sql_metadata import Parser
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.data_analytics_agent.models import (
    GenerateSQLCreatorState,
    SQLCreator,
    SQLQuery,
    VisualizationRecommender,
    VisualizationStatus,
)
from agents.data_analytics_agent.prompts import (
    sql_correction_instructions_prompt,
    sql_instructions_prompt,
    visualization_selector_prompt,
    visualization_recommender_prompt,
)
from config.dependencies import get_db_session
from config.logger import logger
from models.database import Client, ClientDB, Metabase
from service.bedrock_service import BedrockAsync
from service.metabase_service import MetabaseService
from service.vectordb_service import QdrantVectorDB

db_session: AsyncSession = get_db_session()
sql_instructions = sql_instructions_prompt()
visualization_recommender = visualization_recommender_prompt()
sql_correction_instructions = sql_correction_instructions_prompt()
visualization_prompt = visualization_selector_prompt()
bedrock_async_service = BedrockAsync()
metabase_service = MetabaseService()

METABASE_URL = os.getenv("METABASE_URL")

CONTENT_TYPE = "application/json"
METABASE_DATASET_URL = f"{METABASE_URL}/api/dataset"


class HelperFunctions:
    def __init__(self):
        pass

    def _process_schema_data(self, retrieve_data: list) -> tuple:
        """Process and validate schema data"""
        tables = []
        columns = []

        for entry in retrieve_data:
            try:
                for entry in retrieve_data:
                    original_data = entry["metadata"]["original_data"]

                    tables.append(original_data["Table Name"])

                    columns = [
                        column["Column Name"] for column in original_data["Columns"]
                    ]
                    columns.extend(columns)
            except Exception as e:
                logger.warning(f"Error processing schema entry: {str(e)}")
                continue

        sql_data = {
            "schema": retrieve_data,
            "tables": list(set(tables)),
            "columns": columns,
        }

        return sql_data

    async def generate_sql(self, state: GenerateSQLCreatorState):
        try:
            llm = await bedrock_async_service.create_llm()
            question = json.dumps(
                {"inputText": json.dumps(state["messages"][0].content)}
            )

            try:
                question_embedding = await bedrock_async_service.create_embedding_async(
                    question
                )
            except Exception as e:
                logger.error(f"Failed to create embedding: {str(e)}")
                raise RuntimeError("Failed to generate embedding") from e

            client_name = state["user_info"]["user_name"].lower().replace(" ", "")
            database_name = state["selected_databases"][0]["database_name"]
            collection_name = f"{client_name}_{database_name}"

            # Retrieve vector data with timeout
            try:
                retrieve_data = QdrantVectorDB(
                    collection_name=collection_name
                ).search_points(
                    query_vector=question_embedding,
                    limit=5,
                    score_threshold=0.2,
                )
            except Exception as e:
                logger.error(f"Vector search failed: {str(e)}")
                raise RuntimeError("Failed to retrieve vector data") from e

            sql_data = self._process_schema_data(retrieve_data=retrieve_data)

            system_message = sql_instructions.format(
                question=question, schema=retrieve_data
            )

            try:
                structured_llm = llm.with_structured_output(SQLQuery)
                response = structured_llm.invoke(
                    [SystemMessage(content=system_message)]
                    + [
                        HumanMessage(
                            content="Generate proper sql query that aligns with schema provided and database rules."
                        )
                    ]
                )
            except Exception as e:
                logger.error(f"SQL generation failed: {str(e)}")
                raise RuntimeError("Failed to generate SQL query") from e

            sql_queries = SQLCreator(sql_query=response.sql_query)

            # Generate visualization recommendation
            try:
                visualization_llm = llm.with_structured_output(VisualizationRecommender)
                system_message = visualization_recommender.format(
                    sql_query=sql_queries.sql_query
                )
                response = visualization_llm.invoke(
                    [SystemMessage(content=system_message)]
                    + [
                        HumanMessage(
                            content="You are the best visualization recommender."
                        )
                    ]
                )

                initially_recommended_visualization = response
            except Exception as e:
                logger.error(f"Visualization generation failed: {str(e)}")
                raise RuntimeError("Failed to generate visualization") from e

            # Write the list of analysis to state
            return {
                "sql_queries": sql_queries,
                "sql_data": sql_data,
                "count": 1,
                "count_for_visualization": 0,
                "status_enough_feedback": False,
                "initially_recommended_visualization": initially_recommended_visualization,
            }
        except Exception as e:
            logger.error(f"Error in generate_sql: {str(e)}")
            raise

    async def validate_query(self, state: GenerateSQLCreatorState):
        try:
            tables = state["sql_data"]["tables"]
            columns = state["sql_data"]["columns"]

            # Initialize the status and error lists
            schema_validation_status = True
            missing_tables = []
            missing_columns = []
            schema_error_message = ""

            # Parse the SQL query once
            sql_query = state["sql_queries"].sql_query
            parsed_query = Parser(sql_query)

            fetched_tables = set(
                parsed_query.tables
            )  # Use a set for faster membership checks
            fetched_columns = set(parsed_query.columns)

            # Check for missing tables and columns
            missing_tables = [table for table in fetched_tables if table not in tables]
            missing_columns = [
                column for column in fetched_columns if column not in columns
            ]

            # Update schema validation status
            if missing_tables or missing_columns:
                schema_validation_status = False

            # Build the error message
            if missing_tables:
                schema_error_message += f"Tables not found in predefined tables: {', '.join(missing_tables)}"
            if missing_columns:
                if (
                    schema_error_message
                ):  # Add a separator if there's already an error message
                    schema_error_message += " | "
                schema_error_message += f"Columns not found in predefined columns: {', '.join(missing_columns)}"

            # Return the results
            return {
                "tables_columns_validation_status": schema_validation_status,
                "schema_error_message": schema_error_message
                or None,  # None if no error message
            }

        except Exception as e:
            # Catch any other unexpected errors
            return {
                "tables_columns_validation_status": False,
                "schema_error_message": f"Unexpected error: {str(e)}",
            }

    async def check_metabase_query_execution(self, state: GenerateSQLCreatorState):
        client_name = state["user_info"]["user_name"]
        database_name = state["selected_databases"][0]["database_name"]

        try:
            # Execute the query within an async DB session
            async with db_session as db:
                query = (
                    select(Metabase.metabase_database_id)
                    .select_from(Client)  # Add the base table
                    .join(ClientDB, ClientDB.client_id == Client.client_id)
                    .join(Metabase, ClientDB.id == Metabase.database_id)
                    .where(Client.client_name == client_name)
                    .where(ClientDB.database_name == database_name)
                )

                # Execute the query and fetch results
                result = await db.execute(query)

                # Retrieve the result as a list of metabase_database_id
                metabase_ids = result.fetchall()

                if not metabase_ids:
                    print("No Metabase IDs found.")
                    return

                # Iterate over the result rows and print each Metabase ID
                for row in metabase_ids:
                    database_id = row.metabase_database_id

            headers = {
                "Content-Type": CONTENT_TYPE,
                "X-Metabase-Session": metabase_service.generate_session_id(),
            }
            payload = {
                "type": "native",
                "database": database_id,
                "native": {
                    "query": state["sql_queries"].sql_query,
                    "template-tags": {},
                },
                "parameters": [],
            }

            response = requests.post(
                METABASE_DATASET_URL,
                headers=headers,
                json=payload,
            )

            json_response = response.json()
            respone_list = list(json_response.keys())
            if respone_list[0] == "data":
                data = json_response["data"]["rows"]
                columns = [
                    item["display_name"] for item in json_response["data"]["cols"]
                ]

                df = pd.DataFrame(data, columns=columns)
                json_output = df.to_json(orient="records")
                return {
                    "query_execution_validation_status": True,
                    "execution_error_message": None,
                    "dataframe": json_output,
                }
            else:
                return {
                    "query_execution_validation_status": False,
                    "execution_error_message": json_response["via"][0]["error"],
                    "dataframe": None,
                }
        except Exception as e:
            print(f"An error occurred while executing the query: {e}")

    async def sql_query_accuracy_checker(self, state: GenerateSQLCreatorState):
        pass

    async def end_or_retry_feedback(self, state: GenerateSQLCreatorState):
        tables_columns_validation_status = state["tables_columns_validation_status"]
        query_execution_validation_status = state["query_execution_validation_status"]
        count = state["count"]

        if count == 2 or (
            tables_columns_validation_status and query_execution_validation_status
        ):
            return "feedback_collector"
        else:
            return "regenerate_sql_query"

    async def regenerate_sql_query(self, state: GenerateSQLCreatorState):
        # Initialize LLM (Language Model) for query generation
        llm = await bedrock_async_service.create_llm()

        # Extract necessary data from the state
        count = state["count"]
        schema = state["sql_data"]["schema"]
        tables_columns_validation_status = state["tables_columns_validation_status"]
        schema_error_message = state["schema_error_message"]
        execution_error_message = state["execution_error_message"]

        # Combine error messages into a single string
        error_message = f"{schema_error_message}\n{execution_error_message}"
        sql_query = state["sql_queries"].sql_query
        question = state["messages"][0].content

        system_message = sql_correction_instructions.format(
            schema=schema,
            question=question,
            error_message=error_message,
            current_sql_query=sql_query,
        )

        # Enforce structured output
        structured_llm = llm.with_structured_output(SQLQuery)

        # Generate SQL query
        response = structured_llm.invoke(
            [SystemMessage(content=system_message)]
            + [
                HumanMessage(
                    content="Generate proper sql query that aligns with schema provided and database rules."
                )
            ]
        )
        sql_queries = SQLCreator(sql_query=response.sql_query)

        # Write the list of analysis to state
        return {"sql_queries": sql_queries, "count": count + 1}

    async def human_feedback(self, state: GenerateSQLCreatorState):
        """No-op node that should be interrupted on"""
        count_for_visualization = state["count_for_visualization"]
        return {"count_for_visualization": count_for_visualization + 1}

    async def should_continue(self, state: GenerateSQLCreatorState):
        """Return the next node to execute"""

        status_enough_feedback = state["status_enough_feedback"]

        human_analyst_feedback = state.get("human_analyst_feedback", None)
        if not status_enough_feedback:
            return "feedback_collector"

        return "generate_diagram"

    async def feedback_collector(self, state: GenerateSQLCreatorState):
        llm = await bedrock_async_service.create_llm()
        human_analyst_feedback = state.get("human_analyst_feedback", None)
        status_enough_feedback = state.get("status_enough_feedback", None)
        sql_query = SQLCreator(sql_query=state["sql_queries"].sql_query)

        if not status_enough_feedback:
            system_message = visualization_prompt.format(
                feedback=human_analyst_feedback, sql_query=sql_query
            )

            # Enforce structured output
            structured_llm = llm.with_structured_output(VisualizationStatus)

            # Generate SQL query
            response = structured_llm.invoke(
                [SystemMessage(content=system_message)]
                + [HumanMessage(content="Generate best visualization type.")]
            ).__dict__
            print(type(response["visualization_status"]))
            print(response["visualization_status"])
            if response["visualization_status"]:
                return {
                    "status_enough_feedback": True,
                    "recommended_visualization": response[
                        "selected_visualization_types"
                    ],
                }

    async def generate_diagram(self, state: GenerateSQLCreatorState):
        pass
