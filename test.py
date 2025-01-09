## Visualization in Streamlit

# import streamlit as st
# import pandas as pd
# import numpy as np
# import pydeck as pdk

# # Generate random data around Nepal
# chart_data = pd.DataFrame(
#     np.random.randn(1000, 2) / [10, 10] + [28.3949, 84.1240],  # Centered on Nepal
#     columns=["lat", "lon"],
# )

# # Pydeck chart configuration
# st.pydeck_chart(
#     pdk.Deck(
#         map_style=None,  # Default map style
#         initial_view_state=pdk.ViewState(
#             latitude=28.3949,  # Centered on Nepal
#             longitude=84.1240,
#             zoom=7,            # Adjust zoom level for better view of Nepal
#             pitch=50,
#         ),
#         layers=[
#             pdk.Layer(
#                 "HexagonLayer",
#                 data=chart_data,
#                 get_position="[lon, lat]",
#                 radius=10000,  # Increase radius for larger hexagons
#                 elevation_scale=50,
#                 elevation_range=[0, 3000],
#                 pickable=True,
#                 extruded=True,
#             ),
#             pdk.Layer(
#                 "ScatterplotLayer",
#                 data=chart_data,
#                 get_position="[lon, lat]",
#                 get_color="[200, 30, 0, 160]",
#                 get_radius=5000,
#             ),
#         ],
#     )
# )


# ### Form for database

# import streamlit as st

# # Page title
# st.title("Database Connection Setup")

# # Create a form for input
# with st.form("db_credentials_form"):
#     st.subheader("Enter Database Credentials")

#     # Input fields
#     db_endpoint = st.text_input("Database Endpoint", placeholder="e.g., localhost:5432")
#     db_username = st.text_input("Username", placeholder="e.g., admin")
#     db_password = st.text_input("Password", type="password", placeholder="Enter your password securely")

#     # Submit button
#     submitted = st.form_submit_button("Submit")

# # Handle form submission
# if submitted:
#     if db_endpoint and db_username and db_password:
#         st.success("Credentials saved successfully!")
#         # Display entered values (password should not be shown in a real application)
#         st.write("**Endpoint:**", db_endpoint)
#         st.write("**Username:**", db_username)
#     else:
#         st.error("All fields are required. Please fill out the form completely.")

from src.service.bedrock_service import BedrockAsync
from src.service.vectordb_service import QdrantVectorDB
import asyncio
import json


async def generate_response():
    bedrock_service = BedrockAsync()
    vector_service = QdrantVectorDB(collection_name="anishmachamasi_postgres")

    question = "Can you give me a list of loans where the borrower has been employed for over 5 years, the home ownership status is 'MORTGAGE', and the loan amount is between $10,000 and $50,000? I also want to know the loan status, the total amount funded, and the debt-to-income ratio for each loan. Only include loans that have no more than 2 inquiries in the last 6 months and have a revolving utilization rate of less than 60%. Finally, sort the results by total payment in descending order and only include loans that have a public record."

    # Generate embedding using Bedrock
    payload = {"inputText": json.dumps(question)}
    body = json.dumps(payload)

    question_embedding = await bedrock_service.create_embedding_async(body)

    search_results = vector_service.search_points(
        query_vector=question_embedding,
        limit=5,  # Adjust based on how many results you want
        score_threshold=0.7,  # Adjust threshold based on your needs (0-1)
    )
    return search_results


# For Jupyter notebooks
if __name__ == "__main__":
    response = asyncio.run(generate_response())
    print(response)
