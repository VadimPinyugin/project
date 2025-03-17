from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import User, Chat, Message
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from faker import Faker
faker = Faker()
DATABASE_URL = "postgresql://user:password@localhost:5432/messenger"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

# Таблица пользователей
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=False, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

# Таблица чатов
class Chat(Base):
    __tablename__ = 'chats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)

# Таблица сообщений
class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey('chats.id'))
    sender_id = Column(Integer, ForeignKey('users.id'))
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat")
    sender = relationship("User")

Base.metadata.create_all(engine)
'''with engine.connect() as conn:
    conn.execute(text("ALTER SEQUENCE users_id_seq RESTART WITH 1;"))
    conn.execute(text("ALTER SEQUENCE chats_id_seq RESTART WITH 1;"))
    conn.execute(text("ALTER SEQUENCE messages_id_seq RESTART WITH 1;"))
    conn.commit()'''

# Создание пользователей
user1 = User(username=faker.name(), email=faker.email(), password_hash="hashed_password")
user2 = User(username=faker.name(), email=faker.email(), password_hash="hashed_password")

# Создание чатов
chat1 = Chat(name=faker.text())
chat2 = Chat(name=faker.text())

# Добавление и коммит пользователей и чатов (чтобы получить их id)
session.add_all([user1, user2, chat1, chat2])
session.commit()  # Важно: commit нужен для получения id!

# Создание сообщений
message1 = Message(chat_id=chat1.id, sender_id=user1.id, content=faker.words(6))
message2 = Message(chat_id=chat1.id, sender_id=user2.id, content=faker.words(6))
message3 = Message(chat_id=chat2.id, sender_id=user1.id, content=faker.words(6))
message4 = Message(chat_id=chat2.id, sender_id=user2.id, content=faker.words(6))

# Добавление сообщений
session.add_all([message1, message2, message3, message4])
session.commit() # Закоммитить сообщения после добавления
# Чтение данных (сообщений из общего чата)
print("\nСообщения из общего чата:")
for message in session.query(Message).filter(Message.chat_id == chat1.id).all():
    sender = session.query(User).filter(User.id == message.sender_id).first() # Retrieve sender from the user table
    print(f"  {sender.username}: {message.content} (at {message.timestamp})") # Use sender.username

# Чтение данных (сообщений из разговора John & Jane)
print("\nСообщения из личного чата John & Jane:")
for message in session.query(Message).filter(Message.chat_id == chat2.id).all():
    sender = session.query(User).filter(User.id == message.sender_id).first() # Retrieve sender from the user table
    print(f"  {sender.username}: {message.content} (at {message.timestamp})") # Use sender.username

# Печать списка пользователей в каждом чате
print("\nПользователи в чате:", chat1.name)
users_in_chat1 = session.query(User).join(Message).filter(Message.chat_id == chat1.id).distinct().all()
for user in users_in_chat1:
    print(f"  {user.username}")

print("\nПользователи в чате:", chat2.name)
users_in_chat2 = session.query(User).join(Message).filter(Message.chat_id == chat2.id).distinct().all()
for user in users_in_chat2:
    print(f"  {user.username}")
    
session.close()