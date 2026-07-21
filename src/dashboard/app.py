import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL_INTERNAL")

st.set_page_config(
    page_title="Facial Access Control",
    page_icon=":material/badge:"
)

st.title(":material/person_add: Register Person")
st.caption("Register a new person in the facial recognition system.")

with st.form("registration_form", clear_on_submit=True):
    full_name = st.text_input("Full Name")
    employee_id = st.text_input("Employee ID")
    access_level = st.selectbox(
        "Access Level",
        ["Visitor", "Employee", "Administrator"]
    )
    st.caption("The more photos, the better the recognition accuracy")

    photo_1 = st.file_uploader("mandatory 1ª", type=["jpg", "jpeg", "png"])
    photo_2 = st.file_uploader("optional 2ª ", type=["jpg", "jpeg", "png"])
    photo_3 = st.file_uploader("optional 3ª", type=["jpg", "jpeg", "png"])

    cols = st.columns(3)
    for col, photo, label in zip(cols, [photo_1, photo_2, photo_3], ["photo 1ª", "photo 2ª", "photo 3ª"]):
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
            "and at least the first face photo before registering"
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

                # ArcFace extraction
                response = requests.post(
                    f"{API_URL}/enroll",
                    data=data,
                    files=files,
                    timeout=15,
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success(
                        f":material/check_circle: {full_name} was registered successfully."
                        f"({result.get('photos_registered', 1)} photo(s))."
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