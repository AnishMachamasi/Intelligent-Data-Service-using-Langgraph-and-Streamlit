import streamlit as st
import streamlit.components.v1 as components
import requests

# Custom styles for the iframe
st.html(
    """
    <style>
    iframe {
        transform: scale(1.2);  /* Zoom in */
        transform-origin: top left;  /* Scale from top-left corner */
    }
    </style>
"""
)

# Add these constants at the top of your file
METABASE_URL = "http://localhost:3000"
METABASE_SESSION_URL = f"{METABASE_URL}/api/session"

# Metabase login credentials (replace with your credentials)
METABASE_USERNAME = "anishmachamasi2262@gmail.com"
METABASE_PASSWORD = "beinganish1@1"
CONTENT_TYPE = "application/json"

# Headers for the requests
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": METABASE_URL,
}

try:

    # Define the URL for the dashboard (you can replace the URL with the correct one for your Metabase question or dashboard)
    dashboard_url = (
        "http://localhost:3000/public/question/1079fc0f-91b8-4186-a65d-e061a70cf4b0"
    )

    st.subheader("Embedded Metabase Dashboard")

    # Generate iframe code to embed the dashboard
    iframe_code = f"""
    <iframe src="{dashboard_url}" 
            width="100%" 
            height="600px"  <!-- Increase the height as needed -->
            style="transform: scale(1.2); transform-origin: top left;"  <!-- Zoom effect -->
            frameborder="0"
            allowfullscreen></iframe>
    """

    # Embed the iframe in the Streamlit app
    components.html(iframe_code, height=900)

except Exception as e:
    st.error(f"Error loading Metabase dashboard: {str(e)}")
