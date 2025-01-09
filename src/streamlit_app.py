"""
    streamlit_app.py

    This module provides functionality to handle user authentication and 
    data validation for the application.
"""

import asyncio
import os
from collections.abc import AsyncGenerator

import streamlit as st
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import get_script_run_ctx

from authentication import authenticate
from client import AgentClient, AgentClientError
from client.database_client import DatabaseClient
from client.schema_client import SchemaClient
from config.logger import logger
from config.settings import (
    APP_ICON,
    APP_TITLE,
    DEFAULT_STREAMING,
    SIDEBAR_DESCRIPTION,
    SIDEBAR_TITLE,
    WELCOME_MESSAGE,
)
from schema import ChatHistory, ChatMessage
from streamlit_service.message_handller import draw_messages, handle_feedback
from streamlit_service.tabs import DatabaseView
from styles.custom_styles import BUTTON_STYLE, HIDE_STREAMLIT_STYLE, SIDEBAR_STYLE
from utils.constants.constant import DatabaseType

# A Streamlit app for interacting with the langgraph agent via a simple chat interface.
# The app has three main functions which are all run async:

# - main() - sets up the streamlit app and high level structure
# - draw_messages() - draws a set of chat messages - either replaying existing messages
#   or streaming new ones.
# - handle_feedback() - Draws a feedback widget and records feedback from the user.

# The app heavily uses AgentClient to interact with the agent's FastAPI endpoints.

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    menu_items={},
)

st.markdown(
    BUTTON_STYLE,
    unsafe_allow_html=True,
)
st.markdown(
    SIDEBAR_STYLE,
    unsafe_allow_html=True,
)

name, authentication_status, username, authenticator, email = authenticate()


async def main() -> None:
    # Hide the streamlit upper-right chrome
    st.html(
        HIDE_STREAMLIT_STYLE,
    )
    if st.get_option("client.toolbarMode") != "minimal":
        st.set_option("client.toolbarMode", "minimal")
        await asyncio.sleep(0.1)
        st.rerun()

    if "agent_client" not in st.session_state:
        load_dotenv()
        agent_url = os.getenv("AGENT_URL")
        if not agent_url:
            host = os.getenv("HOST", "0.0.0.0")
            port = os.getenv("PORT", "8000")
            agent_url = f"http://{host}:{port}"
        try:
            with st.spinner("Connecting to agent service..."):
                st.session_state.agent_client = AgentClient(base_url=agent_url)
        except AgentClientError as e:
            st.error(f"Error connecting to agent service: {e}")
            st.markdown("The service might be booting up. Try again in a few seconds.")
            st.stop()
    agent_client: AgentClient = st.session_state.agent_client

    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8000")
    agent_url = f"http://{host}:{port}"

    ## Vector Database Settings

    ## Database Settings
    if "database_client" not in st.session_state:
        st.session_state.database_client = DatabaseClient(base_url=agent_url)

    database_client: DatabaseClient = st.session_state.database_client

    if "schema_client" not in st.session_state:
        st.session_state.schema_client = SchemaClient(base_url=agent_url)

    schema_client: SchemaClient = st.session_state.schema_client

    ## TABS
    # Initialize the database view

    if "db_view" not in st.session_state:
        st.session_state.db_view = DatabaseView(database_client, schema_client)

    db_view: DatabaseView = st.session_state.db_view
    await db_view.render_database_view(name, email)

    # Add a check for client storage status
    if "client_stored" not in st.session_state:
        st.session_state.client_stored = False

    # Only store client if not already stored
    if not st.session_state.client_stored:

        result = await database_client.store_client(name, email)
        st.session_state.client_stored = True  # Mark as stored

    with st.popover("🗄️ Database Settings", use_container_width=True):
        if "show_form" not in st.session_state:
            st.session_state.show_form = False

        # Toggle the form visibility
        if st.button("➕ Add New Database"):
            st.session_state.show_form = True

            # Close the form
        if st.session_state.show_form:
            st.button(
                "❌ Close Form",
                on_click=lambda: setattr(st.session_state, "show_form", False),
            )

        # Add Database Form
        if st.session_state.show_form:
            with st.form("add_database_form"):
                db_name = st.text_input("Database Name")
                db_type = st.selectbox(
                    "Database Type",
                    options=DatabaseType.get_all_values(),
                    help="Select the type of database you want to connect to",
                )
                # Create two columns with a 7:3 ratio
                host_col, port_col = st.columns([7, 3])

                with host_col:
                    db_host = st.text_input(
                        "Database Host",
                        help="Enter the database hostname or IP address",
                    )

                with port_col:
                    db_port = st.number_input(
                        "Database Port",
                        min_value=1,
                        max_value=65535,
                        value=5432,
                        help="Enter the database port number (1-65535)",
                    )
                db_username = st.text_input("Database Username")
                db_password = st.text_input("Database Password", type="password")

                submit_button = st.form_submit_button("Save Database")
                if submit_button:
                    # Validation: Check for missing values
                    missing_fields = []
                    if not db_name:
                        missing_fields.append("Database Name")
                    if not db_type:
                        missing_fields.append("Database Type")
                    if not db_host:
                        missing_fields.append("Database Host")
                    if not db_port:
                        missing_fields.append("Database Port")
                    if not db_username:
                        missing_fields.append("Database Username")
                    if not db_password:
                        missing_fields.append("Database Password")

                    if missing_fields:
                        st.error(
                            f"Please fill in the following fields: {', '.join(missing_fields)}"
                        )
                    else:
                        # Add database API call here
                        result = await database_client.add_database(
                            email,
                            {
                                "db_name": db_name,
                                "db_type": db_type,
                                "db_host": db_host,
                                "db_port": db_port,
                                "db_username": db_username,
                                "db_password": db_password,
                            },
                        )
                        if result:
                            st.success("Database added successfully!")
                            st.session_state.show_form = (
                                False  # Close the form after success
                            )
                            st.rerun()  # Refresh the page to update database list
                        else:
                            st.error("Failed to add the database. Please try again.")

        # View Current Databases
        # Initialize session states
        if "show_database_selector" not in st.session_state:
            st.session_state.show_database_selector = False
        if "selected_db_info" not in st.session_state:
            st.session_state.selected_db_info = []

        # View Current Databases
        with st.expander("View and Select Databases", expanded=False):
            try:
                # Fetch available databases
                available_databases = await database_client.get_databases(email)

                if available_databases is None:
                    st.info(
                        "Unable to fetch databases. Please check your connection or try again later."
                    )
                elif not available_databases.get("databases"):
                    st.info(
                        "No databases available. Add a new database to get started."
                    )
                else:
                    databases_list = available_databases["databases"]

                    # Database selector
                    selected_databases = st.multiselect(
                        "Select Databases",
                        options=[db["database_name"] for db in databases_list],
                        help="Select one or more databases to use",
                    )

                    # Toggle database selection confirmation
                    if st.button("Use Selected Databases"):
                        st.session_state.show_database_selector = True

                    # Show confirmation and store selection
                    if st.session_state.show_database_selector:
                        # Add close button
                        st.button(
                            "❌ Clear Selection",
                            on_click=lambda: setattr(
                                st.session_state, "show_database_selector", False
                            ),
                        )

                        if selected_databases:
                            # Clear previous selections
                            st.session_state.selected_db_info = []

                            # Store the selected database information in session state
                            for db_name in selected_databases:
                                db_info = next(
                                    (
                                        db
                                        for db in databases_list
                                        if db["database_name"] == db_name
                                    ),
                                    None,
                                )
                                if db_info:
                                    st.session_state.selected_db_info.append(
                                        {
                                            "database_name": db_info["database_name"],
                                            "metabase_database_id": db_info[
                                                "metabase_database_id"
                                            ],
                                            "metabase_collection_id": db_info[
                                                "metabase_collection_id"
                                            ],
                                        }
                                    )

                            st.success(
                                f"Selected databases: {', '.join(selected_databases)}"
                            )

                            # Display stored information
                            st.write(
                                "Active database selections:",
                                st.session_state.selected_db_info,
                            )
                        else:
                            st.warning(
                                "No databases selected. Please select at least one database."
                            )

            except Exception as e:
                st.error(f"An error occurred while fetching databases: {str(e)}")

        if st.session_state.selected_db_info:
            print(f"SESSION DATABASE: {st.session_state.selected_db_info}")

    if "thread_id" not in st.session_state:
        thread_id = st.query_params.get("thread_id")
        if not thread_id:
            thread_id = get_script_run_ctx().session_id
            messages = []
        else:
            history: ChatHistory = agent_client.get_history(thread_id=thread_id)
            messages = history.messages
        st.session_state.messages = messages
        st.session_state.thread_id = thread_id

    # Config options
    with st.sidebar:
        st.header(SIDEBAR_TITLE)
        st.markdown(SIDEBAR_DESCRIPTION)
        with st.popover(":material/settings: Settings", use_container_width=True):
            model_idx = agent_client.info.models.index(agent_client.info.default_model)
            model = st.selectbox(
                "LLM to use", options=agent_client.info.models, index=model_idx
            )
            agent_list = [a.key for a in agent_client.info.agents]
            logger.info(agent_list)
            agent_idx = agent_list.index(agent_client.info.default_agent)
            agent_client.agent = st.selectbox(
                "Agent to use",
                options=agent_list,
                index=agent_idx,
            )
            use_streaming = st.toggle("Stream results", value=DEFAULT_STREAMING)

        @st.dialog("Architecture")
        def architecture_dialog() -> None:
            st.image(
                "https://github.com/JoshuaC215/agent-service-toolkit/blob/main/media/agent_architecture.png?raw=true"
            )
            "[View full size on Github](https://github.com/JoshuaC215/agent-service-toolkit/blob/main/media/agent_architecture.png)"
            st.caption(
                "App hosted on [Streamlit Cloud](https://share.streamlit.io/) with FastAPI service running in [Azure](https://learn.microsoft.com/en-us/azure/app-service/)"
            )

        if st.button(":material/schema: Architecture", use_container_width=True):
            architecture_dialog()

        with st.popover(":material/policy: Privacy", use_container_width=True):
            st.write(
                "Prompts, responses and feedback in this app are anonymously recorded and saved to LangSmith for product evaluation and improvement purposes only."
            )

        st.markdown(
            f"Thread ID: **{st.session_state.thread_id}**",
            help=f"Set URL query parameter ?thread_id={st.session_state.thread_id} to continue this conversation",
        )

        """[View the source code](https://github.com/JoshuaC215/agent-service-toolkit)"""
        st.caption(
            "Made with :material/favorite: by [Joshua](https://www.linkedin.com/in/joshua-k-carroll/) in Oakland"
        )

    # Draw existing messages
    messages: list[ChatMessage] = st.session_state.messages

    if len(messages) == 0:
        with st.chat_message("ai"):
            st.write(WELCOME_MESSAGE)

    # draw_messages() expects an async iterator over messages
    async def amessage_iter() -> AsyncGenerator[ChatMessage, None]:
        for m in messages:
            yield m

    await draw_messages(amessage_iter())

    # Generate new message if the user provided new input
    if user_input := st.chat_input():
        user_info = {
            "user_name": name,
            "user_email": email,
        }

        selected_databases = []
        if str(agent_client.agent) == "data-analytics":
            if not st.session_state.selected_db_info:
                st.warning("⚠️ Please select a database to continue")
                # Optionally, you can stop further execution
                st.stop()
            else:
                selected_databases = st.session_state.selected_db_info

        messages.append(ChatMessage(type="human", content=user_input))
        st.chat_message("human").write(user_input)
        try:
            if use_streaming and str(agent_client.agent) != "data-analytics":
                stream = agent_client.astream(
                    message=user_input,
                    user_info=user_info,
                    model=model,
                    thread_id=st.session_state.thread_id,
                )
                await draw_messages(stream, is_new=True)
            else:
                response = await agent_client.ainvoke(
                    message=user_input,
                    user_info=user_info,
                    selected_databases=selected_databases,
                    model=model,
                    thread_id=st.session_state.thread_id,
                )
                messages.append(response)
                st.chat_message("ai").write(response.content)
            st.rerun()  # Clear stale containers
        except AgentClientError as e:
            st.error(f"Error generating response: {e}")
            st.stop()

    # If messages have been generated, show feedback widget
    if len(messages) > 0 and st.session_state.last_message:
        with st.session_state.last_message:
            await handle_feedback()

    authenticator.logout("Logout", "sidebar")


if __name__ == "__main__":
    if authentication_status:
        st.success(f"Welcome {name}")
        asyncio.run(main())
