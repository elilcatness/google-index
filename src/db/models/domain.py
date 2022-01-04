from sqlalchemy import Column, Integer, String

from src.db.db_session import SqlAlchemyBase
from src.constants import QUEUE_LIMIT


class Domain(SqlAlchemyBase):
    __tablename__ = 'domains'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    user_id = Column(Integer)
    url = Column(String)
    login = Column(String, nullable=True)
    password = Column(String, nullable=True)
    json_keys = Column(String, nullable=True)
    limit = Column(Integer, default=QUEUE_LIMIT)

    verbose_names = {'login': 'Логин', 'password': 'Пароль', 'json_keys': 'JSON-ключи'}
