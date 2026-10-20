from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

connect_args = {'check_same_thread': False} if settings.database_url.startswith('sqlite') else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session_context():
    with Session(engine) as session:
        yield session


def get_session():
    with Session(engine) as session:
        yield session
