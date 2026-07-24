from io import BytesIO
from dotenv import load_dotenv

import streamlit as st

import os
import requests
import base64

load_dotenv()

API_URL = os.getenv("API_URL_INTERNAL")

st.set_page_config(
    page_title="Face Access Control System",
    page_icon=":material/badge:"
)

def register_page():
    st.title(":material/person_add: Register Person")
    st.caption("Register a new person in the facial recognition system.")

    with st.form("registration_form", clear_on_submit=True):
        full_name = st.text_input("Full Name")
        employee_id = st.text_input("Employee ID")
        access_level = st.selectbox(
            "Access Level",
            ["Visitor", "Employee", "Administrator"]
        )
        st.caption("The more photos, the better the recognition accuracy.")

        photo_1 = st.file_uploader("Required 1st Photo", type=["jpg", "jpeg", "png"])
        photo_2 = st.file_uploader("Optional 2nd Photo", type=["jpg", "jpeg", "png"])
        photo_3 = st.file_uploader("Optional 3rd Photo", type=["jpg", "jpeg", "png"])

        cols = st.columns(3)
        for col, photo, label in zip(
            cols,
            [photo_1, photo_2, photo_3],
            ["1st Photo", "2nd Photo", "3rd Photo"],
        ):
            if photo is not None:
                col.image(photo, caption=label, width=150)

        submit = st.form_submit_button(
            ":material/how_to_reg: Register"
        )

    if submit:
        missing_fields = (
            not full_name or
            not employee_id or
            photo_1 is None
        )

        if missing_fields:
            st.error(
                ":material/error: Please provide the full name, employee ID, "
                "and at least the first face photo before registering."
            )
        else:
            with st.spinner("Extracting face embedding and saving the record..."):
                try:
                    files = {
                        "photo_1": (photo_1.name, photo_1.getvalue(), photo_1.type),
                    }
                    if photo_2 is not None:
                        files["photo_2"] = (photo_2.name, photo_2.getvalue(), photo_2.type)
                    if photo_3 is not None:
                        files["photo_3"] = (photo_3.name, photo_3.getvalue(), photo_3.type)

                    data = {
                        "name": full_name,
                        "employee_id": employee_id,
                        "access_level": access_level,
                    }

                    response = requests.post(
                        f"{API_URL}/enroll",
                        data=data,
                        files=files,
                        timeout=40,
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.success(
                            f":material/check_circle: {full_name} was registered successfully "
                            f"{result.get('photos_registered', 1)} photo(s)."
                        )
                    else:
                        st.error(
                            f":material/cancel: Registration failed "
                            f"({response.status_code})\n\n{response.text}"
                        )

                except requests.exceptions.RequestException as exc:
                    st.error(
                        f":material/cloud_off: Unable to connect to the API.\n\n{exc}"
                    )

def chat_page():
    st.title(":material/forum: Analytics Chat")
    st.caption("Ask questions in natural language about the recorded access events.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input(
        "Example: Who attempted to access outside business hours this week?"
    )

    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking, it might take a while..."):
                try:
                    response = requests.post(
                        f"{API_URL}/analytics/chat",
                        json={
                            "message": question,
                            "history": st.session_state.chat_history[:-1],
                        },
                        timeout=120,
                    )

                    if response.status_code == 200:
                        reply = response.json()["reply"]
                    else:
                        reply = (
                            f":material/error: Error ({response.status_code}): "
                            f"{response.text}"
                        )

                except requests.exceptions.RequestException as exc:
                    reply = (
                        f":material/cloud_off: Unable to connect to the API.\n\n{exc}"
                    )

                st.markdown(reply)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": reply}
        )

def unknown_faces_page():
    st.title(":material/person_search: Unknown Faces")
    st.caption("Recent access attempts by faces that couldn't be matched, with AI-generated descriptions.")

    limit = st.slider("Number of recent attempts to show", min_value=5, max_value=50, value=20, step=5)

    if st.button(":material/refresh: Refresh"):
        st.rerun()

    try:
        response = requests.get(
            f"{API_URL}/analytics/unknown-faces",
            params={"limit": limit},
            timeout=15,
        )
    except requests.exceptions.RequestException as exc:
        st.error(f":material/cloud_off: Unable to connect to the API.\n\n{exc}")
        return

    if response.status_code != 200:
        st.error(f":material/error: Error ({response.status_code}): {response.text}")
        return

    faces = response.json()["faces"]

    if not faces:
        st.info(":material/info: No unrecognized access attempts logged yet.")
        return

    for face in faces:
        col_img, col_info = st.columns([1, 3])

        with col_img:
            if face["image_base64"]:
                image_bytes = base64.b64decode(face["image_base64"])
                st.image(BytesIO(image_bytes), width=120)
            else:
                st.caption("No image")

        with col_info:
            st.markdown(f"**{face['attempted_at']}**")
            if face["description"]:
                st.write(face["description"])
            else:
                st.caption(":material/hourglass_empty: Description not generated yet (or generation failed).")

        st.divider()

register = st.Page(register_page, title="Register Person", icon=":material/person_add:")
chat = st.Page(chat_page, title="Analytics Chat", icon=":material/forum:")
unknown_faces = st.Page(unknown_faces_page, title="Unknown Faces", icon=":material/person_search:")

pg = st.navigation([register, chat, unknown_faces])
pg.run()