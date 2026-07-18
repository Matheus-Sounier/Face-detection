from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv("API_URL")
MODEL_PATH = os.getenv("MODEL_PATH")