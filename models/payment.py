# Payment model untuk Midtrans integration
from datetime import datetime
from app import db

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    gross_amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_type = db.Column(db.String(50))
    transaction_status = db.Column(db.String(50), default='pending')
    transaction_time = db.Column(db.DateTime)
    settlement_time = db.Column(db.DateTime)
    payment_data = db.Column(db.Text)  # JSON data from Midtrans
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='payments', foreign_keys=[user_id])
    course = db.relationship('Course', backref='payments', foreign_keys=[course_id])
    
    def __repr__(self):
        return f'<Payment {self.order_id}>'
