from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default='FARMER') # FARMER or BUYER
    state = db.Column(db.String(50)) # For regional cost benchmarks
    district = db.Column(db.String(50))
    village = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    farm_profile = db.relationship('FarmProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    active_crops = db.relationship('ActiveCrop', backref='user', lazy=True)
    products = db.relationship('Product', backref='farmer', lazy=True)
    orders = db.relationship('Order', backref='customer', lazy=True, foreign_keys='Order.customer_id')

class FarmProfile(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), unique=True, nullable=False)
    location = db.Column(db.String(200))
    soil_type = db.Column(db.String(100))
    farm_size = db.Column(db.Float) # in acres
    
    # History of soil data for ML
    soil_records = db.relationship('SoilRecord', backref='farm', lazy=True, cascade='all, delete-orphan')

class SoilRecord(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farm_id = db.Column(db.String(36), db.ForeignKey('farm_profile.id'), nullable=False)
    n = db.Column(db.Float) # Nitrogen
    p = db.Column(db.Float) # Phosphorus
    k = db.Column(db.Float) # Potassium
    ph = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActiveCrop(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    crop_name = db.Column(db.String(100), nullable=False)
    sowing_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    harvest_prediction = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='GROWING') # GROWING, HARVESTED
    
    # Quality Verification Metrics
    irrigation_count = db.Column(db.Integer, default=0)
    pest_risk_events = db.Column(db.Integer, default=0)
    compliance_score = db.Column(db.Float, default=100.0) # 100% initial
    
    def get_das(self):
        """Returns Days After Sowing."""
        delta = datetime.utcnow() - self.sowing_date
        return delta.days

class Product(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    price_per_kg = db.Column(db.Float, nullable=False)
    quantity_available = db.Column(db.Float, nullable=False) # in kg
    description = db.Column(db.Text)
    
    # ML Verified Quality Score (A/B/C)
    quality_grade = db.Column(db.String(5), default='N/A')
    growth_history_json = db.Column(db.Text) # JSON string of weather/care history details
    image_url = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='PENDING') # PENDING, SHIPPED, DELIVERED, INQUIRY
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
