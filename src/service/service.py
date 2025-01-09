import base64
import io
import json
import logging
import os
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date
from io import BytesIO
from typing import Annotated, Any
from uuid import UUID, uuid4

import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core._api import LangChainBetaWarning
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langsmith import Client as LangsmithClient
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents import DEFAULT_AGENT, get_agent, get_all_agent_info
from config.dependencies import create_tables, get_db_session
from config.logger import logger
from core import settings
from models.backend import ClientCreate, DatabaseCreate, SQLRequest
from models.database import Client, ClientDB, Metabase
from schema import (
    ChatHistory,
    ChatHistoryInput,
    ChatMessage,
    Feedback,
    FeedbackResponse,
    ServiceMetadata,
    StreamInput,
    UserInput,
)
from service.excel_service import GenerateExcelService
from service.metabase_service import MetabaseService
from service.minio_service import MinioHandler
from service.utils import (
    convert_message_content_to_string,
    langchain_to_chat_message,
    remove_tool_calls,
)
from service.vectordb_service import QdrantVectorDB

load_dotenv()

warnings.filterwarnings("ignore", category=LangChainBetaWarning)
logging.basicConfig(level=logging.DEBUG)  # Change to INFO or DEBUG based on your needs
logger = logging.getLogger(__name__)

metabase_service = MetabaseService()
minio_handler = MinioHandler()
excel_service = GenerateExcelService()


def verify_bearer(
    http_auth: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(
            HTTPBearer(
                description="Please provide AUTH_SECRET api key.", auto_error=False
            )
        ),
    ],
) -> None:
    if not settings.AUTH_SECRET:
        return
    auth_secret = settings.AUTH_SECRET.get_secret_value()
    if not http_auth or http_auth.credentials != auth_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Construct agent with Sqlite checkpointer
    # TODO: It's probably dangerous to share the same checkpointer on multiple agents
    await create_tables()
    async with AsyncSqliteSaver.from_conn_string("./checkpoints.db") as saver:
        agents = get_all_agent_info()
        for a in agents:
            agent = get_agent(a.key)
            agent.checkpointer = saver
        yield
    # context manager will clean up the AsyncSqliteSaver on exit


app = FastAPI(lifespan=lifespan)
router = APIRouter(dependencies=[Depends(verify_bearer)])


## Database
# API Endpoint to store authenticated user
@app.post("/store_client")
async def store_client(
    client: ClientCreate, db_session: AsyncSession = Depends(get_db_session)
):
    metabase_session_id = metabase_service.generate_session_id()

    headers = {
        "Content-Type": "application/json",
        "X-Metabase-Session": metabase_session_id,
    }
    async with db_session as db:
        try:

            # Check if client already exists
            query = select(Client).where(Client.client_email == client.client_email)
            result = await db.execute(query)
            existing_client = result.scalar_one_or_none()

            if existing_client:
                return {
                    "message": "Client already exists",
                    "client_id": str(existing_client.client_id),
                    "client_name": existing_client.client_name,
                }

            # Create metabase collection for the corporate
            parentCollectionId = metabase_service.create_metabase_collection(
                client.client_name,
                headers,
            )

            # If client doesn't exist, create new client
            new_client = Client(
                client_name=client.client_name,
                client_email=client.client_email,
                parentcollectionid=parentCollectionId,
            )
            db.add(new_client)
            await db.commit()
            await db.refresh(new_client)

            return {
                "message": "Client stored successfully",
                "client_id": str(new_client.client_id),
                "client_name": new_client.client_name,
            }

        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to store client information: {str(e)}"
            )


# API Endpoint to store authenticated user
@app.post("/add_databases")
async def store_database(
    database_info: DatabaseCreate, db_session: AsyncSession = Depends(get_db_session)
):
    metabase_session_id = metabase_service.generate_session_id()

    headers = {
        "Content-Type": "application/json",
        "X-Metabase-Session": metabase_session_id,
    }
    async with db_session as db:
        # 1. Get client by email
        query = select(Client).where(Client.client_email == database_info.client_email)
        result = await db.execute(query)
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(
                status_code=404,
                detail=f"Client with email {database_info.client_email} not found",
            )

        existing_db_query = select(ClientDB).where(
            and_(
                ClientDB.client_id == client.client_id,
                ClientDB.database_name == database_info.database_config.db_name,
            )
        )

        existing_db = await db.execute(existing_db_query)
        if existing_db.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Database '{database_info.database_config.db_name}' already exists for this client",
            )

        try:

            # 2. Create ClientDB entry
            new_client_db = ClientDB(
                database_name=database_info.database_config.db_name,
                database_type=database_info.database_config.db_type.value,  # Get string value from enum
                client_id=client.client_id,
                # Other fields (excel_file, excel_location, etc.) will be NULL/None by default
                # They can be updated later as needed
            )
            db.add(new_client_db)
            await db.flush()  # This will populate the id field

            try:
                # 3. Create database in Metabase
                metabase_db_id = metabase_service.create_database(
                    database_info, headers, client.client_name
                )

                metabase_collection_id = metabase_service.create_metabase_collection(
                    database_info.database_config.db_name,
                    headers,
                    client.parentcollectionid,
                )
                # 4. Create Metabase entry
                new_metabase = Metabase(
                    metabase_database_id=metabase_db_id,
                    metabase_collection_id=metabase_collection_id,
                    database_id=new_client_db.id,
                )
                db.add(new_metabase)

                await db.commit()

                return {
                    "status": "success",
                    "message": "Database added successfully",
                    "client_db_id": new_client_db.id,
                    "metabase_id": new_metabase.id,
                }

            except Exception as e:
                await db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Error creating Metabase database: {str(e)}",
                )

        except HTTPException as he:
            # Re-raise HTTP exceptions
            raise he
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Error storing database: {str(e)}"
            )


# API Endpoint to store authenticated user
@app.get("/get_databases")
async def get_database(
    client_info: ClientCreate, db_session: AsyncSession = Depends(get_db_session)
):
    async with db_session as db:
        # Single query using JOIN to get all required data
        query = (
            select(
                ClientDB.database_name,
                Metabase.metabase_database_id,
                Metabase.metabase_collection_id,
            )
            .join(Client, ClientDB.client_id == Client.client_id)
            .join(Metabase, ClientDB.id == Metabase.database_id, isouter=True)
            .where(Client.client_email == client_info.client_email)
        )

        result = await db.execute(query)
        databases = result.all()

        if not databases:
            raise HTTPException(
                status_code=404,
                detail=f"No databases found for client with email {client_info.client_email}",
            )

        return {
            "status": "success",
            "message": "Databases retrieved successfully",
            "databases": [
                {
                    "database_name": db.database_name,
                    "metabase_database_id": db.metabase_database_id,
                    "metabase_collection_id": db.metabase_collection_id,
                }
                for db in databases
            ],
        }


## Schema
@app.post("/process_sql")
async def process_sql(
    request: SQLRequest, db_session: AsyncSession = Depends(get_db_session)
):
    async with db_session as db:
        all_results = []
        try:
            # Create bucket name from corporate name (sanitize it first)
            bucket_name = os.getenv("MINIO_BUCKET_NAME", "intelligent-data-service")
            folder = os.getenv("SQL_FOLDER")
            current_date = date.today()

            # Access the SQL content from the request
            files = request.files
            database_name = request.database_name
            client_name = request.client_name
            client_email = request.client_email
            filename = ""

            for file in files:
                filename = file["filename"]
                try:
                    logger.info(f"Processing file: {filename}")
                    folder_path = f"{str(client_name).lower().replace(' ', '-')}/{database_name}/{current_date}_sql_script/{folder}/{filename}"
                    logger.info(f"Folder path: {folder_path}")

                    # Get presigned URL for upload
                    try:
                        # Convert content to bytes if it's not already
                        file_content = file["content"]
                        if isinstance(file_content, str):
                            file_content = file_content.encode("utf-8")

                        # Direct upload to MinIO using minio client
                        await minio_handler.upload_file(
                            bucket_name,
                            folder_path,
                            file_content,
                        )

                        logger.info(f"Successfully uploaded {filename} to Minio")

                    except Exception as e:
                        logger.error(f"Error uploading to Minio: {str(e)}")
                        raise

                    base_folder_path = "/".join(folder_path.split("/")[:2])
                    query = select(Client).where(
                        Client.client_name == client_name,
                        Client.client_email == client_email,
                    )
                    result = await db.execute(query)  # Add await here
                    client = result.scalar_one_or_none()

                    if not client:
                        raise ValueError(
                            f"No client found with name {client_name} and email {client_email}"
                        )

                    # Update ClientDB entry
                    client_db_query = select(ClientDB).where(
                        ClientDB.client_id == client.client_id,
                        ClientDB.database_name == database_name,
                    )
                    result = await db.execute(client_db_query)  # Add await here
                    client_db = result.scalar_one_or_none()

                    if not client_db:
                        raise ValueError(
                            f"No ClientDB entry found for client_id {client.client_id} and database {database_name}"
                        )

                    # Update the sql_script_location
                    client_db.sql_script_location = base_folder_path
                    await db.commit()

                except Exception as e:
                    logger.error(f"Error processing file {filename}: {str(e)}")
                    all_results.append({"filename": filename, "error": str(e)})

            content_parts = []
            for file in files:
                content_parts.append(file["content"])
            combined_content = "\n\n".join(content_parts)

            response = await excel_service.convert_to_excel(combined_content)

            excel_data_base64 = base64.b64encode(response).decode("utf-8")

            return JSONResponse(
                content={
                    "status": "success",
                    "message": "SQL processed successfully",
                    "excel": {
                        "filename": filename,
                        "excel_data": excel_data_base64,
                    },
                }
            )

        except Exception as e:
            return JSONResponse(
                content={"status": "error", "message": str(e)}, status_code=500
            )


@app.post("/process_excel")
async def process_excel(
    request: SQLRequest, db_session: AsyncSession = Depends(get_db_session)
):
    async with db_session as db:
        all_results = []
        try:
            # Create bucket name from corporate name (sanitize it first)
            bucket_name = os.getenv("MINIO_BUCKET_NAME", "intelligent-data-service")
            folder = os.getenv("EXCEL_FOLDER")
            current_date = date.today()

            # Access the SQL content from the request
            files = request.files
            database_name = request.database_name
            client_name = request.client_name
            client_email = request.client_email
            filename = ""
            file_contents = []

            print(f"COUNT OF FILES: {len(files)}")

            for file in files:
                filename = file["filename"]
                try:
                    logger.info(f"Processing file: {filename}")
                    folder_path = f"{str(client_name).lower().replace(' ', '-')}/{database_name}/{current_date}_sql_script/{folder}/{filename}"
                    logger.info(f"Folder path: {folder_path}")

                    # Get presigned URL for upload
                    try:
                        # Convert content to bytes if it's not already
                        file_content = file["content"]

                        if isinstance(file_content, str):
                            file_content = file_content.encode("utf-8")

                        file_contents.append(file_content)

                        # Direct upload to MinIO using minio client
                        await minio_handler.upload_file(
                            bucket_name,
                            folder_path,
                            file_content,
                        )

                        logger.info(f"Successfully uploaded {filename} to Minio")
                        base_folder_path = "/".join(folder_path.split("/")[:2])
                        query = select(Client).where(
                            Client.client_name == client_name,
                            Client.client_email == client_email,
                        )
                        result = await db.execute(query)  # Add await here
                        client = result.scalar_one_or_none()

                        if not client:
                            raise ValueError(
                                f"No client found with name {client_name} and email {client_email}"
                            )

                        # Update ClientDB entry
                        client_db_query = select(ClientDB).where(
                            ClientDB.client_id == client.client_id,
                            ClientDB.database_name == database_name,
                        )
                        result = await db.execute(client_db_query)  # Add await here
                        client_db = result.scalar_one_or_none()

                        if not client_db:
                            raise ValueError(
                                f"No ClientDB entry found for client_id {client.client_id} and database {database_name}"
                            )

                        # Update the sql_script_location
                        client_db.excel_file = filename
                        client_db.excel_location = base_folder_path
                        await db.commit()
                    except Exception as e:
                        logger.error(f"Error uploading to Minio: {str(e)}")
                        raise
                except Exception as e:
                    logger.error(f"Error processing file {filename}: {str(e)}")
                    all_results.append({"filename": filename, "error": str(e)})

            client_name = str(client_name).lower().replace(" ", "")
            collection_name = f"{client_name}_{database_name}"
            vector_db_service = QdrantVectorDB(collection_name=collection_name)
            for file_content in file_contents:
                excel_json = await excel_service.json_from_excel(file_content)
                collection_response = vector_db_service.check_collection_exists()
                if collection_response:
                    logger.info(f"Collection {collection_name} already exists.")
                else:
                    vector_db_service.create_collection()
                embedding_response = await vector_db_service.upsert_points(excel_json)

            return {"status": "success", "message": "Excel file processed successfully"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


@router.get("/info")
async def info() -> ServiceMetadata:
    models = list(settings.AVAILABLE_MODELS)
    models.sort()
    return ServiceMetadata(
        agents=get_all_agent_info(),
        models=models,
        default_agent=DEFAULT_AGENT,
        default_model=settings.DEFAULT_MODEL,
    )


def _parse_input(user_input: UserInput) -> tuple[dict[str, Any], UUID]:
    run_id = uuid4()
    thread_id = user_input.thread_id or str(uuid4())
    kwargs = {
        "input": {
            "messages": [HumanMessage(content=user_input.message)],
            "user_info": user_input.user_info,
            "selected_databases": user_input.selected_databases,
        },
        "config": RunnableConfig(
            configurable={"thread_id": thread_id, "model": user_input.model},
            run_id=run_id,
        ),
    }
    return kwargs, run_id


@router.post("/{agent_id}/invoke")
@router.post("/invoke")
async def invoke(
    user_input: UserInput,
    agent_id: str = DEFAULT_AGENT,
) -> ChatMessage:
    """
    Invoke an agent with user input to retrieve a final response.

    If agent_id is not provided, the default agent will be used.
    Use thread_id to persist and continue a multi-turn conversation. run_id kwarg
    is also attached to messages for recording feedback.
    """
    agent: CompiledStateGraph = get_agent(agent_id)
    kwargs, run_id = _parse_input(user_input)
    try:
        response = await agent.ainvoke(**kwargs)
        print(response)
        output = langchain_to_chat_message(response["messages"][-1])
        output.run_id = str(run_id)
        return output
    except Exception as e:
        logger.error(f"An exception occurred: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error")


async def message_generator(
    user_input: StreamInput, agent_id: str = DEFAULT_AGENT
) -> AsyncGenerator[str, None]:
    """
    Generate a stream of messages from the agent.

    This is the workhorse method for the /stream endpoint.
    """
    agent: CompiledStateGraph = get_agent(agent_id)
    kwargs, run_id = _parse_input(user_input)

    # Process streamed events from the graph and yield messages over the SSE stream.
    async for event in agent.astream_events(**kwargs, version="v2"):
        if not event:
            continue

        new_messages = []
        # Yield messages written to the graph state after node execution finishes.
        if (
            event["event"] == "on_chain_end"
            # on_chain_end gets called a bunch of times in a graph execution
            # This filters out everything except for "graph node finished"
            and any(t.startswith("graph:step:") for t in event.get("tags", []))
            and "messages" in event["data"]["output"]
        ):
            new_messages = event["data"]["output"]["messages"]

        # Also yield intermediate messages from agents.utils.CustomData.adispatch().
        if event["event"] == "on_custom_event" and "custom_data_dispatch" in event.get(
            "tags", []
        ):
            new_messages = [event["data"]]

        for message in new_messages:
            try:
                chat_message = langchain_to_chat_message(message)
                chat_message.run_id = str(run_id)
            except Exception as e:
                logger.error(f"Error parsing message: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': 'Unexpected error'})}\n\n"
                continue
            # LangGraph re-sends the input message, which feels weird, so drop it
            if (
                chat_message.type == "human"
                and chat_message.content == user_input.message
            ):
                continue
            yield f"data: {json.dumps({'type': 'message', 'content': chat_message.model_dump()})}\n\n"

        # Yield tokens streamed from LLMs.
        if (
            event["event"] == "on_chat_model_stream"
            and user_input.stream_tokens
            and "llama_guard" not in event.get("tags", [])
        ):
            content = remove_tool_calls(event["data"]["chunk"].content)
            if content:
                # Empty content in the context of OpenAI usually means
                # that the model is asking for a tool to be invoked.
                # So we only print non-empty content.
                yield f"data: {json.dumps({'type': 'token', 'content': convert_message_content_to_string(content)})}\n\n"
            continue

    yield "data: [DONE]\n\n"


def _sse_response_example() -> dict[int, Any]:
    return {
        status.HTTP_200_OK: {
            "description": "Server Sent Event Response",
            "content": {
                "text/event-stream": {
                    "example": "data: {'type': 'token', 'content': 'Hello'}\n\ndata: {'type': 'token', 'content': ' World'}\n\ndata: [DONE]\n\n",
                    "schema": {"type": "string"},
                }
            },
        }
    }


@router.post(
    "/{agent_id}/stream",
    response_class=StreamingResponse,
    responses=_sse_response_example(),
)
@router.post(
    "/stream", response_class=StreamingResponse, responses=_sse_response_example()
)
async def stream(
    user_input: StreamInput, agent_id: str = DEFAULT_AGENT
) -> StreamingResponse:
    """
    Stream an agent's response to a user input, including intermediate messages and tokens.

    If agent_id is not provided, the default agent will be used.
    Use thread_id to persist and continue a multi-turn conversation. run_id kwarg
    is also attached to all messages for recording feedback.

    Set `stream_tokens=false` to return intermediate messages but not token-by-token.
    """
    return StreamingResponse(
        message_generator(user_input, agent_id),
        media_type="text/event-stream",
    )


@router.post("/feedback")
async def feedback(feedback: Feedback) -> FeedbackResponse:
    """
    Record feedback for a run to LangSmith.

    This is a simple wrapper for the LangSmith create_feedback API, so the
    credentials can be stored and managed in the service rather than the client.
    See: https://api.smith.langchain.com/redoc#tag/feedback/operation/create_feedback_api_v1_feedback_post
    """
    client = LangsmithClient()
    kwargs = feedback.kwargs or {}
    client.create_feedback(
        run_id=feedback.run_id,
        key=feedback.key,
        score=feedback.score,
        **kwargs,
    )
    return FeedbackResponse()


@router.post("/history")
def history(input: ChatHistoryInput) -> ChatHistory:
    """
    Get chat history.
    """
    # TODO: Hard-coding DEFAULT_AGENT here is wonky
    agent: CompiledStateGraph = get_agent(DEFAULT_AGENT)
    try:
        state_snapshot = agent.get_state(
            config=RunnableConfig(
                configurable={
                    "thread_id": input.thread_id,
                }
            )
        )
        messages: list[AnyMessage] = state_snapshot.values["messages"]
        chat_messages: list[ChatMessage] = [
            langchain_to_chat_message(m) for m in messages
        ]
        return ChatHistory(messages=chat_messages)
    except Exception as e:
        logger.error(f"An exception occurred: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


app.include_router(router)
