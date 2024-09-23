from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
from config import GPT_API_KEY, GPT_API_URL
import os
import pandas as pd

db = SQLAlchemy()

# 모델 클래스 추가
class Summary(db.Model):
    __tablename__ = 'summary'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    user = db.relationship('User', backref=db.backref('summaries', lazy=True))
    
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    summary_id = db.Column(db.Integer, db.ForeignKey('summary.id'))
    message = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    user = db.relationship('User', backref=db.backref('chats', lazy=True))
    summary = db.relationship('Summary', backref=db.backref('chats', lazy=True))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Savings(db.Model):
    __tablename__ = 'savings'
    BANK = db.Column(db.String(255), primary_key=True)
    NAME = db.Column(db.String(255), nullable=False)
    ACCUMULATION_METHOD = db.Column(db.String(255), nullable=False)
    INTEREST_RATE = db.Column(db.String(255), nullable=False)
    PREFERENTIAL_INTEREST_RATE = db.Column(db.String(255), nullable=True)
    INTEREST_METHOD = db.Column(db.Text, nullable=True)
    PREFERENTIAL_CONDITION = db.Column(db.String(255), nullable=True)
    SUBSCRIPTION_TARGET = db.Column(db.String(255), nullable=True)
    SUBSCRIPTION_METHOD = db.Column(db.String(255), nullable=True)
    INTEREST_RATE_AFTER_MATURITY = db.Column(db.String(255), nullable=True)
    PRECAUTION = db.Column(db.String(255), nullable=True)
    MONTH_CHECK = db.Column(db.String(255), nullable=True)
    
def load_savings_from_csv(csv_path):
    csv_file = os.path.join(os.path.dirname(__file__), csv_path)
    df = pd.read_csv(csv_file)
    
    for index, row in df.iterrows():
        existing_savings = Savings.query.filter_by(BANK=row['은행']).first()
        if not existing_savings:
            new_savings = Savings(
                BANK=row['은행'],
                NAME=row['상품명'],
                ACCUMULATION_METHOD=row['적립방식'],
                INTEREST_RATE=row['금리'],
                PREFERENTIAL_INTEREST_RATE=row.get('최고우대금리'),
                INTEREST_METHOD=row.get('이자계산방식'),
                PREFERENTIAL_CONDITION=row.get('우대조건'),
                SUBSCRIPTION_TARGET=row.get('가입대상'),
                SUBSCRIPTION_METHOD=row.get('가입방법'),
                INTEREST_RATE_AFTER_MATURITY=row.get('만기후금리'),
                PRECAUTION=row.get('유의사항'),
                MONTH_CHECK=row.get('저축기간')
            )
            db.session.add(new_savings)

    db.session.commit()