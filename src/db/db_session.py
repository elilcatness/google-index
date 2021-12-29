from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

SqlAlchemyBase = declarative_base()
__factory = None


def global_init(url):
    url = url.strip().replace('postgres', 'postgresql')
    global __factory
    if __factory:
        return
    if not url:
        raise Exception('Некорректный адрес БД')
    engine = create_engine(url, echo=False, poolclass=NullPool)
    __factory = sessionmaker(bind=engine)
    from . import __all_models
    SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    global __factory
    return __factory()