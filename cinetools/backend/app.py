"""
CineTools E-Commerce Backend
Flask REST API with TinyDB (JSON-based, free, production-grade)
"""
import os
import json
import uuid
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_jwt
)
from flask_bcrypt import Bcrypt
from tinydb import TinyDB, Query, where
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware
from dotenv import load_dotenv
import functools

load_dotenv()

app = Flask(__name__)
CORS(app, origins="*", supports_credentials=True)

# Config
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'cinetools-secret-change-in-prod-2024')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# ── Database Setup (TinyDB — JSON-based, no install needed) ──────────────────
os.makedirs('data', exist_ok=True)
db = TinyDB('data/cinetools.json', storage=CachingMiddleware(JSONStorage), indent=2)

users_table     = db.table('users')
products_table  = db.table('products')
orders_table    = db.table('orders')
rentals_table   = db.table('rentals')
cart_table      = db.table('cart')
reviews_table   = db.table('reviews')
wishlist_table  = db.table('wishlist')
coupons_table   = db.table('coupons')
categories_table = db.table('categories')
analytics_table  = db.table('analytics')

User    = Query()
Product = Query()
Order   = Query()
Rental  = Query()
Cart    = Query()
Review  = Query()
Wish    = Query()
Coupon  = Query()
Cat     = Query()
Ana     = Query()

# ── Helpers ──────────────────────────────────────────────────────────────────
def admin_required(fn):
    @functools.wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        uid = get_jwt_identity()
        user = users_table.get(User.id == uid)
        if not user or user.get('role') != 'admin':
            return jsonify(msg='Admin access required'), 403
        return fn(*args, **kwargs)
    return wrapper

def now_iso():
    return datetime.utcnow().isoformat()

def paginate(items, page=1, per_page=12):
    total = len(items)
    start = (page - 1) * per_page
    end   = start + per_page
    return {
        'items': items[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }

# ── Seed Data ────────────────────────────────────────────────────────────────
def seed_database():
    # Admin user
    if not users_table.get(User.email == 'admin@cinetools.com'):
        users_table.insert({
            'id': str(uuid.uuid4()),
            'name': 'Admin User',
            'email': 'admin@cinetools.com',
            'password': bcrypt.generate_password_hash('admin123').decode('utf-8'),
            'role': 'admin',
            'avatar': '',
            'phone': '',
            'address': {},
            'created_at': now_iso(),
            'is_active': True
        })

    # Categories
    cats = ['Cameras', 'Lenses', 'Lighting', 'Audio', 'Stabilizers', 'Monitors', 'Accessories']
    for c in cats:
        if not categories_table.get(Cat.name == c):
            categories_table.insert({'id': str(uuid.uuid4()), 'name': c, 'slug': c.lower(), 'icon': '🎬'})

    # Sample Products
    sample_products = [
        {'name': 'Sony FX6 Cinema Camera', 'category': 'Cameras', 'price': 498097.00, 'rent_price_day': 12450, 'rent_price_week': 66400, 'stock': 5, 'description': 'Full-frame cinema camera with 12.1MP sensor, perfect for professional filmmaking. Features dual-base ISO and 15+ stops of dynamic range.', 'specs': {'sensor': 'Full-Frame 12.1MP', 'iso': '80-102400', 'fps': '4K 120fps', 'weight': '890g'}, 'images': ['https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600'], 'rating': 4.8, 'reviews_count': 24, 'can_rent': True, 'can_buy': True, 'badge': 'Best Seller', 'brand': 'Sony'},
        {'name': 'ARRI ALEXA 35', 'category': 'Cameras', 'price': 6639917.00, 'rent_price_day': 207500, 'rent_price_week': 996000, 'stock': 2, 'description': 'ARRI\'s flagship cinema camera with 4.6K ALEV 4 sensor. The gold standard for Hollywood productions.', 'specs': {'sensor': '4.6K ALEV4', 'iso': '800-3200', 'fps': '4K 120fps', 'weight': '2.9kg'}, 'images': ['https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?w=600'], 'rating': 5.0, 'reviews_count': 8, 'can_rent': True, 'can_buy': True, 'badge': 'Premium', 'brand': 'ARRI'},
        {'name': 'Canon EF 50mm f/1.2L', 'category': 'Lenses', 'price': 124417.00, 'rent_price_day': 2905, 'rent_price_week': 14940, 'stock': 8, 'description': 'Legendary Canon prime lens with ultra-fast f/1.2 aperture. Exceptional low-light performance and beautiful bokeh.', 'specs': {'focal_length': '50mm', 'aperture': 'f/1.2', 'filter': '72mm', 'weight': '580g'}, 'images': ['https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600'], 'rating': 4.7, 'reviews_count': 42, 'can_rent': True, 'can_buy': True, 'badge': 'Popular', 'brand': 'Canon'},
        {'name': 'ZEISS Supreme Prime 85mm T1.5', 'category': 'Lenses', 'price': 954500.00, 'rent_price_day': 9960, 'rent_price_week': 48140, 'stock': 3, 'description': 'Cinema-grade prime lens with stunning optical performance. Favorite for portrait and drama production.', 'specs': {'focal_length': '85mm', 'aperture': 'T1.5', 'filter': '95mm', 'weight': '1.4kg'}, 'images': ['https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=600'], 'rating': 4.9, 'reviews_count': 15, 'can_rent': True, 'can_buy': True, 'badge': 'Cinema Grade', 'brand': 'ZEISS'},
        {'name': 'APUTURE 600D Pro Light', 'category': 'Lighting', 'price': 141017.00, 'rent_price_day': 3735, 'rent_price_week': 18260, 'stock': 10, 'description': '600W daylight LED light with Bowens mount. Perfect for film sets, interviews and commercial shoots.', 'specs': {'power': '600W', 'cct': '5600K', 'cri': '96+', 'range': '120m²'}, 'images': ['https://images.unsplash.com/photo-1527698266440-12104e498b76?w=600'], 'rating': 4.6, 'reviews_count': 31, 'can_rent': True, 'can_buy': True, 'badge': 'New', 'brand': 'Aputure'},
        {'name': 'DJI Ronin 4D', 'category': 'Stabilizers', 'price': 597517.00, 'rent_price_day': 14940, 'rent_price_week': 74700, 'stock': 4, 'description': '4-axis cinema-grade gimbal with built-in 6K camera system. Revolutionary stabilization technology.', 'specs': {'axes': '4-axis', 'payload': '4.5kg', 'battery': '2h 10min', 'weight': '3.6kg'}, 'images': ['https://images.unsplash.com/photo-1533750349088-cd871a92f312?w=600'], 'rating': 4.5, 'reviews_count': 19, 'can_rent': True, 'can_buy': True, 'badge': 'Featured', 'brand': 'DJI'},
        {'name': 'Sennheiser MKH 416 Shotgun', 'category': 'Audio', 'price': 82917.00, 'rent_price_day': 2075, 'rent_price_week': 9960, 'stock': 12, 'description': 'Industry-standard shotgun microphone. Used on virtually every major film and TV production worldwide.', 'specs': {'type': 'Shotgun', 'pattern': 'Supercardioid', 'frequency': '40Hz-20kHz', 'weight': '175g'}, 'images': ['https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=600'], 'rating': 4.9, 'reviews_count': 67, 'can_rent': True, 'can_buy': True, 'badge': 'Industry Standard', 'brand': 'Sennheiser'},
        {'name': 'SmallHD 702 Touch Monitor', 'category': 'Monitors', 'price': 82917.00, 'rent_price_day': 2490, 'rent_price_week': 11620, 'stock': 7, 'description': '7-inch touchscreen field monitor with 1920x1200 resolution and professional scopes for precise exposure.', 'specs': {'size': '7"', 'resolution': '1920×1200', 'brightness': '1500 nits', 'inputs': 'HDMI, SDI'}, 'images': ['https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=600'], 'rating': 4.4, 'reviews_count': 22, 'can_rent': True, 'can_buy': True, 'badge': '', 'brand': 'SmallHD'},
    ]

    for p in sample_products:
        if not products_table.get(Product.name == p['name']):
            products_table.insert({
                'id': str(uuid.uuid4()),
                'created_at': now_iso(),
                'updated_at': now_iso(),
                'is_active': True,
                'sales_count': 0,
                **p
            })

    # Coupons
    if not coupons_table.get(Coupon.code == 'CINEMA20'):
        coupons_table.insert({'id': str(uuid.uuid4()), 'code': 'CINEMA20', 'type': 'percentage', 'value': 20, 'min_order': 100, 'max_uses': 100, 'used': 0, 'expires_at': '2025-12-31', 'is_active': True})
    if not coupons_table.get(Coupon.code == 'SAVE50'):
        coupons_table.insert({'id': str(uuid.uuid4()), 'code': 'SAVE50', 'type': 'fixed', 'value': 50, 'min_order': 200, 'max_uses': 50, 'used': 0, 'expires_at': '2025-12-31', 'is_active': True})

# ════════════════════════════════════════════════════════════════════════════
#  AUTH ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ['name','email','password']):
        return jsonify(msg='Missing required fields'), 400
    if users_table.get(User.email == data['email']):
        return jsonify(msg='Email already registered'), 409
    user_id = str(uuid.uuid4())
    users_table.insert({
        'id': user_id,
        'name': data['name'],
        'email': data['email'],
        'password': bcrypt.generate_password_hash(data['password']).decode('utf-8'),
        'role': 'customer',
        'avatar': f"https://ui-avatars.com/api/?name={data['name'].replace(' ','+')}",
        'phone': data.get('phone', ''),
        'address': {},
        'created_at': now_iso(),
        'is_active': True
    })
    token = create_access_token(identity=user_id)
    user = users_table.get(User.id == user_id)
    user.pop('password', None)
    return jsonify(token=token, user=user), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = users_table.get(User.email == data.get('email',''))
    if not user or not bcrypt.check_password_hash(user['password'], data.get('password','')):
        return jsonify(msg='Invalid credentials'), 401
    token = create_access_token(identity=user['id'])
    user = dict(user); user.pop('password', None)
    return jsonify(token=token, user=user)

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def me():
    uid = get_jwt_identity()
    user = users_table.get(User.id == uid)
    if not user: return jsonify(msg='Not found'), 404
    user = dict(user); user.pop('password', None)
    return jsonify(user=user)

@app.route('/api/auth/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    uid = get_jwt_identity()
    data = request.get_json()
    allowed = ['name','phone','address','avatar']
    update = {k: data[k] for k in allowed if k in data}
    users_table.update(update, User.id == uid)
    user = users_table.get(User.id == uid)
    user = dict(user); user.pop('password', None)
    return jsonify(user=user)

# ════════════════════════════════════════════════════════════════════════════
#  PRODUCTS ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/products', methods=['GET'])
def get_products():
    args = request.args
    products = products_table.search(Product.is_active == True)

    # Filter
    if args.get('category'):
        products = [p for p in products if p.get('category','').lower() == args['category'].lower()]
    if args.get('brand'):
        products = [p for p in products if p.get('brand','').lower() == args['brand'].lower()]
    if args.get('search'):
        q = args['search'].lower()
        products = [p for p in products if q in p['name'].lower() or q in p.get('description','').lower()]
    if args.get('can_rent') == 'true':
        products = [p for p in products if p.get('can_rent')]
    if args.get('can_buy') == 'true':
        products = [p for p in products if p.get('can_buy')]
    if args.get('min_price'):
        products = [p for p in products if p['price'] >= float(args['min_price'])]
    if args.get('max_price'):
        products = [p for p in products if p['price'] <= float(args['max_price'])]

    # Sort
    sort = args.get('sort', 'created_at')
    reverse = args.get('order', 'desc') == 'desc'
    try:
        products.sort(key=lambda x: x.get(sort, 0), reverse=reverse)
    except: pass

    page = int(args.get('page', 1))
    per_page = int(args.get('per_page', 12))
    return jsonify(paginate(products, page, per_page))

@app.route('/api/products/<pid>', methods=['GET'])
def get_product(pid):
    p = products_table.get(Product.id == pid)
    if not p: return jsonify(msg='Not found'), 404
    # attach reviews
    p['reviews'] = reviews_table.search(Review.product_id == pid)
    return jsonify(product=p)

@app.route('/api/products/featured', methods=['GET'])
def featured_products():
    products = products_table.search(Product.is_active == True)
    featured = [p for p in products if p.get('badge') in ['Best Seller','Featured','Popular']][:8]
    return jsonify(products=featured)

@app.route('/api/categories', methods=['GET'])
def get_categories():
    cats = categories_table.all()
    # count products per category
    for c in cats:
        c['count'] = len(products_table.search(
            (Product.category == c['name']) & (Product.is_active == True)
        ))
    return jsonify(categories=cats)

# ── Admin Product CRUD ───────────────────────────────────────────────────────
@app.route('/api/admin/products', methods=['POST'])
@admin_required
def create_product():
    data = request.get_json()
    pid = str(uuid.uuid4())
    products_table.insert({'id': pid, 'created_at': now_iso(), 'updated_at': now_iso(),
                           'is_active': True, 'sales_count': 0, 'rating': 0,
                           'reviews_count': 0, **data})
    return jsonify(id=pid, msg='Product created'), 201

@app.route('/api/admin/products/<pid>', methods=['PUT'])
@admin_required
def update_product(pid):
    data = request.get_json()
    data['updated_at'] = now_iso()
    products_table.update(data, Product.id == pid)
    return jsonify(msg='Updated')

@app.route('/api/admin/products/<pid>', methods=['DELETE'])
@admin_required
def delete_product(pid):
    products_table.update({'is_active': False}, Product.id == pid)
    return jsonify(msg='Deleted')

# ════════════════════════════════════════════════════════════════════════════
#  CART ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/cart', methods=['GET'])
@jwt_required()
def get_cart():
    uid = get_jwt_identity()
    items = cart_table.search(Cart.user_id == uid)
    # Enrich with product data
    enriched = []
    for item in items:
        p = products_table.get(Product.id == item['product_id'])
        if p:
            enriched.append({**item, 'product': p})
    total = sum(
        (i['product']['rent_price_day'] * i.get('rent_days', 1) if i['type'] == 'rent'
         else i['product']['price']) * i['quantity']
        for i in enriched if 'product' in i
    )
    return jsonify(cart=enriched, total=round(total, 2))

@app.route('/api/cart', methods=['POST'])
@jwt_required()
def add_to_cart():
    uid = get_jwt_identity()
    data = request.get_json()
    pid = data.get('product_id')
    item_type = data.get('type', 'buy')  # 'buy' or 'rent'
    rent_days = data.get('rent_days', 1)
    qty = data.get('quantity', 1)

    existing = cart_table.get((Cart.user_id == uid) & (Cart.product_id == pid) & (Cart.type == item_type))
    if existing:
        cart_table.update({'quantity': existing['quantity'] + qty}, Cart.id == existing['id'])
    else:
        cart_table.insert({'id': str(uuid.uuid4()), 'user_id': uid, 'product_id': pid,
                           'type': item_type, 'quantity': qty, 'rent_days': rent_days,
                           'rent_start': data.get('rent_start'), 'rent_end': data.get('rent_end'),
                           'added_at': now_iso()})
    return jsonify(msg='Added to cart'), 201

@app.route('/api/cart/<cid>', methods=['PUT'])
@jwt_required()
def update_cart(cid):
    data = request.get_json()
    cart_table.update(data, Cart.id == cid)
    return jsonify(msg='Updated')

@app.route('/api/cart/<cid>', methods=['DELETE'])
@jwt_required()
def remove_from_cart(cid):
    cart_table.remove(Cart.id == cid)
    return jsonify(msg='Removed')

@app.route('/api/cart/clear', methods=['DELETE'])
@jwt_required()
def clear_cart():
    uid = get_jwt_identity()
    cart_table.remove(Cart.user_id == uid)
    return jsonify(msg='Cart cleared')

# ════════════════════════════════════════════════════════════════════════════
#  COUPON ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/coupons/apply', methods=['POST'])
@jwt_required()
def apply_coupon():
    data = request.get_json()
    code = data.get('code','').upper()
    order_total = data.get('total', 0)
    coupon = coupons_table.get((Coupon.code == code) & (Coupon.is_active == True))
    if not coupon:
        return jsonify(msg='Invalid coupon code'), 404
    if coupon.get('used', 0) >= coupon.get('max_uses', 0):
        return jsonify(msg='Coupon usage limit reached'), 400
    if order_total < coupon.get('min_order', 0):
        return jsonify(msg=f"Minimum order ${coupon['min_order']} required"), 400
    discount = (order_total * coupon['value'] / 100) if coupon['type'] == 'percentage' else coupon['value']
    return jsonify(discount=round(discount, 2), coupon=coupon)

# ════════════════════════════════════════════════════════════════════════════
#  ORDERS ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/orders', methods=['GET'])
@jwt_required()
def get_orders():
    uid = get_jwt_identity()
    orders = orders_table.search(Order.user_id == uid)
    orders.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify(orders=orders)

@app.route('/api/orders/<oid>', methods=['GET'])
@jwt_required()
def get_order(oid):
    uid = get_jwt_identity()
    order = orders_table.get(Order.id == oid)
    if not order or order['user_id'] != uid:
        return jsonify(msg='Not found'), 404
    return jsonify(order=order)

@app.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    uid = get_jwt_identity()
    data = request.get_json()
    # Get cart items
    cart_items = cart_table.search(Cart.user_id == uid)
    if not cart_items:
        return jsonify(msg='Cart is empty'), 400

    # Build order items
    order_items = []
    subtotal = 0
    for item in cart_items:
        p = products_table.get(Product.id == item['product_id'])
        if not p: continue
        if item['type'] == 'rent':
            price = p['rent_price_day'] * item.get('rent_days', 1) * item['quantity']
        else:
            price = p['price'] * item['quantity']
        subtotal += price
        order_items.append({
            'product_id': item['product_id'],
            'product_name': p['name'],
            'product_image': p['images'][0] if p.get('images') else '',
            'type': item['type'],
            'quantity': item['quantity'],
            'rent_days': item.get('rent_days'),
            'rent_start': item.get('rent_start'),
            'rent_end': item.get('rent_end'),
            'unit_price': p['rent_price_day'] if item['type'] == 'rent' else p['price'],
            'total_price': price
        })

    # Apply coupon
    discount = data.get('discount', 0)
    tax = round((subtotal - discount) * 0.08, 2)
    total = round(subtotal - discount + tax + data.get('shipping', 0), 2)

    order_id = str(uuid.uuid4())
    order_num = f"CT-{datetime.utcnow().strftime('%Y%m%d')}-{order_id[:6].upper()}"

    order = {
        'id': order_id,
        'order_number': order_num,
        'user_id': uid,
        'items': order_items,
        'shipping_address': data.get('shipping_address', {}),
        'billing_address': data.get('billing_address', {}),
        'payment_method': data.get('payment_method', 'card'),
        'subtotal': round(subtotal, 2),
        'discount': round(discount, 2),
        'tax': tax,
        'shipping': data.get('shipping', 0),
        'total': total,
        'coupon_code': data.get('coupon_code', ''),
        'status': 'pending',
        'payment_status': 'pending',
        'notes': data.get('notes', ''),
        'created_at': now_iso(),
        'updated_at': now_iso()
    }
    orders_table.insert(order)

    # Update product stock & sales
    for item in cart_items:
        p = products_table.get(Product.id == item['product_id'])
        if p and item['type'] == 'buy':
            products_table.update({
                'stock': max(0, p['stock'] - item['quantity']),
                'sales_count': p.get('sales_count', 0) + item['quantity']
            }, Product.id == item['product_id'])

    # Update coupon usage
    if data.get('coupon_code'):
        coupons_table.update({'used': coupons_table.get(Coupon.code == data['coupon_code']).get('used', 0) + 1},
                             Coupon.code == data['coupon_code'])

    # Clear cart
    cart_table.remove(Cart.user_id == uid)

    return jsonify(order=order, msg='Order placed successfully'), 201

# ════════════════════════════════════════════════════════════════════════════
#  RENTALS ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/rentals', methods=['GET'])
@jwt_required()
def get_rentals():
    uid = get_jwt_identity()
    rentals = rentals_table.search(Rental.user_id == uid)
    return jsonify(rentals=rentals)

# ════════════════════════════════════════════════════════════════════════════
#  REVIEWS ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/products/<pid>/reviews', methods=['GET'])
def get_reviews(pid):
    rvs = reviews_table.search(Review.product_id == pid)
    return jsonify(reviews=rvs)

@app.route('/api/products/<pid>/reviews', methods=['POST'])
@jwt_required()
def add_review(pid):
    uid = get_jwt_identity()
    data = request.get_json()
    user = users_table.get(User.id == uid)
    rid = str(uuid.uuid4())
    review = {
        'id': rid, 'product_id': pid, 'user_id': uid,
        'user_name': user['name'], 'user_avatar': user.get('avatar',''),
        'rating': data.get('rating', 5), 'title': data.get('title',''),
        'body': data.get('body',''), 'created_at': now_iso()
    }
    reviews_table.insert(review)
    # Update product rating
    all_reviews = reviews_table.search(Review.product_id == pid)
    avg = sum(r['rating'] for r in all_reviews) / len(all_reviews)
    products_table.update({'rating': round(avg, 1), 'reviews_count': len(all_reviews)}, Product.id == pid)
    return jsonify(review=review), 201

# ════════════════════════════════════════════════════════════════════════════
#  WISHLIST ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/wishlist', methods=['GET'])
@jwt_required()
def get_wishlist():
    uid = get_jwt_identity()
    items = wishlist_table.search(Wish.user_id == uid)
    enriched = []
    for item in items:
        p = products_table.get(Product.id == item['product_id'])
        if p: enriched.append({**item, 'product': p})
    return jsonify(wishlist=enriched)

@app.route('/api/wishlist', methods=['POST'])
@jwt_required()
def toggle_wishlist():
    uid = get_jwt_identity()
    pid = request.get_json().get('product_id')
    existing = wishlist_table.get((Wish.user_id == uid) & (Wish.product_id == pid))
    if existing:
        wishlist_table.remove(Wish.id == existing['id'])
        return jsonify(msg='Removed', added=False)
    else:
        wishlist_table.insert({'id': str(uuid.uuid4()), 'user_id': uid, 'product_id': pid, 'added_at': now_iso()})
        return jsonify(msg='Added', added=True)

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN DASHBOARD ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    all_orders = orders_table.all()
    all_products = products_table.search(Product.is_active == True)
    all_users = users_table.search(User.role == 'customer')

    revenue = sum(o['total'] for o in all_orders if o.get('payment_status') == 'paid')
    pending_orders = len([o for o in all_orders if o['status'] == 'pending'])
    low_stock = [p for p in all_products if p.get('stock', 0) < 3]

    # Revenue by month (last 6 months)
    monthly = {}
    for o in all_orders:
        m = o['created_at'][:7]
        monthly[m] = monthly.get(m, 0) + o['total']

    return jsonify({
        'total_revenue': round(revenue, 2),
        'total_orders': len(all_orders),
        'total_products': len(all_products),
        'total_customers': len(all_users),
        'pending_orders': pending_orders,
        'low_stock_count': len(low_stock),
        'monthly_revenue': monthly,
        'recent_orders': sorted(all_orders, key=lambda x: x['created_at'], reverse=True)[:10],
        'low_stock_products': low_stock[:5]
    })

@app.route('/api/admin/orders', methods=['GET'])
@admin_required
def admin_orders():
    orders = orders_table.all()
    status = request.args.get('status')
    if status: orders = [o for o in orders if o['status'] == status]
    orders.sort(key=lambda x: x['created_at'], reverse=True)
    page = int(request.args.get('page', 1))
    return jsonify(paginate(orders, page, 20))

@app.route('/api/admin/orders/<oid>', methods=['PUT'])
@admin_required
def update_order(oid):
    data = request.get_json()
    data['updated_at'] = now_iso()
    orders_table.update(data, Order.id == oid)
    return jsonify(msg='Order updated')

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users():
    users = users_table.all()
    for u in users: u.pop('password', None)
    page = int(request.args.get('page', 1))
    return jsonify(paginate(users, page, 20))

@app.route('/api/admin/coupons', methods=['GET'])
@admin_required
def admin_coupons():
    return jsonify(coupons=coupons_table.all())

@app.route('/api/admin/coupons', methods=['POST'])
@admin_required
def create_coupon():
    data = request.get_json()
    data['id'] = str(uuid.uuid4())
    data['used'] = 0
    data['is_active'] = True
    coupons_table.insert(data)
    return jsonify(msg='Coupon created', id=data['id']), 201

@app.route('/api/admin/coupons/<cid>', methods=['DELETE'])
@admin_required
def delete_coupon(cid):
    coupons_table.update({'is_active': False}, Coupon.id == cid)
    return jsonify(msg='Deleted')

# ════════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify(status='ok', version='1.0.0', timestamp=now_iso())

# ════════════════════════════════════════════════════════════════════════════
#  STATIC FILES & FRONTEND ROUTES
# ════════════════════════════════════════════════════════════════════════════
@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/checkout')
def checkout():
    return send_from_directory('../frontend', 'checkout.html')

@app.route('/orders')
def orders():
    return send_from_directory('../frontend', 'orders.html')

@app.route('/shop')
def shop():
    return send_from_directory('../frontend', 'shop.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('../frontend', filename)

if __name__ == '__main__':
    seed_database()
    app.run(debug=True, port=5000)