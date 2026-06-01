import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db, init_db
from app.main import app
from app.models import TaskRoute, TaskInstance, TaskParticipant, FileRecord, ReminderLog, UserMapping, GroupMapping, RDTask, RDSubTask, PipelineTemplate, RDProject

# Use file-based SQLite for tests so connections can share the database
TEST_DB_URL = "sqlite:///./test.db"

@pytest.fixture
def db_engine():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    init_db(engine)
    yield engine
    Base.metadata.drop_all(engine)
    # Clean up test database file
    import os
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
