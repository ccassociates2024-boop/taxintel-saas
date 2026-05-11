from app.db.models import Base
from app.db.session import engine


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database schema initialized")

