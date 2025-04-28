from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Инициализация приложения
app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the Messenger API!"

# Настройки базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost:5432/messenger'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Настройки JWT
app.config['JWT_SECRET_KEY'] = 'your_secret_key_here'  # Укажи свой секретный ключ
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 360000  # Время жизни токена в секундах
jwt = JWTManager(app)

# Инициализация базы данных и Marshmallow и JWT
db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)

# Черный список для токенов
blacklist = set()

@app.before_request
def check_token_in_blacklist():
    token = request.headers.get('Authorization', None)
    if token:
        token = token.split(" ")[1]  # Извлекаем токен из заголовка Authorization
        try:
            verify_jwt_in_request()
            # Извлекаем данные токена
            decoded_token = get_jwt()
            jti = decoded_token.get('jti')
            
            # Проверяем, есть ли токен в черном списке
            if jti in blacklist:
                return jsonify({"description": "The token has been revoked.", "error": "token_revoked"}), 401
        except Exception as e:
            return jsonify({"description": str(e), "error": "invalid_token"}), 401

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return jsonify(
        {"description": "The token has been revoked.", "error": "token_revoked"}
    ), 401

# Модели
class User(db.Model):
    __tablename__ = 'users'
    
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
        return f'<Chat {self.name}>'

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.content}>'

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

# Регистрация пользователя
@app.route('/register', methods=['POST'])
def register():
    username = request.json.get('username')
    email = request.json.get('email')
    password = request.json.get('password')

    if not username or not email or not password:
        return jsonify({"error": "Missing data"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "User already exists"}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password_hash=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201

# Вход пользователя
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid username or password"}), 401

    # Создание токена с 'jti'
    access_token = create_access_token(identity=user.id)
    print(f"Generated JWT: {access_token}")  # Log token for debugging
    return jsonify(access_token=access_token)

# Разлогинивание (удаление токена из черного списка)
@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    
    # Получаем текущий токен
    token = get_jwt()

    # Извлекаем 'jti' из токена
    jti = token['jti']
    # Добавляем 'jti' в черный список
    blacklist.add(jti)

    return jsonify({"message": "Successfully logged out"}), 200

# Смена пароля
@app.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')

    if not check_password_hash(user.password_hash, old_password):
        return jsonify({"error": "Old password is incorrect"}), 400

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({"message": "Password changed successfully"})

# Пример защищённого эндпоинта
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()

    user = User.query.get(current_user_id)
    return jsonify(logged_in_as=user.username)

# Получение всех пользователей
@app.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    users = User.query.all()
    user_schema = UserSchema(many=True)
    return jsonify(user_schema.dump(users))

# Получение одного пользователя по ID
@app.route('/users/<int:id>', methods=['GET'])
@jwt_required()
def get_user(id):
    user = User.query.get(id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    user_schema = UserSchema()
    return jsonify(user_schema.dump(user))

# Создание нового чата
@app.route('/chats', methods=['POST'])
@jwt_required()
def add_chat():
    name = request.json.get('name')
    
    new_chat = Chat(name=name)
    db.session.add(new_chat)
    db.session.commit()
    
    chat_schema = ChatSchema()
    return jsonify(chat_schema.dump(new_chat)), 201

# Получение всех сообщений в чате
@app.route('/chats/<int:chat_id>/messages', methods=['GET'])
@jwt_required()
def get_messages(chat_id):
    messages = Message.query.filter_by(chat_id=chat_id).all()
    message_schema = MessageSchema(many=True)
    return jsonify(message_schema.dump(messages))

# Отправка нового сообщения
@app.route('/messages', methods=['POST'])
@jwt_required()
def add_message():
    chat_id = request.json.get('chat_id')
    sender_id = get_jwt_identity()
    content = request.json.get('content')
    
    new_message = Message(chat_id=chat_id, sender_id=sender_id, content=content)
    db.session.add(new_message)
    db.session.commit()
    
    message_schema = MessageSchema()
    return jsonify(message_schema.dump(new_message)), 201

# Удаление чата
@app.route('/chats/<int:chat_id>', methods=['DELETE'])
@jwt_required()
def delete_chat(chat_id):
    chat = Chat.query.get(chat_id)
    
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    
    Message.query.filter_by(chat_id=chat_id).delete()
    db.session.delete(chat)
    db.session.commit()
    
    return jsonify({"message": f"Chat with ID {chat_id} and all its messages deleted successfully."}), 200

if __name__ == '__main__':
    app.run(debug=True)
