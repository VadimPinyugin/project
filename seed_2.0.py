from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from faker import Faker

# Настройки и подключение к БД
faker = Faker()
DATABASE_URL = "postgresql://user:password@localhost:5432/messenger"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

# Модели
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

class Chat(Base):
    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey('chats.id'))
    sender_id = Column(Integer, ForeignKey('users.id'))
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat")
    sender = relationship("User")

class ChatMember(Base):
    __tablename__ = 'chat_members'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    chat = relationship("Chat")
    user = relationship("User")

# Создание всех таблиц
Base.metadata.create_all(engine)

# Создание пользователей
user1 = User(username=faker.name(), email=faker.email(), password_hash="hashed_password")
user2 = User(username=faker.name(), email=faker.email(), password_hash="hashed_password")

# Создание чатов
chat1 = Chat(name=faker.text(max_nb_chars=20))
chat2 = Chat(name=faker.text(max_nb_chars=20))

# Добавление пользователей и чатов
session.add_all([user1, user2, chat1, chat2])
session.commit()

# Добавление участников в чаты
chat_members = [
    ChatMember(chat_id=chat1.id, user_id=user1.id),
    ChatMember(chat_id=chat1.id, user_id=user2.id),
    ChatMember(chat_id=chat2.id, user_id=user1.id),
    ChatMember(chat_id=chat2.id, user_id=user2.id),
]
session.add_all(chat_members)
session.commit()

# Создание сообщений
message1 = Message(chat_id=chat1.id, sender_id=user1.id, content=' '.join(faker.words(6)))
message2 = Message(chat_id=chat1.id, sender_id=user2.id, content=' '.join(faker.words(6)))
message3 = Message(chat_id=chat2.id, sender_id=user1.id, content=' '.join(faker.words(6)))
message4 = Message(chat_id=chat2.id, sender_id=user2.id, content=' '.join(faker.words(6)))

session.add_all([message1, message2, message3, message4])
session.commit()

# Вывод сообщений из общего чата
print("\nСообщения из общего чата:")
for message in session.query(Message).filter(Message.chat_id == chat1.id).all():
    sender = session.query(User).filter(User.id == message.sender_id).first()
    print(f"  {sender.username}: {message.content} (at {message.timestamp})")

# Вывод сообщений из личного чата
print("\nСообщения из личного чата:")
for message in session.query(Message).filter(Message.chat_id == chat2.id).all():
    sender = session.query(User).filter(User.id == message.sender_id).first()
    print(f"  {sender.username}: {message.content} (at {message.timestamp})")

# Вывод участников чатов через chat_members
print("\nУчастники чата:", chat1.name)
for user in session.query(User).join(ChatMember).filter(ChatMember.chat_id == chat1.id).all():
    print(f"  {user.username}")

print("\nУчастники чата:", chat2.name)
for user in session.query(User).join(ChatMember).filter(ChatMember.chat_id == chat2.id).all():
    print(f"  {user.username}")

session.close()
