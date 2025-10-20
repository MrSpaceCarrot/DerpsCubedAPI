# Module imports
from logging.config import dictConfig
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging


class Settings(BaseSettings):
    # General settings
    APP_TITLE: str
    APP_SUMMARY: str
    APP_VERSION: str
    APP_RELOAD: bool
    APP_ORIGINS: list
    APP_RUN_SCHEDULED_TASKS: bool

    # Logging Settings
    LOG_LEVEL_WATCHFILES: str
    LOG_LEVEL_UVICORN: str
    LOG_LEVEL_APSCHEDULER: str
    LOG_LEVEL_SERVICES: str

    # Database settings
    DB_HOST: str
    DB_PORT: int
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_DATABASE: str

    # Minio Settings
    STORAGE_BUCKET_ENDPOINT: str
    STORAGE_BUCKET_ACCESS_KEY: str
    STORAGE_BUCKET_SECRET_KEY: str
    STORAGE_BUCKET_NAME: str
    STORAGE_BUCKET_CACHE_TIMEOUT: int
    STORAGE_BUCKET_MEDIA_URL: str
    STORAGE_BUCKET_REGION_NAME: str

    # Discord Oauth Settings
    DISCORD_CLIENT_ID: str
    DISCORD_CLIENT_SECRET: str
    DISCORD_AUTHORIZE_URL: str
    DISCORD_REDIRECT_URL: str
    DISCORD_SERVER_WHITELIST: list[str]
    DISCORD_BOT_TOKEN: str

    # Pterodactyl Panel Settings
    PTERODACTYL_DOMAIN: str
    PTERODACTYL_CLIENT_API_KEY: str

    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRY_MINS: int
    JWT_REFRESH_TOKEN_EXPIRY_MINS: int

    # Misc Settings
    MISC_PEOPLE_CONSTANT: int

    # Specify env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# Logging
# Define ANSI escape sequences for colors
LOG_COLORS = {
    logging.DEBUG: "\033[94m",    # Blue
    logging.INFO: "\033[92m",     # Green
    logging.WARNING: "\033[93m",  # Yellow
    logging.ERROR: "\033[91m",    # Red
    logging.CRITICAL: "\033[31m", # Maroon
}

RESET_COLOR = "\033[0m"

# Custom Formatter to colorize [levelname]
class ColorFormatter(logging.Formatter):
    def format(self, record):
        # Get color from dictionary
        log_color: str = LOG_COLORS.get(record.levelno, RESET_COLOR)

        # Apply and return formatting
        record.levelname = f"{log_color}[{record.levelname}]{RESET_COLOR}"
        return super().format(record)

# Log config
log_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            '()': ColorFormatter,
            'fmt': '\033[90m{asctime} \033[34m{levelname} \x1b[38;5;98m[{name}]\033[97m: {message}\033[0m',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/application.log',
            'backupCount': 5,
            'maxBytes': 10000000,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
        'formatter': 'verbose',
    },
    'loggers': {
        'watchfiles': {
            'handlers': ['console', 'logfile'],
            'level': settings.LOG_LEVEL_WATCHFILES,
            'propagate': False,
        },
        'uvicorn': {
            'handlers': ['console', 'logfile'],
            'level': settings.LOG_LEVEL_UVICORN,
            'propagate': False,
        },
        'apscheduler.scheduler': {
            'handlers': ['console', 'logfile'],
            'level': settings.LOG_LEVEL_APSCHEDULER,
            'propagate': False,
        },
        'services': {
            'handlers': ['console', 'logfile'],
            'level': settings.LOG_LEVEL_SERVICES,
            'propagate': False,
        },
    },
}
dictConfig(log_config)
