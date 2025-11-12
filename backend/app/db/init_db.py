"""
Database initialization
"""
from app.db.base import Base
from app.db.session import engine
# Import models to ensure they are registered with SQLAlchemy
from app.models.fund import Fund  # noqa: F401
from app.models.transaction import CapitalCall, Distribution, Adjustment  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.conversation import Conversation, ChatMessage  # noqa: F401


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
