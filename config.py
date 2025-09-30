# Module imports
from logging.config import dictConfig
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # General settings
    APP_TITLE: str
    APP_SUMMARY: str
    APP_VERSION: str
    APP_RELOAD: bool

    # Logging Settings
    LOG_LEVEL_WATCHFILES: str
    LOG_LEVEL_UVICORN: str
    LOG_LEVEL_SERVICES: str

    # Database settings
    DB_HOST: str
    DB_PORT: str
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_DATABASE: str

    # Discord Oauth Settings
    DISCORD_CLIENT_ID: str
    DISCORD_CLIENT_SECRET: str
    DISCORD_AUTHORIZE_URL: str
    DISCORD_REDIRECT_URL: str
    DISCORD_ACCESS_TOKEN_URL: str
    DISCORD_USERINFO_URL: str

    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRY_MINS: int
    JWT_REFRESH_TOKEN_EXPIRY_MINS: int

    # Specify env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# Logging
log_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] [{levelname}] [{name}]: {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
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
        'uvicorn.error': {
            'handlers': ['console', 'logfile'],
            'level': settings.LOG_LEVEL_UVICORN,
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
