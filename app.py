from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from datetime import datetime
#from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

# Инициализация приложения
app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the Messenger API!"

# Настройки базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost:5432/messenger'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных и Marshmallow
db = SQLAlchemy(app)
ma = Marshmallow(app)

class UserSchema(ma.Schema):
    id = ma.Int()
    username = ma.Str()
    email = ma.Str()
    password_hash = ma.Str()

class ChatSchema(ma.Schema):
    id = ma.Int()
    name = ma.Str()

class MessageSchema(ma.Schema):
    id = ma.Int()
    chat_id = ma.Int()
    sender_id = ma.Int()
    content = ma.Str()
    timestamp = ma.DateTime()

# Сущности моделей из вашего проекта
class User(db.Model):
    __tablename__ = 'users'  # Update this to 'users', not 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return f'<User {self.username}>'

class Chat(db.Model):
    __tablename__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    def __repr__(self):
        return f'<Chat {self.username}>'

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    def __repr__(self):
        return f'<Message {self.username}>'

# Схемы для сериализации
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User

class ChatSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Chat

class MessageSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Message

# Реализация маршрутов для CRUD-операций

# Получение всех пользователей
@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    user_schema = UserSchema(many=True)
    return jsonify(user_schema.dump(users))

# Получение одного пользователя по ID
@app.route('/users/<int:id>', methods=['GET'])
def get_user(id):
    user = User.query.get(id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    user_schema = UserSchema()
    return jsonify(user_schema.dump(user))

# Создание нового пользователя
@app.route('/users', methods=['POST'])
def add_user():
    username = request.json['username']
    email = request.json['email']
    password_hash = request.json['password_hash']
    
    new_user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(new_user)
    db.session.commit()
    
    user_schema = UserSchema()
    return jsonify(user_schema.dump(new_user)), 201

# Добавление чата
@app.route('/chats', methods=['POST'])
def add_chat():
    name = request.json['name']
    
    new_chat = Chat(name=name)
    db.session.add(new_chat)
    db.session.commit()
    
    chat_schema = ChatSchema()
    return jsonify(chat_schema.dump(new_chat)), 201

# Получение всех сообщений в чате
@app.route('/chats/<int:chat_id>/messages', methods=['GET'])
def get_messages(chat_id):
    messages = Message.query.filter_by(chat_id=chat_id).all()
    message_schema = MessageSchema(many=True)
    return jsonify(message_schema.dump(messages))

# Отправка нового сообщения
@app.route('/messages', methods=['POST'])
def add_message():
    chat_id = request.json['chat_id']
    sender_id = request.json['sender_id']
    content = request.json['content']
    
    new_message = Message(chat_id=chat_id, sender_id=sender_id, content=content)
    db.session.add(new_message)
    db.session.commit()
    
    message_schema = MessageSchema()
    return jsonify(message_schema.dump(new_message)), 201

@app.route('/chats/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    # Find the chat by its ID
    chat = Chat.query.get(chat_id)
    
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    
    # Delete all messages in the chat
    Message.query.filter_by(chat_id=chat_id).delete()
    
    # Delete the chat itself
    db.session.delete(chat)
    db.session.commit()
    
    return jsonify({"message": f"Chat with ID {chat_id} and all its messages deleted successfully."}), 200

if __name__ == '__main__':
    app.run(debug=True)
