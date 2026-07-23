import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL_INTERNAL")

st.set_page_config(
    page_title="Face Access Control System",
    page_icon=":material/badge:"
)

st.title(":material/badge: Face Access Control System")

tab_register, tab_chat = st.tabs(
    [":material/person_add: Register Person", ":material/forum: Analytics Chat"]
)

with tab_register:
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