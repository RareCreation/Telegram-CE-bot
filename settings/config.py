import os
from dotenv import load_dotenv

dotenv_path = os.path.join("data", ".env")
load_dotenv(dotenv_path)

TOKEN=os.getenv("TOKEN")
ADMINS = [int(x.strip()) for x in os.getenv("ADMINS", "").split(",") if x.strip().isdigit()]