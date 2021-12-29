from sqlalchemy import Column, Integer, String

from src.db.db_session import SqlAlchemyBase


class State(SqlAlchemyBase):
    __tablename__ = 'states'

    user_id = Column(Integer, primary_key=True, unique=True)
    callback = Column(String)
    data = Column(String, nullable=True)