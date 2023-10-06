# database/models.py
from sqlalchemy import Boolean, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True)
    birthdate = Column(Date)
    additional_info = Column(String, nullable=True)

    user_email = Column(String, ForeignKey("users.email"))
    user = relationship("User", back_populates="contacts")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    refresh_token = Column(String, nullable=True, index=True)
    is_verified = Column(Boolean, default=False)
    avatar_url = Column(String, nullable=True)

    contacts = relationship("Contact", back_populates="user")
