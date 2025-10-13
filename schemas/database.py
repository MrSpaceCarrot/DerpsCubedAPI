# Module Imports
import logging
from urllib.parse import quote_plus
from config import settings
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import func


logger = logging.getLogger("services")

# Database setup
DATABASE_URL = f"mysql+mysqlconnector://{settings.DB_USERNAME}:{quote_plus(settings.DB_PASSWORD)}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_DATABASE}"
engine = create_engine(DATABASE_URL)

def setup_database():
    SQLModel.metadata.create_all(engine)

# Get session
def get_session():
    with Session(engine) as session:
        yield session

# Filter a db search from a request
def apply_filters(query, model, filters):
    # Apply filters
    for field, value in filters.dict(exclude_none=True).items():
        if hasattr(model, field):
            col = getattr(model, field)
            # Allow partial queries
            if isinstance(value, str) and "%" in value:
                query = query.where(col.like(value))
            else:
                query = query.where(col == value)

    # Apply ordering
    if filters.order_by:
        if filters.order_by == "random":
            query = query.order_by(func.random())
        if hasattr(model, filters.order_by):
            col = getattr(model, filters.order_by)
            if filters.order_dir == "desc":
                query = query.where(col != None).order_by((col).desc())
            else:
                query = query.where(col != None).order_by((col).asc())
        
    # Apply pagination
    if filters.page < 1:
        filters.page = 1
    if filters.per_page < 1 or filters.per_page > 100:
        filters.per_page = 10
    offset = (filters.page - 1) * filters.per_page
    query = query.offset(offset).limit(filters.per_page)

    return query
