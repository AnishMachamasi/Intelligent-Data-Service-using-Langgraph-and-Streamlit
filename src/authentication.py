import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader


def authenticate():
    with open("./src/authentication/config.yaml") as file:
        config = yaml.load(file, Loader=SafeLoader)

    email = ""

    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )

    authenticator.login()

    name = st.session_state["name"]
    authentication_status = st.session_state["authentication_status"]
    username = st.session_state["username"]

    for key, value in config["credentials"]["usernames"].items():
        if key == username:
            email = value["email"]

    return name, authentication_status, username, authenticator, email
