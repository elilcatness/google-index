from sqlalchemy import Column, Integer, ForeignKey, Text, Boolean, DateTime
from sqlalchemy.orm import relation

from src.db.db_session import SqlAlchemyBase


class Queue(SqlAlchemyBase):
    __tablename__ = 'queues'

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    user_id = Column(Integer)
    domain_id = Column(Integer, ForeignKey('domains.id'))
    number = Column(Integer)
    domain = relation('Domain', foreign_keys=domain_id)
    method = Column(Text)
    urls = Column(Text)
    start_length = Column(Integer)
    last_request = Column(DateTime, nullable=True)
    data = Column(Text, nullable=True)
    in_progress = Column(Boolean, default=False)
    is_broken = Column(Boolean, default=False)
    limit_message_sent = Column(Boolean, default=False)
