import getpass
import operator
import os
from typing import Annotated, List

import pandas as pd
import requests
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg_pool import AsyncConnectionPool, ConnectionPool

from agents.data_analytics_agent.helper_functions import HelperFunctions
from agents.data_analytics_agent.models import GenerateSQLCreatorState
from service.bedrock_service import BedrockAsync

helper_functions = HelperFunctions()

load_dotenv()

builder = StateGraph(GenerateSQLCreatorState)
builder.add_node("generate_sql", helper_functions.generate_sql)
builder.add_node("validate_query", helper_functions.validate_query)
builder.add_node(
    "validate_metabase_execution", helper_functions.check_metabase_query_execution
)

builder.add_edge(START, "generate_sql")
builder.add_edge("generate_sql", "validate_query")
# builder.add_edge("generate_sql", "validate_metabase_execution")
# builder.add_edge("generate_sql", END)
builder.add_edge("validate_query", END)

data_analytics = builder.compile()
