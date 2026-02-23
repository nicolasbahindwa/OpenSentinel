"""
External APIs configuration.

Contains API keys and settings for all external services used by the agent.
"""

import os
from dataclasses import dataclass
from typing import Optional, List

from .base import BaseConfig, validate_api_key


@dataclass
class ExternalAPIsConfig(BaseConfig):
    """
    External APIs configuration.

    Contains API keys for:
    - Web Search: Tavily, DuckDuckGo
    - Weather: OpenWeatherMap
    - News: NewsAPI
    - Email: SendGrid, Mailgun
    - Maps: Google Maps
    - Calendar: Google Calendar
    - Cloud Storage: AWS S3, Google Cloud Storage
    - Database: PostgreSQL, MongoDB
    """

    # ═══════════════════════════════════════════════════════════════════════
    # WEB SEARCH APIs
    # ═══════════════════════════════════════════════════════════════════════
    tavily_api_key: Optional[str] = None
    serper_api_key: Optional[str] = None
    brave_search_api_key: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # WEATHER APIs
    # ═══════════════════════════════════════════════════════════════════════
    openweather_api_key: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # NEWS APIs
    # ═══════════════════════════════════════════════════════════════════════
    newsapi_key: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # EMAIL APIs
    # ═══════════════════════════════════════════════════════════════════════
    sendgrid_api_key: Optional[str] = None
    mailgun_api_key: Optional[str] = None
    mailgun_domain: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # MAPS & LOCATION APIs
    # ═══════════════════════════════════════════════════════════════════════
    google_maps_api_key: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # CALENDAR APIs
    # ═══════════════════════════════════════════════════════════════════════
    google_calendar_credentials_path: Optional[str] = None
    google_calendar_token_path: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # CLOUD STORAGE APIs
    # ═══════════════════════════════════════════════════════════════════════
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_s3_bucket: Optional[str] = None

    google_cloud_credentials_path: Optional[str] = None
    google_cloud_project_id: Optional[str] = None
    google_cloud_storage_bucket: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # DATABASE APIs
    # ═══════════════════════════════════════════════════════════════════════
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None

    mongodb_uri: Optional[str] = None
    mongodb_database: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ExternalAPIsConfig":
        """Load external APIs configuration from environment variables"""
        return cls(
            # Web Search
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            serper_api_key=os.getenv("SERPER_API_KEY"),
            brave_search_api_key=os.getenv("BRAVE_SEARCH_API_KEY"),

            # Weather
            openweather_api_key=os.getenv("OPENWEATHER_API_KEY"),

            # News
            newsapi_key=os.getenv("NEWSAPI_KEY"),

            # Email
            sendgrid_api_key=os.getenv("SENDGRID_API_KEY"),
            mailgun_api_key=os.getenv("MAILGUN_API_KEY"),
            mailgun_domain=os.getenv("MAILGUN_DOMAIN"),

            # Maps
            google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY"),

            # Calendar
            google_calendar_credentials_path=os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH"),
            google_calendar_token_path=os.getenv("GOOGLE_CALENDAR_TOKEN_PATH"),

            # AWS
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_s3_bucket=os.getenv("AWS_S3_BUCKET"),

            # Google Cloud
            google_cloud_credentials_path=os.getenv("GOOGLE_CLOUD_CREDENTIALS_PATH"),
            google_cloud_project_id=os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
            google_cloud_storage_bucket=os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET"),

            # PostgreSQL
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_database=os.getenv("POSTGRES_DATABASE"),
            postgres_user=os.getenv("POSTGRES_USER"),
            postgres_password=os.getenv("POSTGRES_PASSWORD"),

            # MongoDB
            mongodb_uri=os.getenv("MONGODB_URI"),
            mongodb_database=os.getenv("MONGODB_DATABASE"),
        )

    def validate(self) -> List[str]:
        """Validate external APIs configuration"""
        errors = []

        # Note: Most API keys are optional - only validate format if provided

        # Validate Tavily API key if provided
        if self.tavily_api_key:
            error = validate_api_key(self.tavily_api_key, "Tavily", required=False)
            if error:
                errors.append(error)

        # Validate OpenWeather API key if provided
        if self.openweather_api_key:
            error = validate_api_key(self.openweather_api_key, "OpenWeather", required=False)
            if error:
                errors.append(error)

        # Validate Mailgun configuration
        if self.mailgun_api_key and not self.mailgun_domain:
            errors.append("ExternalAPIsConfig: mailgun_domain is required when mailgun_api_key is set")

        # Validate AWS configuration
        if self.aws_access_key_id and not self.aws_secret_access_key:
            errors.append("ExternalAPIsConfig: aws_secret_access_key is required when aws_access_key_id is set")
        if self.aws_secret_access_key and not self.aws_access_key_id:
            errors.append("ExternalAPIsConfig: aws_access_key_id is required when aws_secret_access_key is set")

        # Validate PostgreSQL port
        if not (1 <= self.postgres_port <= 65535):
            errors.append(
                f"ExternalAPIsConfig: postgres_port must be between 1-65535, got {self.postgres_port}"
            )

        # Validate Google Cloud configuration
        if self.google_cloud_storage_bucket and not self.google_cloud_project_id:
            errors.append(
                "ExternalAPIsConfig: google_cloud_project_id is required when google_cloud_storage_bucket is set"
            )

        return errors

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════

    def has_web_search(self) -> bool:
        """Check if any web search API is configured"""
        return bool(self.tavily_api_key or self.serper_api_key or self.brave_search_api_key)

    def has_weather(self) -> bool:
        """Check if weather API is configured"""
        return bool(self.openweather_api_key)

    def has_news(self) -> bool:
        """Check if news API is configured"""
        return bool(self.newsapi_key)

    def has_email(self) -> bool:
        """Check if any email API is configured"""
        return bool(self.sendgrid_api_key or (self.mailgun_api_key and self.mailgun_domain))

    def has_maps(self) -> bool:
        """Check if maps API is configured"""
        return bool(self.google_maps_api_key)

    def has_calendar(self) -> bool:
        """Check if calendar API is configured"""
        return bool(self.google_calendar_credentials_path)

    def has_cloud_storage(self) -> bool:
        """Check if any cloud storage is configured"""
        aws_configured = bool(self.aws_access_key_id and self.aws_secret_access_key)
        gcp_configured = bool(self.google_cloud_credentials_path and self.google_cloud_project_id)
        return aws_configured or gcp_configured

    def has_database(self) -> bool:
        """Check if any database is configured"""
        postgres_configured = bool(self.postgres_database and self.postgres_user and self.postgres_password)
        mongodb_configured = bool(self.mongodb_uri)
        return postgres_configured or mongodb_configured
