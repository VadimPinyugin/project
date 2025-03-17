from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import User, Chat, Message

DATABASE_URL = "postgresql://user:password@localhost:5432/messenger"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

user1 = User(username="john_doe", email="john@example.com", password_hash="hashed_password")
user2 = User(username="jane_doe", email="jane@example.com", password_hash="hashed_password")
chat = Chat(name="John & Jane")

session.add_all([user1, user2, chat])
session.commit()

message = Message(chat_id=chat.id, sender_id=user1.id, content="Привет, как дела?")
session.add(message)
session.commit()

session.close()
