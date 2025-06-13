from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(64))
    records = db.relationship('Receipt', backref='user', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    receipts = db.relationship('Receipt', backref='category', lazy=True)

class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    merchant = db.Column(db.String(128))
    date = db.Column(db.String(32))
    amount = db.Column(db.Float)
    details = db.Column(db.Text)
    image_path = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 