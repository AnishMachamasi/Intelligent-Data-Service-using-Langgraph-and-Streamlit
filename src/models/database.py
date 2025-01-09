from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from config.database import Base


class Client(Base):
    __tablename__ = "clients"
    client_id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, index=True)
    client_email = Column(String, unique=True, index=True)
    parentcollectionid = Column(Integer)

    # Relationships
    client_dbs = relationship("ClientDB", back_populates="client")


class ClientDB(Base):
    __tablename__ = "client_dbs"
    id = Column(Integer, primary_key=True)
    database_name = Column(String(50), nullable=False)
    database_type = Column(String(20), nullable=False)
    excel_file = Column(String(200))
    excel_location = Column(String(200))
    sql_script_location = Column(String(200))
    total_tables = Column(Integer)
    client_id = Column(Integer, ForeignKey("clients.client_id"))

    # Relationships
    client = relationship("Client", back_populates="client_dbs")
    metabases = relationship("Metabase", back_populates="client_db")


class Metabase(Base):
    __tablename__ = "metabase"
    id = Column(Integer, primary_key=True)
    metabase_database_id = Column(Integer, nullable=False)
    metabase_collection_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    database_id = Column(Integer, ForeignKey("client_dbs.id"), nullable=False)

    # Relationships
    client_db = relationship("ClientDB", back_populates="metabases")
