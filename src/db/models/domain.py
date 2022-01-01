from sqlalchemy import Column, Integer, String

from src.db.db_session import SqlAlchemyBase


class Domain(SqlAlchemyBase):
    __tablename__ = 'domains'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    url = Column(String)
    login = Column(String, nullable=True)
    password = Column(String, nullable=True)
    api_key = Column(String, nullable=True)

    verbose_names = {'login': 'Логин', 'password': 'Пароль', 'api_key': 'API ключ'}
