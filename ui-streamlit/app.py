import os
from typing import Any, Dict, Optional

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678").rstrip("/")
DEFAULT_BASIC_USER = os.getenv("N8N_BASIC_AUTH_USER", "")
DEFAULT_BASIC_PASSWORD = os.getenv("N8N_BASIC_AUTH_PASSWORD", "")


def _auth_tuple(user: str, password: str) -> Optional[tuple[str, str]]:
    if user and password:
        return (user, password)
    return None


def call_json_webhook(
    url: str,
    payload: Dict[str, Any],
    user: str,
    password: str,
    timeout: int = 90,
) -> Dict[str, Any]:
    response = requests.post(
        url,
        json=payload,
        auth=_auth_tuple(user, password),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def call_file_webhook(
    url: str,
    file_name: str,
    file_bytes: bytes,
    mime_type: str,
    user: str,
    password: str,
    timeout: int = 180,
) -> Dict[str, Any]:
    files = {
        "data": (file_name, file_bytes, mime_type or "application/octet-stream"),
    }
    response = requests.post(
        url,
        files=files,
        auth=_auth_tuple(user, password),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="NutriHealth n8n Prototype", page_icon="🥗", layout="wide")
st.title("NutriHealth n8n Prototype")
st.caption("Meal planner + fitness advice + voice-to-text powered by local n8n webhooks")

with st.sidebar:
    st.header("Connection")
    base_url = st.text_input("n8n Base URL", value=DEFAULT_BASE_URL)
    basic_user = st.text_input("Basic Auth User", value=DEFAULT_BASIC_USER)
    basic_password = st.text_input(
        "Basic Auth Password",
        value=DEFAULT_BASIC_PASSWORD,
        type="password",
    )
    st.markdown("Webhook endpoints:")
    st.code(
        "\n".join(
            [
                f"{base_url}/webhook/meal-planner",
                f"{base_url}/webhook/fitness-advice",
                f"{base_url}/webhook/voice-to-text",
            ]
        ),
        language="text",
    )

tab_meal, tab_fitness, tab_voice = st.tabs(
    ["AI Meal Planner (Groq)", "Fitness Advice (HF Mistral)", "Voice-to-Text (HF Whisper)"]
)

with tab_meal:
    st.subheader("Meal Planner")
    with st.form("meal_planner_form"):
        diet = st.selectbox(
            "Diet type",
            [
                "balanced",
                "high-protein",
                "keto",
                "vegetarian",
                "vegan",
                "mediterranean",
            ],
        )
        calories = st.number_input("Target calories", min_value=900, max_value=6000, value=2200)
        allergies = st.text_input("Allergies (comma-separated)", value="peanuts,shellfish")
        submit_meal = st.form_submit_button("Generate Meal Plan")

    if submit_meal:
        payload = {
            "diet": diet,
            "calories": calories,
            "allergies": [a.strip() for a in allergies.split(",") if a.strip()],
        }
        url = f"{base_url}/webhook/meal-planner"
        with st.spinner("Calling meal planner workflow..."):
            try:
                data = call_json_webhook(url, payload, basic_user, basic_password)
                st.success("Meal plan generated")
                st.json(data)
            except requests.HTTPError as exc:
                st.error(f"HTTP error: {exc}")
                if exc.response is not None:
                    st.code(exc.response.text)
            except Exception as exc:
                st.error(f"Request failed: {exc}")

with tab_fitness:
    st.subheader("Fitness Advice")
    with st.form("fitness_advice_form"):
        query = st.text_area(
            "Ask a fitness question",
            value="How should I structure a 4-day beginner strength program?",
            height=140,
        )
        submit_fitness = st.form_submit_button("Get Advice")

    if submit_fitness:
        url = f"{base_url}/webhook/fitness-advice"
        with st.spinner("Calling fitness advice workflow..."):
            try:
                data = call_json_webhook(url, {"query": query}, basic_user, basic_password)
                st.success("Advice generated")
                st.json(data)
            except requests.HTTPError as exc:
                st.error(f"HTTP error: {exc}")
                if exc.response is not None:
                    st.code(exc.response.text)
            except Exception as exc:
                st.error(f"Request failed: {exc}")

with tab_voice:
    st.subheader("Voice to Text")
    audio_file = st.file_uploader(
        "Upload audio",
        type=["wav", "mp3", "m4a", "ogg", "flac", "webm"],
        help="The webhook expects multipart/form-data with file field name 'data'.",
    )
    if st.button("Transcribe Audio", type="primary", disabled=audio_file is None):
        if audio_file is None:
            st.warning("Please upload an audio file.")
        else:
            url = f"{base_url}/webhook/voice-to-text"
            with st.spinner("Calling Whisper workflow..."):
                try:
                    data = call_file_webhook(
                        url=url,
                        file_name=audio_file.name,
                        file_bytes=audio_file.getvalue(),
                        mime_type=audio_file.type or "application/octet-stream",
                        user=basic_user,
                        password=basic_password,
                    )
                    st.success("Transcription completed")
                    st.json(data)
                except requests.HTTPError as exc:
                    st.error(f"HTTP error: {exc}")
                    if exc.response is not None:
                        st.code(exc.response.text)
                except Exception as exc:
                    st.error(f"Request failed: {exc}")
