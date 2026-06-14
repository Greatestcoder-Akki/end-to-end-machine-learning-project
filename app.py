import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import uuid
import bcrypt
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Import Engines and Models
from models import db, User, FarmProfile, SoilRecord, ActiveCrop, Product, Order
from engine.ml_suite import MLSuite
from engine.mandi_api import MandiAPI
from engine.economics import EconomicEngine
from engine.advisory import AdvisoryEngine
from engine.weather_api import WeatherAPI
from engine.soil_api import SoilAPI

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'grow-fasal-secret-key-123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grow_fasal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Initialize Intelligence Engines
ml_suite = MLSuite()
mandi_api = MandiAPI()
economics = EconomicEngine()
advisory = AdvisoryEngine()
weather_api = WeatherAPI()
soil_api = SoilAPI()

# --- ROUTES ---

@app.route('/')
def index():
    # Fetch top 10 records for the homepage preview
    mandi_records = mandi_api.get_market_prices()
    # If API key is missing or fails, mandi_records might be a dict with 'error'
    if isinstance(mandi_records, dict) and 'error' in mandi_records:
        mandi_records = []
    
    # Fallback mock data if API fails to ensure UI looks populated
    if not mandi_records:
        mandi_records = [
            {"state": "Punjab", "mandi": "Amritsar", "commodity": "Wheat", "arrival_date": datetime.today().strftime('%d/%m/%Y'), "min_price": "2100", "max_price": "2300", "modal_price": "2200"},
            {"state": "Maharashtra", "mandi": "Pune", "commodity": "Onion", "arrival_date": datetime.today().strftime('%d/%m/%Y'), "min_price": "1500", "max_price": "1800", "modal_price": "1650"},
            {"state": "Uttar Pradesh", "mandi": "Agra", "commodity": "Potato", "arrival_date": datetime.today().strftime('%d/%m/%Y'), "min_price": "800", "max_price": "1000", "modal_price": "900"},
            {"state": "Karnataka", "mandi": "Hubli", "commodity": "Cotton", "arrival_date": datetime.today().strftime('%d/%m/%Y'), "min_price": "6000", "max_price": "6500", "modal_price": "6200"},
            {"state": "Haryana", "mandi": "Karnal", "commodity": "Rice", "arrival_date": datetime.today().strftime('%d/%m/%Y'), "min_price": "3000", "max_price": "3500", "modal_price": "3200"}
        ]
        if current_user.is_authenticated and current_user.state:
            # Injecting local data for user's state
            mandi_records.insert(0, {"state": current_user.state, "mandi": "Local District Market", "commodity": "Seasonal Vegetables", "arrival_date": datetime.today().strftime('%d/%m/%Y'), "min_price": "1200", "max_price": "1500", "modal_price": "1350"})

    return render_template('index.html', mandi_records=mandi_records[:10])

def _build_product_context(products):
    """Enriches product objects with image paths and market price comparisons."""
    mandi = MandiAPI()
    enriched = []
    
    # Simple mapping for our generated images + High quality fallbacks
    crop_images = {
        'rice': '/static/images/crop_rice.png',
        'wheat': '/static/images/crop_wheat.png',
        'maize': '/static/images/crop_maize.png',
        'cotton': '/static/images/crop_cotton.png',
        'tomato': '/static/images/crop_tomato.png',
        'onion': '/static/images/crop_onion.png',
        'potato': 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=600',
        'sugarcane': 'https://images.unsplash.com/photo-1593113598332-cd288d649433?auto=format&fit=crop&w=600',
        'soybean': 'https://images.unsplash.com/photo-1599599810769-bcde5a160d32?auto=format&fit=crop&w=600',
        'chickpea': 'https://images.unsplash.com/photo-1543255006-d6395b6f1171?auto=format&fit=crop&w=600',
        'banana': 'https://images.unsplash.com/photo-1571771894821-ad9b5886439b?auto=format&fit=crop&w=600',
        'mango': 'https://images.unsplash.com/photo-1553334820-1372ef9ad0f0?auto=format&fit=crop&w=600'
    }

    for p in products:
        # Support both SQLAlchemy model and Dict (for flexibility)
        name = p.name if hasattr(p, 'name') else p.get('name', 'Unknown')
        price = p.price_per_kg if hasattr(p, 'price_per_kg') else p.get('price_per_kg', 0)
        
        # Get market price (simulated or real from mandi api)
        mandi_info = mandi.get_nearest_mandis(28.61, 77.20, name, limit=1)
        market_price = float(mandi_info[0]['modal_price']) if mandi_info else price * 0.95
        
        enriched.append({
            'id': p.id if hasattr(p, 'id') else p.get('id'),
            'name': name,
            'farmer_id': p.farmer_id if hasattr(p, 'farmer_id') else p.get('farmer_id'),
            'quantity_available': p.quantity_available if hasattr(p, 'quantity_available') else p.get('quantity_available'),
            'price_per_kg': price,
            'quality_grade': p.quality_grade if hasattr(p, 'quality_grade') else p.get('quality_grade', 'B'),
            'category': p.category if hasattr(p, 'category') else p.get('category', 'Grain'),
            'description': p.description if hasattr(p, 'description') else p.get('description'),
            'image_url': (p.image_url if hasattr(p, 'image_url') and p.image_url else (p.get('image_url') if hasattr(p, 'get') else None)) or crop_images.get(name.lower(), 'https://images.unsplash.com/photo-1615811361523-6bd03d7748e7?auto=format&fit=crop&w=600'),
            'market_price': market_price,
            'price_diff': round(((price - market_price) / market_price) * 100, 1) if market_price else 0
        })
    return enriched

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'FARMER':
        db_crops = ActiveCrop.query.filter_by(user_id=current_user.id).all()
        active_count = len(db_crops)
        # Fetch orders for farmer's products
        farmer_products = Product.query.filter_by(farmer_id=current_user.id).all()
        farmer_product_ids = [p.id for p in farmer_products]
        recent_orders = Order.query.filter(Order.product_id.in_(farmer_product_ids)).order_by(Order.created_at.desc()).limit(10).all()
        total_revenue = sum(o.total_price for o in Order.query.filter(Order.product_id.in_(farmer_product_ids)).all())
        listed_products_count = len(farmer_products)
        return render_template('farmer_dashboard.html',
                               active_count=active_count,
                               recent_orders=recent_orders,
                               total_revenue=round(total_revenue, 2),
                               listed_products_count=listed_products_count,
                               farmer_products=farmer_products)

    # Buyer Dashboard: Show all marketplace products
    products = Product.query.filter(Product.quantity_available > 0).order_by(Product.created_at.desc()).all()
    products_ctx = _build_product_context(products)
    
    # Pre-calculate counts/stats for Amazon-like dashboard efficiency
    grade_a_count = sum(1 for p in products_ctx if p['quality_grade'] == 'A')
    total_stock = int(sum(p['quantity_available'] for p in products_ctx))
    avg_price = round(sum(p['price_per_kg'] for p in products_ctx) / len(products_ctx), 1) if products_ctx else 0
    is_buyer = current_user.is_authenticated
    
    return render_template('customer_dashboard.html',
                           products=products_ctx,
                           grade_a_count=grade_a_count,
                           total_stock=total_stock,
                           avg_price=avg_price,
                           is_buyer=is_buyer)

@app.route('/my-crops')
@login_required
def my_crops():
    if current_user.role != 'FARMER':
        return redirect(url_for('dashboard'))
    
    db_crops = ActiveCrop.query.filter_by(user_id=current_user.id).all()
    formatted_crops = []
    for crop in db_crops:
        das = crop.get_das()
        q_grade = advisory.calculate_quality_grade(crop)
        
        # Align keys with my_crops.html template expectations
        maturity_days = advisory.CROP_MATURITY_DAYS.get(crop.crop_name.lower(), 100)
        progress = min(100, max(0, int((das / maturity_days) * 100)))
        
        status_str = "Harvest Ready" if progress >= 95 else (crop.status if crop.status else "Growing")
        formatted_crops.append({
            "id": crop.id,
            "crop_name": crop.crop_name,
            "sown_date": crop.sowing_date,
            "status": status_str,
            "growth_progress": progress,
            "quality_grade": q_grade,
            "health_score": getattr(crop, 'compliance_score', 94),
            "das": das
        })
    return render_template('my_crops.html', crops=formatted_crops)

@app.route('/mandi-trends')
def mandi_trends():
    # Pass target_commodity to template if the farmer clicked from 'My Crops'
    target_commodity = request.args.get('commodity', '')
    
    mandi_records = mandi_api.get_market_prices()
    if isinstance(mandi_records, dict) and 'error' in mandi_records:
        mandi_records = []
    
    if not mandi_records:
        mandi_records = [
            {"state": "Punjab", "mandi": "Amritsar", "commodity": "Wheat", "arrival_date": datetime.today().strftime('%d/%m/%Y'), "min_price": "2100", "max_price": "2300", "modal_price": "2200"},
            {"state": "Maharashtra", "mandi": "Pune", "commodity": "Onion", "arrival_date": datetime.today().strftime('%d/%m/%Y'), "min_price": "1500", "max_price": "1800", "modal_price": "1650"}
        ]
        if current_user.is_authenticated and current_user.state:
            mandi_records.insert(0, {"state": current_user.state, "mandi": "Local District Market", "commodity": "Seasonal Vegetables", "arrival_date": datetime.today().strftime('%d/%m/%Y'), "min_price": "1200", "max_price": "1500", "modal_price": "1350"})

    return render_template('mandi_trends.html', mandi_records=mandi_records[:20], target_commodity=target_commodity)

@app.route('/api/mandi/nearest', methods=['POST'])
@login_required
def get_nearest_mandi():
    data = request.json
    lat = float(data.get('lat', 0.0))
    lon = float(data.get('lon', 0.0))
    commodity = data.get('commodity', 'Wheat')
    
    nearest = mandi_api.get_nearest_mandis(lat, lon, commodity, limit=3)
    return jsonify({"status": "success", "markets": nearest})

@app.route('/weather')
def weather():
    forecast = weather_api.get_6_month_forecast()
    return render_template('weather.html', forecast=forecast)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        user = User.query.filter_by(phone=phone).first()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash("Invalid credentials for system access.")
        return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        name = request.form.get('name')
        role = request.form.get('role', 'FARMER')
        state = request.form.get('state')
        district = request.form.get('district')
        village = request.form.get('village')
        
        if User.query.filter_by(phone=phone).first():
            return render_template('register.html', error="System ID Already Registered")
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        new_user = User(
            id=str(uuid.uuid4()),
            phone=phone,
            password=hashed,
            name=name,
            role=role,
            state=state,
            district=district,
            village=village
        )
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('dashboard'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- API ENDPOINTS ---

@app.route('/api/predict/crops/smart', methods=['POST'])
@login_required
def predict_crops_smart():
    data = request.json
    lat = float(data.get('lat', 20.5937)) # Default Central India
    lon = float(data.get('lon', 78.9629))
    
    # 1. Fetch Precise Soil via ISRIC SoilGrids
    soil_profile = soil_api.get_soil_profile(lat, lon)
    
    # 2. Fetch Average Weather via Open-Meteo
    forecast = weather_api.get_6_month_forecast(lat, lon)
    # Average temp over the upcoming season
    avg_temp = sum(forecast['temperature_c'][:12]) / 12 if len(forecast['temperature_c']) >= 12 else 25.0
    # Average rainfall over upcoming season (first 3 months / 12 weeks accumulated approx)
    avg_rain = sum(forecast['rainfall_mm'][:12]) / 12 * 30 # Rough monthly proxy
    
    # Default Humidity based on rainfall (simple proxy since generic ML datasets expect ~80%)
    hum = 80.0 if avg_rain > 100 else 50.0
    
    # 3. Predict [N, P, K, temperature, humidity, ph, rainfall]
    features = [
        soil_profile['N'], 
        soil_profile['P'], 
        soil_profile['K'], 
        avg_temp, hum, 
        soil_profile['ph'], 
        avg_rain
    ]
    
    recommendations = ml_suite.predict_top_crops(features)
    
    # Get Economics for the top recommendation
    top_crop = recommendations[0]['crop']
    economic_data = economics.get_profitability_analysis(
        current_user.state, top_crop, 22.0, 3800.0 # Hypothetical yield/price
    )
    
    return jsonify({
        "status": "success",
        "recommendations": recommendations,
        "economics": economic_data
    })

@app.route('/api/sow', methods=['POST'])
@login_required
def sow_crop():
    data = request.json
    new_crop = ActiveCrop(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        crop_name=data.get('crop_name'),
        sowing_date=datetime.utcnow(),
        status='GROWING'
    )
    db.session.add(new_crop)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/harvest/<crop_id>', methods=['POST'])
@login_required
def harvest_crop(crop_id):
    crop = ActiveCrop.query.get(crop_id)
    if not crop:
        return jsonify({"status": "error", "message": "Crop not found"}), 404
        
    # Read form data
    try:
        price_per_kg = float(request.form.get('selling_price', 22.0))
        quantity_available = float(request.form.get('quantity', 1000.0))
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid price or quantity"}), 400

    image_url = None
    if 'crop_image' in request.files:
        file = request.files['crop_image']
        if file and file.filename != '':
            from werkzeug.utils import secure_filename
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
            filename = f"crop_{uuid.uuid4().hex}.{ext}"
            file_path = os.path.join(app.root_path, 'static', 'uploads', filename)
            file.save(file_path)
            image_url = f"/static/uploads/{filename}"

    # Calculate Quality Grade
    grade = advisory.calculate_quality_grade(crop)
    
    # Create Market Product
    new_product = Product(
        id=str(uuid.uuid4()),
        farmer_id=current_user.id,
        name=crop.crop_name,
        price_per_kg=price_per_kg,
        quantity_available=quantity_available,
        quality_grade=grade,
        image_url=image_url,
        created_at=datetime.utcnow()
    )
    
    db.session.add(new_product)
    db.session.delete(crop) # Move from active to products
    db.session.commit()
    
    return jsonify({"status": "success", "grade": grade})

@app.route('/api/mandi/forecast', methods=['GET'])
@login_required
def mandi_forecast():
    commodity = request.args.get('commodity', 'Wheat')
    trend = mandi_api.get_price_series(current_user.state, commodity)
    return jsonify({"trend": trend})


# ─────────────────────────────────────────────────────────────────────────────
#  E-COMMERCE: MARKETPLACE PURCHASE FLOW
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/purchase', methods=['POST'])
@login_required
def purchase():
    """Buyer places a purchase for a specific product lot."""
    if current_user.role != 'BUYER':
        return jsonify({"status": "error", "message": "Only buyers can purchase products."}), 403

    data = request.json
    product_id = data.get('product_id')
    quantity = float(data.get('quantity', 0))

    if quantity <= 0:
        return jsonify({"status": "error", "message": "Quantity must be greater than zero."}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"status": "error", "message": "Product not found."}), 404

    if product.quantity_available < quantity:
        return jsonify({"status": "error", "message": f"Only {product.quantity_available} kg available."}), 400

    if product.farmer_id == current_user.id:
        return jsonify({"status": "error", "message": "You cannot purchase your own product."}), 400

    total_price = round(product.price_per_kg * quantity, 2)

    # Create order
    new_order = Order(
        id=str(uuid.uuid4()),
        customer_id=current_user.id,
        product_id=product_id,
        quantity=quantity,
        total_price=total_price,
        status='CONFIRMED'
    )

    # Deduct stock
    product.quantity_available -= quantity
    if product.quantity_available <= 0:
        product.quantity_available = 0

    db.session.add(new_order)
    db.session.commit()

    return jsonify({
        "status": "success",
        "order_id": new_order.id,
        "total_price": total_price,
        "message": f"Order placed successfully! ₹{total_price} for {quantity} kg of {product.name}."
    })


@app.route('/my-orders')
@login_required
def my_orders():
    """Buyer's order history page."""
    if current_user.role != 'BUYER':
        return redirect(url_for('dashboard'))

    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()
    order_details = []
    for o in orders:
        product = Product.query.get(o.product_id)
        farmer = User.query.get(product.farmer_id) if product else None
        order_details.append({
            "id": o.id[:8].upper(),
            "product_name": product.name if product else "N/A",
            "farmer_name": farmer.name if farmer else "Unknown",
            "farmer_state": farmer.state if farmer else "—",
            "quantity": o.quantity,
            "total_price": o.total_price,
            "quality_grade": product.quality_grade if product else "N/A",
            "status": o.status,
            "created_at": o.created_at.strftime('%d %b %Y, %I:%M %p')
        })

    total_spent = sum(o['total_price'] for o in order_details)
    return render_template('my_orders.html', orders=order_details, total_spent=round(total_spent, 2))


@app.route('/marketplace')
def marketplace():
    """Public-facing marketplace (accessible even without login for browsing)."""
    products = Product.query.filter(Product.quantity_available > 0).order_by(Product.created_at.desc()).all()
    products_ctx = _build_product_context(products)
    grade_a_count = sum(1 for p in products if p.quality_grade == 'A')
    total_stock = int(sum(p.quantity_available for p in products))
    avg_price = round(sum(p.price_per_kg for p in products) / len(products), 1) if products else 0
    is_buyer = current_user.is_authenticated
    return render_template('customer_dashboard.html',
                           products=products_ctx,
                           grade_a_count=grade_a_count,
                           total_stock=total_stock,
                           avg_price=avg_price,
                           is_buyer=is_buyer)


@app.route('/api/sow-manual', methods=['POST'])
@login_required
def sow_manual():
    """Manually starts a crop cycle (bypass GPS)."""
    if current_user.role != 'FARMER':
        return jsonify({'status': 'error', 'message': 'Access denied'})
    
    data = request.json
    crop_name = data.get('crop_name', 'Wheat')
    
    new_crop = ActiveCrop(
        user_id=current_user.id,
        crop_name=crop_name,
        sowing_date=datetime.utcnow(),
        status='Vegetative'
    )
    db.session.add(new_crop)
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'{crop_name} cycle started!'})


@app.route('/api/get-price-recommendation', methods=['POST'])
@login_required
def get_price_recommendation():
    """Provides ML and Mandi-based price suggestions for a farmer listing a crop."""
    data = request.json
    crop_name = data.get('crop_name')
    grade = data.get('grade', 'B')
    
    mandi = MandiAPI()
    # Use user's location if available, otherwise fallback
    lat = getattr(current_user, 'latitude', 28.61)
    lon = getattr(current_user, 'longitude', 77.20)
    
    mandi_data = mandi.get_nearest_mandis(lat, lon, crop_name, limit=1)
    base_mandi_price = float(mandi_data[0]['modal_price']) if mandi_data else 2000
    
    # ML Multiplier based on grade
    multipliers = {'A': 1.25, 'B': 1.1, 'C': 0.9, 'D': 0.75}
    ml_suggested = base_mandi_price * multipliers.get(grade, 1.0)
    
    # Platform barrier (cap)
    platform_cap = base_mandi_price * 1.5
    
    return jsonify({
        'status': 'success',
        'mandi_price': round(base_mandi_price, 2),
        'ml_recommended': round(ml_suggested, 2),
        'platform_cap': round(platform_cap, 2),
        'location': mandi_data[0]['mandi'] if mandi_data else "Regional Market"
    })
@app.route('/api/order/<order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    """Farmer can mark an order as SHIPPED or DELIVERED."""
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"status": "error", "message": "Order not found"}), 404

    product = Product.query.get(order.product_id)
    if not product or product.farmer_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    new_status = request.json.get('status')
    if new_status not in ['CONFIRMED', 'SHIPPED', 'DELIVERED']:
        return jsonify({"status": "error", "message": "Invalid status"}), 400

    order.status = new_status
    db.session.commit()
    return jsonify({"status": "success", "new_status": new_status})

@app.route('/api/crop/<crop_id>/health', methods=['GET'])
@login_required
def get_crop_health(crop_id):
    crop = ActiveCrop.query.get(crop_id)
    if not crop or crop.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Crop not found'}), 404
    
    score = crop.compliance_score
    events = crop.pest_risk_events
    irrigation = crop.irrigation_count
    grade = advisory.calculate_quality_grade(crop)
    
    return jsonify({
        'status': 'success',
        'health_score': score,
        'pest_risk_events': events,
        'irrigation_count': irrigation,
        'quality_grade': grade,
        'message': f"Crop is currently maintaining a Grade {grade} health profile."
    })

@app.route('/api/crop/<crop_id>/advice', methods=['GET'])
@login_required
def get_crop_advice(crop_id):
    crop = ActiveCrop.query.get(crop_id)
    if not crop or crop.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Crop not found'}), 404
        
    das = crop.get_das()
    stage_info = advisory.get_stage_advice(crop.crop_name, das)
    harvest_info = advisory.get_smart_harvest_advice(crop.crop_name, crop.sowing_date, current_user.state, das)
    
    return jsonify({
        'status': 'success',
        'stage': stage_info['stage'],
        'advice': stage_info['advice'],
        'harvest_alert': harvest_info.get('alert'),
        'alert_type': harvest_info.get('alert_type')
    })


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # ── Demo Farmer ──────────────────────────────────────────────
        if not User.query.filter_by(phone='0000').first():
            hashed = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            farmer = User(id='test-farmer-id', phone='0000', password=hashed,
                          name='Ranjit Singh', role='FARMER', state='Punjab',
                          district='Amritsar', village='Chogawan')
            db.session.add(farmer)

            # Crops at DIFFERENT stages of progress
            # ~5% progress  (just sown, early)
            db.session.add(ActiveCrop(
                id='crop-01', user_id='test-farmer-id', crop_name='Wheat',
                sowing_date=datetime.utcnow().replace(hour=0, minute=0, second=0) -
                            __import__('datetime').timedelta(days=5),
                status='GROWING', compliance_score=100.0
            ))
            # ~30% progress
            db.session.add(ActiveCrop(
                id='crop-02', user_id='test-farmer-id', crop_name='Cotton',
                sowing_date=datetime.utcnow().replace(hour=0, minute=0, second=0) -
                            __import__('datetime').timedelta(days=55),
                status='GROWING', irrigation_count=4, compliance_score=98.0
            ))
            # ~60% progress
            db.session.add(ActiveCrop(
                id='crop-03', user_id='test-farmer-id', crop_name='Maize',
                sowing_date=datetime.utcnow().replace(hour=0, minute=0, second=0) -
                            __import__('datetime').timedelta(days=55),
                status='GROWING', irrigation_count=6, compliance_score=95.0
            ))
            # ~90% progress — nearly ready to harvest
            db.session.add(ActiveCrop(
                id='crop-04', user_id='test-farmer-id', crop_name='Rice',
                sowing_date=datetime.utcnow().replace(hour=0, minute=0, second=0) -
                            __import__('datetime').timedelta(days=110),
                status='GROWING', irrigation_count=10, pest_risk_events=1, compliance_score=92.0
            ))
            # 100% — fully ready (harvest alert should trigger)
            db.session.add(ActiveCrop(
                id='crop-05', user_id='test-farmer-id', crop_name='Sugarcane',
                sowing_date=datetime.utcnow().replace(hour=0, minute=0, second=0) -
                            __import__('datetime').timedelta(days=340),
                status='GROWING', irrigation_count=20, compliance_score=88.0
            ))
            db.session.commit()

        # ── Demo Buyer ───────────────────────────────────────────────
        if not User.query.filter_by(phone='1111').first():
            hashed2 = bcrypt.hashpw('buyer'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            buyer = User(id='test-buyer-id', phone='1111', password=hashed2,
                         name='Arjun Mehta', role='BUYER', state='Delhi')
            db.session.add(buyer)
            db.session.commit()

        # ── Demo Marketplace Products (all grades) ────────────────────
        if not Product.query.first():
            sample_products = [
                # Grade A — premium
                Product(id='prod-01', farmer_id='test-farmer-id', name='Rice',
                        price_per_kg=32.0, quantity_available=800.0,
                        quality_grade='A', description='Premium Basmati-variety rice. Grown using precision irrigation.',
                        created_at=datetime.utcnow()),
                Product(id='prod-02', farmer_id='test-farmer-id', name='Wheat',
                        price_per_kg=24.0, quantity_available=1200.0,
                        quality_grade='A', description='High-protein wheat. Ideal for chapati flour.',
                        created_at=datetime.utcnow()),
                # Grade B — standard
                Product(id='prod-03', farmer_id='test-farmer-id', name='Maize',
                        price_per_kg=18.0, quantity_available=600.0,
                        quality_grade='B', description='Good yield maize. Best suited for animal feed and starch.',
                        created_at=datetime.utcnow()),
                Product(id='prod-04', farmer_id='test-farmer-id', name='Onion',
                        price_per_kg=14.5, quantity_available=400.0,
                        quality_grade='B', description='Medium-sized, firm onions. Moderate moisture content.',
                        created_at=datetime.utcnow()),
                # Grade C — below average
                Product(id='prod-05', farmer_id='test-farmer-id', name='Potato',
                        price_per_kg=10.0, quantity_available=900.0,
                        quality_grade='C', description='Budget potatoes. Minor surface blemishes. Good for processing.',
                        created_at=datetime.utcnow()),
                Product(id='prod-06', farmer_id='test-farmer-id', name='Sugarcane',
                        price_per_kg=5.5, quantity_available=3000.0,
                        quality_grade='C', description='Late-season cane. Lower brix content. Good for jaggery.',
                        created_at=datetime.utcnow()),
                # Grade D — basic / distressed
                Product(id='prod-07', farmer_id='test-farmer-id', name='Soybean',
                        price_per_kg=38.0, quantity_available=250.0,
                        quality_grade='D', description='Distressed lot. Harvest delayed. Sell before spoilage.',
                        created_at=datetime.utcnow()),
                # More Grade A
                Product(id='prod-08', farmer_id='test-farmer-id', name='Cotton',
                        price_per_kg=62.0, quantity_available=500.0,
                        quality_grade='A', description='Extra-long staple cotton. Top quality for textile mills.',
                        created_at=datetime.utcnow()),
                Product(id='prod-09', farmer_id='test-farmer-id', name='Tomato',
                        price_per_kg=22.0, quantity_available=300.0,
                        quality_grade='B', description='Roma variety. Firm, bright red. Farm-fresh.',
                        created_at=datetime.utcnow()),
                Product(id='prod-10', farmer_id='test-farmer-id', name='Chickpea',
                        price_per_kg=55.0, quantity_available=180.0,
                        quality_grade='A', description='Desi chickpea. High protein, no pesticides.',
                        created_at=datetime.utcnow()),
            ]
            for p in sample_products:
                db.session.add(p)
            db.session.commit()

    app.run(debug=True, port=8000)


