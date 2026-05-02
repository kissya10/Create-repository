from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(64), nullable=True)
    full_name = Column(String(128), nullable=True)
    balance = Column(Integer, default=1000, nullable=False)
    xp = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    title = Column(String(64), default="Новичок", nullable=False)
    warns_count = Column(Integer, default=0, nullable=False)
    last_bonus_date = Column(DateTime, nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    collection = Column(Text, default="", nullable=False)

    pets = relationship("Pet", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User tg_id={self.tg_id} balance={self.balance} level={self.level}>"

class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    pet_type = Column(String(64), nullable=False)
    level = Column(Integer, default=1, nullable=False)
    satiety = Column(Integer, default=100, nullable=False)

    owner = relationship("User", back_populates="pets")

    def __repr__(self):
        return f"<Pet {self.pet_type} owner={self.owner_id} satiety={self.satiety}>"

class Marriage(Base):
    __tablename__ = "marriages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user1_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wedding_date = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Marriage {self.user1_id}-{self.user2_id}>"
