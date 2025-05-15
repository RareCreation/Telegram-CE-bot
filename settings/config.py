import os
from dotenv import load_dotenv

dotenv_path = os.path.join("data", ".env")
load_dotenv(dotenv_path)

TOKEN=os.getenv("TOKEN")
