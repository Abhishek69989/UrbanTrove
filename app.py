from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_session import Session
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yagmail

app = Flask(__name__)
app.secret_key = os.urandom(24) 

DB_HOST = 'localhost'
DB_NAME = 'UrbanTrove'
DB_USER = 'postgres' 
DB_PASSWORD = 'abhishek@sql123' 

def create_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=5432
    )


def create_tables():
    conn = create_connection()
    cursor = conn.cursor()
    
    create_users_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_products_table_query = """
    CREATE TABLE IF NOT EXISTS products (
        id VARCHAR(10) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        image VARCHAR(255) NOT NULL,
        description TEXT
    );
    """
    
    create_cart_table_query = """
    CREATE TABLE IF NOT EXISTS cart (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        product_id VARCHAR(10) REFERENCES products(id),
        quantity INTEGER NOT NULL,
        size VARCHAR(10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT cart_user_id_product_id_size_key UNIQUE (user_id, product_id, size)
    );
    """
    
    cursor.execute(create_users_table_query)
    cursor.execute(create_products_table_query)
    cursor.execute(create_cart_table_query)
    conn.commit()
    cursor.close()
    conn.close()

create_tables()

def is_logged_in():
    return 'email' in session

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shop')
def shop():
    return render_template('shop.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

from flask import jsonify, session, request
from psycopg2.errors import UniqueViolation

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'email' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    product_id = request.json.get('product_id')
    quantity = request.json.get('quantity', 1)
    size = request.json.get('size')
    
    if not all([product_id, quantity, size]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (session['email'],))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()

        if not product:
            return jsonify({"error": "Product not found"}), 404

        cursor.execute("""
            INSERT INTO cart (user_id, product_id, quantity, size)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, product_id, size) DO UPDATE
            SET quantity = cart.quantity + EXCLUDED.quantity
        """, (user[0], product_id, quantity, size))
        conn.commit()
        return jsonify({"message": "Product added to cart successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/cart')
def cart():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    conn = create_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (session['email'],))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("""
                SELECT c.product_id, c.quantity, c.size, p.name, p.price, p.image
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.user_id = %s
            """, (user['id'],))
            cart_items = cursor.fetchall()
        else:
            cart_items = []
        
        return render_template('cart.html', cart_items=cart_items)
    finally:
        cursor.close()
        conn.close()

@app.route('/update_cart', methods=['POST'])
def update_cart():
    if 'email' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    product_id = request.json.get('product_id')
    quantity = request.json.get('quantity')
    size = request.json.get('size')
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (session['email'],))
        user = cursor.fetchone()
        
        if user:
            if quantity > 0:
                cursor.execute("""
                    UPDATE cart SET quantity = %s
                    WHERE user_id = %s AND product_id = %s AND size = %s
                """, (quantity, user[0], product_id, size))
            else:
                cursor.execute("""
                    DELETE FROM cart
                    WHERE user_id = %s AND product_id = %s AND size = %s
                """, (user[0], product_id, size))
            conn.commit()
            return jsonify({"message": "Cart updated"}), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()
    

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'email' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    product_id = request.json.get('product_id')
    size = request.json.get('size')
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (session['email'],))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("""
                DELETE FROM cart
                WHERE user_id = %s AND product_id = %s AND size = %s
            """, (user[0], product_id, size))
            conn.commit()
            return jsonify({"message": "Product removed from cart"}), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/team')
def team():
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE email = %s;", (email,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and check_password_hash(result[0], password):
            session['email'] = email
            flash('Login successful!', 'success')
            return redirect(url_for('index'))

        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['repassword']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        conn = create_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s);",
                           (name, email, generate_password_hash(password)))
            conn.commit()
            flash('Account created successfully! You can log in now.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash('Email already exists. Please log in.', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.pop('email', None) 
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/category1')
def category1():
    return render_template('Category1.html')

@app.route('/category2')
def category2():
    return render_template('Category2.html')

@app.route('/category3')
def category3():
    return render_template('Category3.html')

@app.route('/category4')
def category4():
    return render_template('Category4.html')

@app.route('/category5')
def category5():
    return render_template('Category5.html')


def insert_products_if_not_exist(conn, products):
    cursor = conn.cursor()

    for product_id, product_data in products.items():
        # Check if the product already exists
        cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        if cursor.fetchone() is None:
            # Product doesn't exist, so insert it
            cursor.execute("""
                INSERT INTO products (id, name, price, image, description)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                product_data['id'],
                product_data['name'],
                product_data['price'],
                product_data['image'],
                product_data['description']
            ))
            print(f"Inserted product: {product_id}")
        else:
            print(f"Product {product_id} already exists, skipping.")

    conn.commit()


@app.route('/product')
def product():
    product_id = request.args.get('product') 
    conn = create_connection()
    products = {
        'SP1': {
            'id': 'SP1',
            'name': 'Black AOP', 
            'price': 799, 
            'description': 'Oversized T-Shirt',
            'image': url_for('static', filename='images/Oversized-T-Shirt/01/men-s-black-aop-oversized-t-shirt-425019-1667560056-1.webp'),
            'additional_images': [
                url_for('static', filename='images/Oversized-T-Shirt/01/men-s-black-aop-oversized-t-shirt-425019-1667560061-2.webp'),
                url_for('static', filename='images/Oversized-T-Shirt/01/men-s-black-aop-oversized-t-shirt-425019-1667560066-3.webp'),
                url_for('static', filename='images/Oversized-T-Shirt/01/men-s-black-aop-oversized-t-shirt-425019-1667560082-6.webp')
            ],
            'material': 'Single Jersey, 100% Cotton Classic, lightweight jersey fabric comprising 100% cotton.',
            'care': 'Machine wash.',
            'country_of_origin': 'India',
            'product_details': [
                'Super Loose On Body Thoda Hawa Aane De'
            ],
            'product_description': "Buy Men's Black AOP Oversized T-shirt from UrbanTrove today."
        },
        'SP2': {
            'id': 'SP2',
            'name': 'Black Warriors Graphic Printed', 
            'price': 699, 
            'description': 'Oversized T-Shirt',
            'image': url_for('static', filename='images/Oversized-T-Shirt/02/men-s-black-warriors-graphic-printed-oversized-t-shirt-519149-1679048409-1.webp'),
            'additional_images': [
                url_for('static', filename='images/Oversized-T-Shirt/02/men-s-black-warriors-graphic-printed-oversized-t-shirt-519149-1679048414-2.webp'),
                url_for('static', filename='images/Oversized-T-Shirt/02/men-s-black-warriors-graphic-printed-oversized-t-shirt-519149-1679048419-3.webp'),
                url_for('static', filename='images/Oversized-T-Shirt/02/men-s-black-warriors-graphic-printed-oversized-t-shirt-519149-1679048436-6.webp')
            ],
            'material': 'Single Jersey, 100% Cotton Classic, lightweight jersey fabric comprising 100% cotton.',
            'care': 'Machine Wash',
            'country_of_origin': 'India',
            'product_details': [
                'Super Loose On Body Thoda Hawa Aane De'
            ],
            'product_description': "Shop Men's Black Warriors Graphic Printed Oversized T-shirt from UrbanTrove today."
        },
        'SP3': {
            'id': 'SP3',
            'name': 'Young Forever', 
            'price': 449, 
            'description': 'T-Shirt',
            'image': url_for('static', filename='images/T-Shirt/01/men-s-white-young-forever-t-shirt-277586-1655747977-1.webp'),
            'additional_images': [
                url_for('static', filename='images/T-Shirt/01/men-s-white-young-forever-t-shirt-277586-1655747982-2.webp'),
                url_for('static', filename='images/T-Shirt/01/men-s-white-young-forever-t-shirt-277586-1655747988-3.webp'),
                url_for('static', filename='images/T-Shirt/01/men-s-white-young-forever-t-shirt-277586-1655748004-6.webp')
            ],
            'material': '80% Cotton 20% Polyester ',
            'care': 'Machine wash.',
            'country_of_origin': 'India',
            'product_details': 'Wear your inner spirit with this Young Forever SideHalf Sleeve T-Shirt. Pair this white t-shirt with a pair of cool kicks and corduroys for the perfect millennial look.',
            'product_description': "Shop Men's White Young Forever T-shirt from UrbanTrove today."
        },
        'SP4': {
            'id': 'SP4',
            'name': 'Never Give Up Typography', 
            'price': 645, 
            'description': 'T-Shirt',
            'image': url_for('static', filename='images/Oversized-T-Shirt/08/men-s-black-typography-oversized-t-shirt-590958-1682522365-1.webp'),
            'additional_images': [
                url_for('static', filename='images/Oversized-T-Shirt/08/men-s-black-typography-oversized-t-shirt-590958-1682522370-2.webp'),
                url_for('static', filename='images/Oversized-T-Shirt/08/men-s-black-typography-oversized-t-shirt-590958-1682522381-4.webp'),
                url_for('static', filename='images/Oversized-T-Shirt/08/men-s-black-typography-oversized-t-shirt-590958-1682522386-5.webp')
            ],
            'material': 'Single Jersey, 100% Cotton Classic, lightweight jersey fabric comprising 100% cotton.',
            'care': 'Machine Wash',
            'country_of_origin': 'India',
            'product_details': 'Relaxed fit - Relaxed at Chest and Straight on Waist Down',
            'product_description': 'Shop Mens Black typography Oversized T-shirt from UrbanTrove today.'
        },
        'SP5': {
            'id': 'SP5',
            'name': 'White Panda Camo', 
            'price': 349, 
            'description': 'Fanny Packs',
            'image': url_for('static', filename='images/fanny-bag/03/white-panda-camo-fanny-bag-578614-1680612792-1.webp'),
            'additional_images': [
                url_for('static', filename='images/fanny-bag/03/white-panda-camo-fanny-bag-578614-1680612797-2.webp'),
                url_for('static', filename='images/fanny-bag/03/white-panda-camo-fanny-bag-578614-1680612808-4.webp'),
                url_for('static', filename='images/fanny-bag/03/white-panda-camo-fanny-bag-578614-1680612813-5.webp')
            ],
            'material': 'Premium Heavy Gauge Fabric',
            'care': 'Machine wash.',
            'country_of_origin': 'India',
            'product_details': 'White Panda Camo Fanny Bag',
            'product_description': 'Shop White Panda Camo Fanny Bag from UrbanTrove today.'
        },
        'SP6': {
            'id': 'SP6',
            'name': 'Black Mickey Hyperprint Sling Bag', 
            'price': 699, 
            'description': 'Fanny Packs',
            'image': url_for('static', filename='images/fanny-bag/04/unisex-mickey-hyperprint-sling-bag-578615-1677841916-1.webp'),
            'additional_images': [
                url_for('static', filename='images/fanny-bag/04/unisex-mickey-hyperprint-sling-bag-578615-1677841922-2.webp'),
                url_for('static', filename='images/fanny-bag/04/unisex-mickey-hyperprint-sling-bag-578615-1677841932-4.webp'),
                url_for('static', filename='images/fanny-bag/04/unisex-mickey-hyperprint-sling-bag-578615-1677841943-6.webp')
            ],
            'material': '80% Cotton 20% Polyester ',
            'care': 'Machine wash.',
            'country_of_origin': 'India',
            'product_details': 'Unisex Black Mickey Hyperprint Sling Bag',
            'product_description': 'Shop Unisex Black Mickey Hyperprint Sling Bag from UrbanTrove today.'
        },
        'SP7': {
            'id': 'SP7',
            'name': "Men's Black Denims", 
            'price': 799, 
            'description': 'Jeans',
            'image': url_for('static', filename='images/jean/04/black-denim-jeans-479358-1680593113-1.webp'),
            'additional_images': [
                url_for('static', filename='images/jean/04/black-denim-jeans-479358-1680593119-2.webp'),
                url_for('static', filename='images/jean/04/black-denim-jeans-479358-1680593124-3.webp'),
                url_for('static', filename='images/jean/04/black-denim-jeans-479358-1680593135-5.webp')
            ],
            'material': 'Denim soft and breathable for maximum comfort. ',
            'care': 'Machine wash.',
            'country_of_origin': 'India',
            'product_details': 'Regular fit - Fits just right - not too tight, not too loose.',
            'product_description': "Shop Men's Black Denim Jeans UrbanTrove today."
        },
        'SP8': {
            'id': 'SP8',
            'name': 'Naruto: Signature', 
            'price': 1999, 
            'description': 'Shoes',
            'image': url_for('static', filename='images/Shoe/Naruto Signature/1676016585_3411903.webp'),
            'additional_images': [
                url_for('static', filename='images/Shoe/Naruto Signature/1676016598_1028925.webp'),
                url_for('static', filename='images/Shoe/Naruto Signature/1676016610_6337884.webp'),
                url_for('static', filename='images/Shoe/Naruto Signature/1676016622_6838454.webp')
            ],
            'material': 'Upper material is made of Suede Leather that is comfortable, lightweight, easy to clean, and can be paired with a wide range of outfits.',
            'care': 'Care: Spot wash with mild soap using a soft clean cloth. Air Dry (do not twist the shoes, avoid tumble dry).',
            'country_of_origin': 'India',
            'product_details': 'Cushioned insole with soft breathable lining.',
            'product_description': "Shop for Naruto Signature Men's Low Top Sneakers at The UrbanTrove Store."
        },
        'SP9': {
            'id': 'SP9',
            'name': 'Punisher: Logo (Glow In The Dark)', 
            'price': 1999, 
            'description': 'Shoes',
            'image': url_for('static', filename='images/Shoe/Punisher Logo (Glow In The Dark)/1678380121_2310053.webp'),
            'additional_images': [
                url_for('static', filename='images/Shoe/Punisher Logo (Glow In The Dark)/1678380121_3509399.webp'),
                url_for('static', filename='images/Shoe/Punisher Logo (Glow In The Dark)/1678380121_3759987.webp'),
                url_for('static', filename='images/Shoe/Punisher Logo (Glow In The Dark)/1678380121_8506768.webp')
            ],
            'material': 'Upper material is made of PU that is comfortable, lightweight, easy to clean, and can be paired with a wide range of outfits.',
            'care': 'Care: Spot wash with mild soap using a soft clean cloth. Air Dry (do not twist the shoes, avoid tumble dry).',
            'country_of_origin': 'India',
            'product_details': 'Cushioned insole with soft breathable lining.',
            'product_description': "Shop for the official licensed Punisher Logo Glow In The Dark low top sneakers for men at The UrbanTrove Store."
        },
        'SP10': {
            'id': 'SP10',
            'name': 'White Batman Dripping Logo', 
            'price': 399, 
            'description': 'Sliders',
            'image': url_for('static', filename="images/sliders/02-Men's White Batman Dripping Logo Printed Velcro Sliders/men-s-white-batman-dripping-logo-printed-velcro-sliders-579923-1680613370-1.webp"),
            'additional_images': [
                url_for('static', filename="images/sliders/02-Men's White Batman Dripping Logo Printed Velcro Sliders/men-s-white-batman-dripping-logo-printed-velcro-sliders-579923-1680613376-2.webp"),
                url_for('static', filename="images/sliders/02-Men's White Batman Dripping Logo Printed Velcro Sliders/men-s-white-batman-dripping-logo-printed-velcro-sliders-579923-1680613386-4.webp"),
                url_for('static', filename="images/sliders/02-Men's White Batman Dripping Logo Printed Velcro Sliders/men-s-white-batman-dripping-logo-printed-velcro-sliders-579923-1680613391-5.webp")
            ],
            'material': 'Velcro',
            'care': 'Spot wash with mild soap using a soft clean cloth. Air Dry.',
            'country_of_origin': 'India',
            'product_details': "Men's White Batman Dripping Logo Printed Velcro Sliders",
            'product_description': 'Shop for White Batman Dripping Logo Sliders at The UrbanTrove Store.'
        },
        'SP11': {
            'id': 'SP11',
            'name': 'Black Ironman Printed Adjustable Strap', 
            'price': 499, 
            'description': 'Sliders',
            'image': url_for('static', filename="images/sliders/04-Men's Black Ironman Printed Adjustable Strap Comfysole Sliders/ironman-comfysole-mens-sliders-537396-1663218816-1.webp"),
            'additional_images': [
                url_for('static', filename="images/sliders/04-Men's Black Ironman Printed Adjustable Strap Comfysole Sliders/ironman-comfysole-mens-sliders-537396-1663218822-2.webp"),
                url_for('static', filename="images/sliders/04-Men's Black Ironman Printed Adjustable Strap Comfysole Sliders/ironman-comfysole-mens-sliders-537396-1663218837-5.webp"),
                url_for('static', filename="images/sliders/04-Men's Black Ironman Printed Adjustable Strap Comfysole Sliders/ironman-comfysole-mens-sliders-537396-1663218842-6.webp")
            ],
            'material': 'Velcro',
            'care': 'Spot wash with mild soap using a soft clean cloth. Air Dry.',
            'country_of_origin': 'India',
            'product_details': 'Black Ironman Printed Adjustable Strap Comfysole Sliders',
            'product_description': 'Shop for Black Ironman Printed Adjustable Strap Comfysole Sliders at The UrbanTrove Store.'
        },
        'SP12': {
            'id': 'SP12',
            'name': 'Lost Mountains Graphic Printed', 
            'price': 449, 
            'description': 'T-Shirt',
            'image': url_for('static', filename='images/T-Shirt/02/lost-mountains-half-sleeve-t-shirt-272010-1655748131-1.webp'),
            'additional_images': [
                url_for('static', filename='images/T-Shirt/02/lost-mountains-half-sleeve-t-shirt-272010-1655748137-2.webp'),
                url_for('static', filename='images/T-Shirt/02/lost-mountains-half-sleeve-t-shirt-272010-1655748142-3.webp'),
                url_for('static', filename='images/T-Shirt/02/lost-mountains-half-sleeve-t-shirt-272010-1655748147-4.webp')
            ],
            'material': 'Single Jersey, 100% Cotton Classic, lightweight jersey fabric comprising 100% cotton.',
            'care': 'Machine wash.',
            'country_of_origin': 'India',
            'product_details': 'Regular fit - Fitted at Chest and Straight on Waist Down',
            'product_description': 'Shop Lost Mountains Graphic Printed T-shirt from UrbanTrove today.'
        }
    }

    insert_products_if_not_exist(conn, products)
    conn.close()

    

    product = products.get(product_id)
    if product:
        return render_template('product.html', product=product)
    else:
        return "Product not found", 404
    

def send_confirmation_email(to_email, order_details):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    sender_email = "urbantrove.orders@gmail.com"
    app_password = "ecrl zmru tvng pyoj"

    message = MIMEMultipart("alternative")
    message["Subject"] = "Order Confirmation - UrbanTrove"
    message["From"] = sender_email
    message["To"] = to_email
    subject = "Order Confirmation - UrbanTrove"

    order_details_html = order_details.replace('\n', '<br>')

    html_content = f"""
    <!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Confirmation</title>
</head>
<body style="font-family: 'Poppins', sans-serif; background-color: #e3e6f2; color: #1d3557; max-width: 700px; margin: 0 auto; padding: 20px; line-height: 1.6;">

    <!-- Header Section -->
    <div style="background-color: #1d3557; color: #e3e6f2; text-align: center; padding: 25px 20px; border-radius: 8px 8px 0 0;">
        <h1 style="font-weight: 600; margin: 0; font-size: 24px;">Thank You for Your Order!</h1>
    </div>

    <!-- Order Details Section -->
    <div style="background-color: #ffffff; padding: 25px; border-radius: 0 0 8px 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 15px;">
        <p style="font-size: 16px; margin: 0;">Dear Valued Customer,</p>
        <p style="font-size: 16px; margin: 15px 0;">We’re excited to confirm that your order has been received and is being processed. Here are the details of your purchase:</p>

        <div style="background-color: #f0f4f8; border: 1px solid #a8dadc; padding: 20px; margin-top: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2 style="color: #1d3557; font-size: 20px; margin: 0 0 10px 0; font-weight: 500;">Order Details:</h2>
            {order_details_html}
        </div>

        <p style="font-size: 16px; margin: 15px 0;">We’re working hard to get your items to you as quickly as possible. You’ll receive another email with tracking information once your order has been shipped.</p>

        <a href="#" style="display: inline-block; background-color: #457b9d; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500; margin-top: 20px;">Track Your Order</a>

        <p style="font-size: 16px; margin: 15px 0;">If you have any questions or concerns about your order, please don’t hesitate to contact our customer service team.</p>

        <p style="font-size: 16px; margin: 0;">Thank you for choosing UrbanTrove. We appreciate your business!</p>

        <p style="font-size: 16px; margin: 15px 0 0 0;">Best regards,<br><strong>The UrbanTrove Team</strong></p>
    </div>

    <!-- Footer Section -->
    <div style="text-align: center; margin-top: 20px; font-size: 14px; color: #1d3557;">
        <p style="margin: 0;">© 2024 UrbanTrove. All rights reserved.</p>
        <p style="margin: 5px 0;">Amrita Vishwa Vidyapeetham, Coimbatore</p>
    </div>

</body>
</html>

    """

    try:
        yag = yagmail.SMTP(sender_email, app_password)
        yag.send(
            to=to_email,
            subject=subject,
            contents=[html_content],
            prettify_html=False
        )
        print("Email sent successfully")
    except Exception as e:
        print(f"Error sending email: {e}")


@app.route('/process_order', methods=['POST'])
def process_order():
    if 'email' not in session:
        return jsonify({"error": "User not logged in"}), 401

    conn = create_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("SELECT id, email FROM users WHERE email = %s", (session['email'],))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        cursor.execute("""
            SELECT c.product_id, c.quantity, c.size, p.name, p.price
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """, (user['id'],))
        cart_items = cursor.fetchall()

        if not cart_items:
            return jsonify({"error": "Cart is empty"}), 400

        total_amount = sum(item['price'] * item['quantity'] for item in cart_items)

        order_details = "\n".join([f"{item['name']} - Size: {item['size']}, Quantity: {item['quantity']}, Price: ₹{item['price']}" for item in cart_items])
        order_details += f"\n\nTotal Amount: ₹{total_amount}"

        cursor.execute("DELETE FROM cart WHERE user_id = %s", (user['id'],))

        send_confirmation_email(user['email'], order_details)

        conn.commit()
        return jsonify({"message": "Order placed successfully"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)
