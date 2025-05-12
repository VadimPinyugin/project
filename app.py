from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://user:password@localhost:5432/messenger'  # fallback для локального запуска
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

class Chat(db.Model):
    __tablename__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMember(db.Model):
    __tablename__ = 'chat_members'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

@app.route('/')
def home():
    return redirect(url_for('login_page'))

@app.route('/register-page', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash("Все поля обязательны для заполнения.")
            return render_template('register.html')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Пользователь с таким логином или email уже существует.")
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash("Успешная регистрация. Войдите в систему.")
        return redirect(url_for('login_page'))

    return render_template('register.html')

@app.route('/login-page', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Неправильный логин или пароль.")
            return render_template('login.html')

        session['user_id'] = user.id
        return redirect(url_for('chats_page'))

    return render_template('login.html')

@app.route('/logout-page')
def logout_page():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/chats-page', methods=['GET', 'POST'])
def chats_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        chat_name = request.form.get('name')
        if chat_name:
            new_chat = Chat(name=chat_name)
            db.session.add(new_chat)
            db.session.commit()

            chat_member = ChatMember(chat_id=new_chat.id, user_id=user_id)
            db.session.add(chat_member)
            db.session.commit()

            initial_message = Message(chat_id=new_chat.id, sender_id=user_id, content="Чат создан")
            db.session.add(initial_message)
            db.session.commit()

            flash("Чат создан.")
        else:
            flash("Имя чата не задано.")
        return redirect(url_for('chats_page'))

    chats = (
        db.session.query(Chat)
        .join(ChatMember, Chat.id == ChatMember.chat_id)
        .filter(ChatMember.user_id == user_id)
        .all()
    )
    return render_template('chats.html', chats=chats)

@app.route('/chats/<int:chat_id>/leave', methods=['POST'])
def leave_chat(chat_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    # Найдём пользователя
    user = User.query.get(user_id)
    if not user:
        flash("Пользователь не найден.")
        return redirect(url_for('chats_page'))

    # Удалим участника из чата
    ChatMember.query.filter_by(chat_id=chat_id, user_id=user_id).delete()
    db.session.commit()

    # Добавим сообщение о выходе пользователя
    leave_message = Message(chat_id=chat_id, sender_id=user_id, content=f"{user.username} покинул чат")
    db.session.add(leave_message)
    db.session.commit()

    # Проверим, остались ли участники
    remaining_members = ChatMember.query.filter_by(chat_id=chat_id).count()
    if remaining_members == 0:
        # Удалим все сообщения
        Message.query.filter_by(chat_id=chat_id).delete()
        # Удалим сам чат
        Chat.query.filter_by(id=chat_id).delete()
        db.session.commit()
        flash("Чат удалён, так как в нём не осталось участников.")
    else:
        flash("Вы покинули чат.")

    return redirect(url_for('chats_page'))

@app.route('/chats/<int:chat_id>/messages-page', methods=['GET', 'POST'])
def view_chat(chat_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'send_as_self':
            content = request.form.get('content')
            if content:
                new_message = Message(chat_id=chat_id, sender_id=user_id, content=content)
                db.session.add(new_message)
                db.session.commit()

        elif action == 'add_user':
            new_user_id_str = request.form.get('new_user_id')
            try:
                new_user_id = int(new_user_id_str)
                user = User.query.get(new_user_id)
                if user:
                    exists = ChatMember.query.filter_by(chat_id=chat_id, user_id=new_user_id).first()
                    if not exists:
                        db.session.add(ChatMember(chat_id=chat_id, user_id=new_user_id))
                        db.session.commit()
                        db.session.add(Message(chat_id=chat_id, sender_id=user_id, content=f"{user.username} добавлен"))
                        db.session.commit()
                        flash("Пользователь добавлен.")
                else:
                    flash("Пользователь не найден.")
            except:
                flash("Неверный ID пользователя.")
        return redirect(url_for('view_chat', chat_id=chat_id))

    messages = (
        db.session.query(Message, User)
        .join(User, Message.sender_id == User.id)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.timestamp.asc())
        .all()
    )

    formatted = [
        {'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'sender': u.username, 'content': m.content}
        for m, u in messages
    ]

    return render_template('messages.html', messages=formatted, chat_id=chat_id)

if __name__ == '__main__':
    app.run(host = "0.0.0.0", port = 5000)
