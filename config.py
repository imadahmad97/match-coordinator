from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
    COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")
    COGNITO_REGION = os.getenv("COGNITO_REGION")
    SECRET_KEY = os.getenv("SECRET_KEY")
