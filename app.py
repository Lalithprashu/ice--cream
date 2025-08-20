from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, current_app, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import os
import stripe
from werkzeug.utils import secure_filename
from models import db, User, Product, Order, OrderItem, Address
from config import Config
from flask_wtf.csrf import CSRFProtect

stripe.api_key = Config.STRIPE_SECRET_KEY
from forms import LoginForm, RegisterForm, ProductForm, EditProfileForm, AddressForm
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, FloatField, IntegerField, SelectField, FileField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ice_cream.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD', 'your-app-password')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_USER', 'your-email@gmail.com')

# Initialize Flask-Mail
mail = Mail(app)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize cart in session
@app.before_request
def initialize_cart():
    if 'cart' not in session:
        session['cart'] = {}

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create database tables
with app.app_context():
    db.create_all()
    # Create admin user if it doesn't exist
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

# Admin login form
class AdminLoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin login route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.is_admin and user.check_password(form.password.data):
            login_user(user)
            flash('Welcome back, Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('admin/login.html', form=form)

# Admin logout route
@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login'))

# Routes
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('home.html', products=products)

@app.route('/cart')
def cart():
    cart_items = []
    total = 0
    if 'cart' in session:
        for cart_key, cart_item in session['cart'].items():
            product_id = cart_item['product_id']
            product = Product.query.get(int(product_id))
            if product:
                quantity = cart_item['quantity']
                price = cart_item['price']
                item_total = price * quantity
                cart_item_data = {
                    'id': product.id,
                    'name': product.name,
                    'price': price,
                    'quantity': quantity,
                    'total': item_total
                }
                
                # Add customization info if present
                if 'customization' in cart_item:
                    customization = cart_item['customization']
                    cart_item_data['customization'] = customization
                    
                    # Get topping names if topping_ids are present
                    if 'topping_ids' in customization and customization['topping_ids']:
                        toppings = Topping.query.filter(Topping.id.in_(customization['topping_ids'])).all()
                        cart_item_data['customization']['toppings'] = [{'id': t.id, 'name': t.name} for t in toppings]
                
                # Add customization info if present
                if 'customization' in cart_item:
                    cart_item_data['customization'] = cart_item['customization']
                
                cart_items.append(cart_item_data)
                total += item_total
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered. Please use a different email or login.', 'danger')
            return render_template('register.html', form=form)
            
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Admin routes
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    products = Product.query.all()
    return render_template('admin/dashboard.html', products=products)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        image_url = save_image(form.image.data)
        if not image_url:
            flash('Invalid image file.', 'danger')
            return render_template('admin/add_product.html', form=form)
            
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            image_url=image_url,
            category=form.category.data,
            stock=form.stock.data
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/add_product.html', form=form)

@app.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        if form.image.data:
            # Delete old image if it exists
            if product.image_url and product.image_url.startswith('/static/uploads/'):
                old_image_path = os.path.join(app.root_path, product.image_url.lstrip('/'))
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            # Save new image
            image_url = save_image(form.image.data)
            if not image_url:
                flash('Invalid image file.', 'danger')
                return render_template('admin/edit_product.html', form=form, product=product)
            product.image_url = image_url
            
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.category = form.category.data
        product.stock = form.stock.data
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/edit_product.html', form=form, product=product)

@app.route('/admin/product/delete/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    
    # Delete product image if it exists
    if product.image_url and product.image_url.startswith('/static/uploads/'):
        image_path = os.path.join(app.root_path, product.image_url.lstrip('/'))
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.session.delete(product)
    db.session.commit()
    
    if request.is_json:
        return jsonify({'status': 'success', 'message': 'Product deleted successfully'})
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# API routes
@app.route('/api/ice-creams')
def get_ice_creams():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'image': p.image_url,
        'category': p.category,
        'stock': p.stock
    } for p in products])

@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.json
    return jsonify({
        'status': 'success',
        'message': 'Thank you for your message! We will get back to you soon.',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def save_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to filename to make it unique
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return f"/static/uploads/{filename}"
    return None

# Cart routes
@app.route('/api/cart/add', methods=['GET', 'POST'])
@login_required
def add_to_cart():
    if request.method == 'GET':
        product_id = request.args.get('product_id')
        if not product_id:
            flash('Product ID is required', 'error')
            return redirect(url_for('index'))
        quantity = 1
        data = None
    else:
        data = request.json
        if not data:
            product_id = request.form.get('product_id')
            quantity = int(request.form.get('quantity', 1))
        else:
            product_id = data.get('product_id')
            quantity = data.get('quantity', 1)
    
    product = Product.query.get_or_404(product_id)
    if product.stock < quantity:
        return jsonify({
            'status': 'error',
            'message': 'Not enough stock available'
        }), 400
    
    # Handle customization data if present
    size = data.get('size')
    container = data.get('container')
    topping_ids = data.get('toppings', [])
    extra_notes = data.get('extra_notes', '')
    
    # Calculate total price
    total_price = product.price
    
    # Add size price if customized
    if size:
        size_prices = {
            'small': 0,
            'medium': 20,
            'large': 40
        }
        total_price += size_prices.get(size, 0)
    
    # Add toppings price if any
    if topping_ids:
        toppings = Topping.query.filter(Topping.id.in_(topping_ids)).all()
        for topping in toppings:
            total_price += topping.price
    
    cart = session.get('cart', {})
    cart_item = {
        'product_id': product_id,
        'quantity': quantity,
        'price': total_price
    }
    
    # Add customization if present
    if size or container or topping_ids or extra_notes:
        cart_item['customization'] = {
            'size': size,
            'container': container,
            'topping_ids': topping_ids,
            'extra_notes': extra_notes
        }
    
    # Generate unique key for cart item
    import json
    cart_key = f"{product_id}_{json.dumps(cart_item.get('customization', {}))}"
    
    if cart_key in cart:
        cart[cart_key]['quantity'] += quantity
    else:
        cart[cart_key] = cart_item
    session['cart'] = cart
    
    return jsonify({
        'status': 'success',
        'message': 'Item added to cart successfully'
    })

@app.route('/api/cart/items')
@login_required
def get_cart_items():
    cart = session.get('cart', {})
    items = []
    total = 0
    
    for cart_key, cart_item in cart.items():
        product_id = cart_item['product_id']
        product = Product.query.get(int(product_id))
        if product:
            quantity = cart_item['quantity']
            price = cart_item['price']
            item_total = price * quantity
            item_data = {
                'id': product.id,
                'name': product.name,
                'price': price,
                'quantity': quantity,
                'total': item_total
            }
            
            # Add customization info if present
            if 'customization' in cart_item:
                item_data['customization'] = cart_item['customization']
            
            items.append(item_data)
            total += item_total
    
    return jsonify({
        'items': items,
        'total': total
    })

@app.route('/api/cart/remove', methods=['POST'])
@login_required
def remove_from_cart():
    data = request.json
    product_id = data.get('product_id')
    
    cart = session.get('cart', {})
    # Find the cart key that matches the product_id
    cart_key_to_remove = None
    for cart_key, cart_item in cart.items():
        if int(cart_item['product_id']) == int(product_id):
            cart_key_to_remove = cart_key
            break
    
    if cart_key_to_remove:
        del cart[cart_key_to_remove]
        session['cart'] = cart
        session.modified = True
        return jsonify({
            'status': 'success',
            'message': 'Item removed from cart successfully'
        })
    
    return jsonify({
        'status': 'error',
        'message': 'Item not found in cart'
    }), 404

@app.route('/checkout')
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('index'))
    
    items = []
    total = 0
    
    for cart_key, cart_item in cart.items():
        product_id = cart_item['product_id']
        product = Product.query.get(int(product_id))
        if product:
            quantity = cart_item['quantity']
            price = cart_item['price']
            item_total = price * quantity
            items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
            total += item_total
    
    return render_template('checkout.html', items=items, total=total)

@app.route('/process_checkout', methods=['POST'])
@login_required
def process_checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('index'))
    
    # Get delivery option
    delivery_option = request.form.get('delivery_option', 'pickup')
    session['delivery_option'] = delivery_option
    
    if delivery_option == 'delivery':
        # Redirect to address form if delivery is selected
        return redirect(url_for('delivery_address'))
    else:
        # Skip address form for pickup
        return redirect(url_for('payment'))

@app.route('/delivery-address', methods=['GET', 'POST'])
@login_required
def delivery_address():
    # Check if user has default address
    default_address = Address.query.filter_by(user_id=current_user.id, is_default=True).first()
    
    # If user has addresses, show them for selection
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    
    if request.method == 'POST':
        # Handle address selection or create new
        address_id = request.form.get('address_id')
        
        if address_id == 'new':
            # Redirect to new address form
            return redirect(url_for('new_address'))
        
        # Store selected address in session
        session['address_id'] = address_id
        return redirect(url_for('payment'))
    
    return render_template('delivery_address.html', addresses=addresses, default_address=default_address)

@app.route('/new-address', methods=['GET', 'POST'])
@login_required
def new_address():
    form = AddressForm()
    return render_template('address_form.html', form=form)

@app.route('/save-address', methods=['POST'])
@login_required
def save_address():
    form = AddressForm()
    
    if form.validate_on_submit():
        # Create new address
        address = Address(
            user_id=current_user.id,
            street=form.street.data,
            city=form.city.data,
            state=form.state.data,
            postal_code=form.postal_code.data,
            country=form.country.data,
            phone=form.phone.data,
            is_default=form.is_default.data
        )
        
        # If this is set as default, unset any existing default
        if form.is_default.data:
            existing_default = Address.query.filter_by(user_id=current_user.id, is_default=True).first()
            if existing_default:
                existing_default.is_default = False
        
        db.session.add(address)
        db.session.commit()
        
        # Store address ID in session
        session['address_id'] = address.id
        
        flash('Address saved successfully!', 'success')
        return redirect(url_for('payment'))
    
    return render_template('address_form.html', form=form)

@app.route('/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    try:
        cart = session.get('cart', {})
        if not cart:
            return jsonify({'error': 'Cart is empty'}), 400

        total = 0
        for product_id, quantity in cart.items():
            product = Product.query.get(product_id)
            if product:
                total += product.price * quantity

        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=int(total * 100),  # Convert to cents
            currency='inr',
            metadata={'integration_check': 'accept_a_payment'}
        )

        return jsonify({
            'clientSecret': intent.client_secret,
            'amount': total
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 403

@app.route('/payment')
@login_required
def payment():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))
    
    # Get items and calculate total
    items = []
    total = 0
    
    for cart_key, cart_item in cart.items():
        product_id = cart_item['product_id'] if isinstance(cart_item, dict) and 'product_id' in cart_item else cart_key.split('_')[0] if '_' in str(cart_key) else cart_key
        quantity = cart_item['quantity'] if isinstance(cart_item, dict) and 'quantity' in cart_item else cart_item
        product = Product.query.get(int(product_id))
        if product:
            price = cart_item['price'] if isinstance(cart_item, dict) and 'price' in cart_item else product.price
            item_total = price * quantity
            items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
            total += item_total
    
    # Get delivery address if delivery option is selected
    address = None
    if session.get('delivery_option') == 'delivery' and session.get('address_id'):
        address = Address.query.get(session.get('address_id'))

    return render_template('payment.html', 
                          stripe_public_key=Config.STRIPE_PUBLIC_KEY,
                          total=total,
                          items=items,
                          address=address)

@app.route('/payment/success')
@login_required
def payment_success():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('index'))
    
    # Create order
    order = Order(
        user_id=current_user.id,
        status='completed',
        total_amount=0
    )
    
    # Add delivery address if delivery option was selected
    if session.get('delivery_option') == 'delivery' and session.get('address_id'):
        order.address_id = session.get('address_id')
    
    db.session.add(order)
    db.session.flush()  # Get the order ID without committing
    
    # Add order items and update stock
    total = 0
    for cart_key, cart_item in cart.items():
        # Extract product_id from cart_key or use the product_id from cart_item
        if isinstance(cart_item, dict) and 'product_id' in cart_item:
            # If cart_item has product_id field, use it
            product_id = cart_item['product_id']
            quantity = cart_item['quantity']
        else:
            # If cart_key is in format "product_id_customization_json"
            if '_' in str(cart_key):
                product_id = cart_key.split('_')[0]
            else:
                product_id = cart_key
            quantity = cart_item
            
        product = Product.query.get(int(product_id))
        if product and product.stock >= quantity:
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price=product.price
            )
            db.session.add(order_item)
            
            # Update stock
            product.stock -= quantity
            
            total += product.price * quantity
    
    order.total_amount = total
    db.session.commit()
    
    # Clear cart
    session.pop('cart', None)
    
    flash('Payment successful! Your order has been placed.', 'success')
    return redirect(url_for('order_confirmation', order_id=order.id))

@app.route('/payment/cancel')
@login_required
def payment_cancel():
    flash('Payment was cancelled.', 'info')
    return redirect(url_for('cart'))

@app.route('/place-order', methods=['POST'])
@login_required
def place_order():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('index'))
    
    # Create order
    order = Order(
        user_id=current_user.id,
        status='pending',
        total_amount=0
    )
    
    # Add delivery address if delivery option was selected
    if session.get('delivery_option') == 'delivery' and session.get('address_id'):
        order.address_id = session.get('address_id')
    
    db.session.add(order)
    
    # Add order items and update stock
    total = 0
    for cart_key, cart_item in cart.items():
        # Extract product_id from cart_key or use the product_id from cart_item
        if isinstance(cart_item, dict) and 'product_id' in cart_item:
            # If cart_item has product_id field, use it
            product_id = cart_item['product_id']
            quantity = cart_item['quantity']
        else:
            # If cart_key is in format "product_id_customization_json"
            if '_' in str(cart_key):
                product_id = cart_key.split('_')[0]
            else:
                product_id = cart_key
            quantity = cart_item
            
        product = Product.query.get(int(product_id))
        if product and product.stock >= quantity:
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price=product.price
            )
            db.session.add(order_item)
            
            # Update stock
            product.stock -= quantity
            
            total += product.price * quantity
    
    order.total_amount = total
    db.session.commit()
    
    # Clear cart
    session.pop('cart', None)
    
    flash('Order placed successfully!', 'success')
    return redirect(url_for('order_confirmation', order_id=order.id))

@app.route('/order-confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    return render_template('order_confirmation.html', order=order)

# New models for customization
class Topping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200))
    description = db.Column(db.Text)

class Customization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_item.id'), nullable=False)
    size = db.Column(db.String(20), nullable=False)  # small, medium, large
    container = db.Column(db.String(20), nullable=False)  # cone, cup
    toppings = db.relationship('Topping', secondary='customization_toppings')
    extra_notes = db.Column(db.Text)

# Association table for customization toppings
customization_toppings = db.Table('customization_toppings',
    db.Column('customization_id', db.Integer, db.ForeignKey('customization.id'), primary_key=True),
    db.Column('topping_id', db.Integer, db.ForeignKey('topping.id'), primary_key=True)
)

# New routes for customization
@app.route('/customize/<int:product_id>')
@login_required
def customize_ice_cream(product_id):
    product = Product.query.get_or_404(product_id)
    toppings = Topping.query.all()
    return render_template('customize.html', product=product, toppings=toppings)

@app.route('/api/customize/add', methods=['POST'])
@login_required
def add_customized_item():
    data = request.get_json()
    product_id = data.get('product_id')
    size = data.get('size')
    container = data.get('container')
    topping_ids = data.get('toppings', [])
    extra_notes = data.get('extra_notes', '')

    # Calculate total price
    product = Product.query.get_or_404(product_id)
    base_price = product.price
    
    # Add size price
    size_prices = {
        'small': 0,
        'medium': 20,
        'large': 40
    }
    total_price = base_price + size_prices.get(size, 0)
    
    # Add toppings price
    toppings = Topping.query.filter(Topping.id.in_(topping_ids)).all()
    for topping in toppings:
        total_price += topping.price

    # Create order item
    order_item = OrderItem(
        product_id=product_id,
        quantity=1,
        price=total_price,
        customization=Customization(
            size=size,
            container=container,
            toppings=toppings,
            extra_notes=extra_notes
        )
    )

    # Add to cart
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append({
        'product_id': product_id,
        'quantity': 1,
        'price': total_price,
        'customization': {
            'size': size,
            'container': container,
            'topping_ids': topping_ids,
            'extra_notes': extra_notes
        }
    })
    session.modified = True

    return jsonify({
        'status': 'success',
        'message': 'Customized item added to cart',
        'total_price': total_price
    })

@app.route('/api/toppings')
def get_toppings():
    toppings = Topping.query.all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'price': t.price,
        'image_url': t.image_url,
        'description': t.description
    } for t in toppings])

# Admin routes for managing toppings
@app.route('/admin/toppings')
@login_required
def manage_toppings():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    toppings = Topping.query.all()
    return render_template('admin/toppings.html', toppings=toppings)

@app.route('/admin/topping/add', methods=['GET', 'POST'])
@login_required
def add_topping():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        description = request.form.get('description')
        
        # Handle image upload
        image = request.files.get('image')
        image_url = None
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f'/static/uploads/{filename}'
        
        topping = Topping(
            name=name,
            price=price,
            image_url=image_url,
            description=description
        )
        db.session.add(topping)
        db.session.commit()
        flash('Topping added successfully!', 'success')
        return redirect(url_for('manage_toppings'))
    
    return render_template('admin/add_topping.html')

@app.route('/admin/topping/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_topping(id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    topping = Topping.query.get_or_404(id)
    
    if request.method == 'POST':
        topping.name = request.form.get('name')
        topping.price = float(request.form.get('price'))
        topping.description = request.form.get('description')
        
        # Handle image upload
        image = request.files.get('image')
        if image:
            # Delete old image if exists
            if topping.image_url and topping.image_url.startswith('/static/uploads/'):
                old_image_path = os.path.join(app.root_path, topping.image_url.lstrip('/'))
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            topping.image_url = f'/static/uploads/{filename}'
        
        db.session.commit()
        flash('Topping updated successfully!', 'success')
        return redirect(url_for('manage_toppings'))
    
    return render_template('admin/edit_topping.html', topping=topping)

@app.route('/admin/topping/delete/<int:id>', methods=['POST'])
@login_required
def delete_topping(id):
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    
    topping = Topping.query.get_or_404(id)
    
    # Delete image if exists
    if topping.image_url and topping.image_url.startswith('/static/uploads/'):
        image_path = os.path.join(app.root_path, topping.image_url.lstrip('/'))
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.session.delete(topping)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Topping deleted successfully'})

@app.route('/orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/order/<int:order_id>')
@login_required
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('my_orders'))
    return render_template('order_details.html', order=order)

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    # Get filter parameters
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Start with base query
    query = Order.query
    
    # Apply filters
    if status:
        query = query.filter_by(status=status)
    
    if date_from:
        query = query.filter(Order.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    
    if date_to:
        query = query.filter(Order.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    
    # Get orders
    orders = query.order_by(Order.created_at.desc()).all()
    
    # Get current time for time-in-status calculations
    now = datetime.utcnow()
    
    return render_template('admin/orders.html', orders=orders, now=now)

@app.route('/admin/order/<int:order_id>')
@login_required
@admin_required
def admin_order_details(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_details.html', order=order)

@app.route('/admin/order/update-status/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status in ['pending', 'processing', 'preparing', 'ready', 'delivered', 'cancelled']:
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Order status updated successfully!', 'success')
    return redirect(url_for('admin_order_details', order_id=order_id))

def create_sample_products():
    if Product.query.count() == 0:
        sample_products = [
            Product(
                name='Vanilla Delight',
                description='Classic vanilla ice cream made with Madagascar vanilla beans',
                price=99.99,
                category='classic',
                stock=50,
                image_url='https://images.unsplash.com/photo-1563805042-7684c019e1cb?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'
            ),
            Product(
                name='Chocolate Dream',
                description='Rich and creamy chocolate ice cream with Belgian chocolate',
                price=129.99,
                category='premium',
                stock=40,
                image_url='https://images.unsplash.com/photo-1563805042-7684c019e1cb?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'
            ),
            Product(
                name='Strawberry Sorbet',
                description='Refreshing strawberry sorbet made with fresh strawberries',
                price=119.99,
                category='sorbet',
                stock=30,
                image_url='https://images.unsplash.com/photo-1563805042-7684c019e1cb?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'
            ),
            Product(
                name='Mango Tango',
                description='Tropical mango ice cream with real mango pieces',
                price=139.99,
                category='premium',
                stock=35,
                image_url='https://images.unsplash.com/photo-1563805042-7684c019e1cb?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'
            ),
            Product(
                name='Vegan Coconut',
                description='Creamy coconut ice cream made with coconut milk',
                price=149.99,
                category='vegan',
                stock=25,
                image_url='https://images.unsplash.com/photo-1563805042-7684c019e1cb?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60'
            )
        ]
        for product in sample_products:
            db.session.add(product)
        db.session.commit()

def create_admin_user():
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

@app.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('user_profile.html', orders=orders)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        if form.password.data:
            current_user.set_password(form.password.data)
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('edit_profile.html', form=form)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if it doesn't exist
        create_admin_user()
        # Add sample products if none exist
        if Product.query.count() == 0:
            sample_products = [
                Product(
                    name='Vanilla Delight',
                    description='Classic vanilla ice cream made with Madagascar vanilla beans',
                    price=99.99,
                    image_url='https://images.unsplash.com/photo-1563805042-7684c019e1cb'
                ),
                Product(
                    name='Chocolate Dream',
                    description='Rich chocolate ice cream',
                    price=129.99,
                    image_url='https://images.unsplash.com/photo-1563805042-7684c019e1cb'
                )
            ]
            for product in sample_products:
                db.session.add(product)
            db.session.commit()
    app.run(debug=True)