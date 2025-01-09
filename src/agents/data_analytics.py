from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg_pool import AsyncConnectionPool, ConnectionPool

from agents.data_analytics_agent.helper_functions import HelperFunctions
from agents.data_analytics_agent.models import GenerateSQLCreatorState
from service.bedrock_service import BedrockAsync
from utils.constants.constant import (
    agent_da_database,
    db_host,
    db_password,
    db_port,
    db_username,
    connection_kwargs,
)

helper_functions = HelperFunctions()

load_dotenv()

DB_URI = f"postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{agent_da_database}?sslmode=disable"

builder = StateGraph(GenerateSQLCreatorState)

# Adding Nodes
builder.add_node("generate_sql", helper_functions.generate_sql)
builder.add_node("validate_query", helper_functions.validate_query)
builder.add_node(
    "validate_metabase_execution", helper_functions.check_metabase_query_execution
)
builder.add_node(
    "sql_query_accuracy_checker", helper_functions.sql_query_accuracy_checker
)
builder.add_node("regenerate_sql_query", helper_functions.regenerate_sql_query)
builder.add_node("human_feedback", helper_functions.human_feedback)
builder.add_node("feedback_collector", helper_functions.feedback_collector)
builder.add_node("generate_diagram", helper_functions.generate_diagram)

# Adding Edges between Nodes
builder.add_edge(START, "generate_sql")
builder.add_edge("generate_sql", "validate_query")
builder.add_edge("generate_sql", "validate_metabase_execution")
builder.add_edge("validate_query", "sql_query_accuracy_checker")
builder.add_edge("validate_metabase_execution", "sql_query_accuracy_checker")
builder.add_conditional_edges(
    "sql_query_accuracy_checker",
    helper_functions.end_or_retry_feedback,
    ["feedback_collector", "regenerate_sql_query"],
)
builder.add_edge("regenerate_sql_query", "validate_query")
builder.add_edge("regenerate_sql_query", "validate_metabase_execution")
builder.add_edge("feedback_collector", "human_feedback")
builder.add_conditional_edges(
    "human_feedback",
    helper_functions.should_continue,
    ["feedback_collector", "generate_diagram"],
)

pool = ConnectionPool(
    conninfo=DB_URI,
    max_size=20,
    kwargs=connection_kwargs,
)
checkpointer = PostgresSaver(pool)

checkpointer.setup()

data_analytics = builder.compile(
    interrupt_before=["human_feedback"], checkpointer=checkpointer
)
