from dotenv import load_dotenv
import os

from utils.airtable import AirtableManager

load_dotenv()

class Environment:
    def __init__(self) -> None:
        self.slack_bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
        self.slack_signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
        self.slack_mailroom_channel = os.environ.get("SLACK_MAILROOM_CHANNEL", "")
        self.airtable_api_key = os.environ.get("AIRTABLE_API_KEY", "")
        self.airtable_base_id = os.environ.get("AIRTABLE_BASE_ID", "")
        self.environment = os.environ.get("ENVIRONMENT", "development")
        self.port = int(os.environ.get("PORT", 3000))
        
        if not self.slack_bot_token:
            raise ValueError("SLACK_BOT_TOKEN is not set")
        if not self.slack_signing_secret:
            raise ValueError("SLACK_SIGNING_SECRET is not set")
        if not self.slack_mailroom_channel:
            raise ValueError("SLACK_MAILROOM_CHANNEL is not set")
        if not self.airtable_api_key:
            raise ValueError("AIRTABLE_API_KEY is not set")
        if not self.airtable_base_id:
            raise ValueError("AIRTABLE_BASE_ID is not set")
        if self.environment not in ["development", "production"]:
            raise ValueError("ENVIRONMENT must be either 'development' or 'production'")
    
        self.airtable = AirtableManager(api_key=self.airtable_api_key, base_id=self.airtable_base_id, production=self.environment == "production")
        
        self.COUNTRIES = ["United Kingdom"]

env = Environment()