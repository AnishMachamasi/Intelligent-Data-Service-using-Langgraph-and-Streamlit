import base64

import streamlit as st

from client.database_client import DatabaseClient
from client.schema_client import SchemaClient


class DatabaseView:

    def __init__(self, database_client: DatabaseClient, schema_client: SchemaClient):
        self.database_client = database_client
        self.schema_client = schema_client
        # Initialize session states if they don't exist
        if "selected_database" not in st.session_state:
            st.session_state.selected_database = None
        if "show_sql_upload" not in st.session_state:
            st.session_state.show_sql_upload = False
        if "show_excel_upload" not in st.session_state:
            st.session_state.show_excel_upload = False

    def reset_upload_states(self):
        st.session_state.show_sql_upload = False
        st.session_state.show_excel_upload = False

    def handle_database_click(self, database_name):
        if st.session_state.selected_database == database_name:
            st.session_state.selected_database = None
            self.reset_upload_states()
        else:
            st.session_state.selected_database = database_name
            self.reset_upload_states()

    def handle_sql_button(self):
        st.session_state.show_sql_upload = not st.session_state.show_sql_upload
        st.session_state.show_excel_upload = False

    def handle_excel_button(self):
        st.session_state.show_excel_upload = not st.session_state.show_excel_upload
        st.session_state.show_sql_upload = False

    async def process_sql_files(
        self,
        files: list,
        database_name: str,
        client_email: str,
        client_name: str,
    ):
        try:
            # Prepare files data
            files_data = []
            for file in files:
                content = file.getvalue().decode("utf-8")
                files_data.append({"filename": file.name, "content": content})

            # Send SQL content to backend for processing
            response = await self.schema_client.process_sql_file(
                client_name,
                client_email,
                database_name,
                files_data,
            )

            if response.get("status") == "success":
                # Get the Excel file from the response
                excel_data_base64 = response["excel"].get("excel_data")
                filename = response["excel"].get("filename")

                # Add null check before decoding
                if excel_data_base64 is not None:
                    # Decode the base64 data
                    excel_data = base64.b64decode(excel_data_base64)

                    # Create download button for the Excel file
                    st.download_button(
                        label="📥 Download Generated Excel",
                        data=excel_data,
                        file_name=f"{filename}_result.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    st.success("SQL processed successfully!")
                else:
                    st.error("No Excel data received from the server")
            else:
                st.error(f"Error processing SQL: {response.get('message')}")

        except Exception as e:
            st.error(f"Error during SQL processing: {str(e)}")

    async def process_excel_file(
        self, files, database_name: str, client_email: str, client_name: str
    ):
        try:
            # Prepare files data
            files_data = []
            for file in files:
                binary_content = file.getvalue()
                base64_content = base64.b64encode(binary_content).decode("utf-8")
                files_data.append({"filename": file.name, "content": base64_content})

            # Send Excel file to backend for processing
            response = await self.schema_client.process_excel_file(
                client_name,
                client_email,
                database_name,
                files_data,
            )

            if response.get("status") == "success":
                st.success("Excel file processed successfully!")
            else:
                st.error(f"Error processing Excel: {response.get('message')}")

        except Exception as e:
            st.error(f"Error during Excel processing: {str(e)}")

    async def render_database_view(self, client_name, client_email):
        # Create tabs
        tab1, tab2, tab3 = st.tabs(["Home", "Databases", "Settings"])

        with tab1:  # Home tab
            st.write("Welcome to Home")

        with tab2:  # Databases tab
            try:
                # Get databases from your API
                response = await self.database_client.get_databases(client_email)

                if response and response.get("status") == "success":
                    databases = response.get("databases", [])

                    # Display databases
                    for db in databases:
                        database_name = db["database_name"]

                        # Create a container for each database
                        with st.container():
                            # Database name as a button
                            if st.button(database_name, key=f"db_{database_name}"):
                                self.handle_database_click(database_name)

                            # Show upload options if database is selected
                            if st.session_state.selected_database == database_name:
                                col1, col2 = st.columns(2)

                                with col1:
                                    if st.button(
                                        "Upload SQL", key=f"sql_btn_{database_name}"
                                    ):
                                        self.handle_sql_button()

                                with col2:
                                    if st.button(
                                        "Upload Excel", key=f"excel_btn_{database_name}"
                                    ):
                                        self.handle_excel_button()

                                # Show upload forms based on button clicks
                                if st.session_state.show_sql_upload:
                                    uploaded_files = st.file_uploader(
                                        "Choose SQL file",
                                        type=["sql"],
                                        accept_multiple_files=True,
                                        key=f"sql_upload_{database_name}",
                                    )
                                    if uploaded_files:
                                        await self.process_sql_files(
                                            uploaded_files,
                                            database_name,
                                            client_email,
                                            client_name,
                                        )

                                if st.session_state.show_excel_upload:
                                    uploaded_files = st.file_uploader(
                                        "Choose Excel file",
                                        type=["xlsx", "xls"],
                                        accept_multiple_files=True,
                                        key=f"excel_upload_{database_name}",
                                    )
                                    if uploaded_files:
                                        await self.process_excel_file(
                                            uploaded_files,
                                            database_name,
                                            client_email,
                                            client_name,
                                        )

            except Exception as e:
                st.error(f"Error loading databases: {str(e)}")

        with tab3:  # Settings tab
            st.write("Settings content here")
