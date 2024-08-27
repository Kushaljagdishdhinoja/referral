from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import jwt
import datetime
import os
import pandas as pd
from io import BytesIO


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['STATIC_FOLDER'] = 'static'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
CORS(app)

SECRET_KEY = 'your_secret_key_here'  # Replace with a strong secret key

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    referrals = db.relationship('Referral', backref='referrer', lazy=True)

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_phone = db.Column(db.String(20), nullable=False)
    purchased = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(10), nullable=False)  # New field for "Buy" or "Sell"
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)  # New field for timestamp


def generate_referral_code():
    return os.urandom(4).hex().upper()

def create_token(user_id):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(days=90)
    token = jwt.encode({'user_id': user_id, 'exp': expiration}, SECRET_KEY, algorithm='HS256')
    return token

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    
    if not phone or not password:
        return jsonify({"message": "Phone and password are required."}), 400

    user = User.query.filter_by(phone=phone).first()
    if user:
        return jsonify({"message": "User already exists."}), 400  # User exists

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    referral_code = generate_referral_code()

    user = User(phone=phone, password=hashed_password, referral_code=referral_code)
    db.session.add(user)
    db.session.commit()

    token = create_token(user.id)
    return jsonify({
        "message": "Signup successful.",
        "id": user.id,
        "phone": user.phone,
        "referral_code": user.referral_code,
        "token": token
    })

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')

    if not phone or not password:
        return jsonify({"message": "Phone and password are required."}), 400

    user = User.query.filter_by(phone=phone).first()
    if user and bcrypt.check_password_hash(user.password, password):
        token = create_token(user.id)
        return jsonify({"id": user.id, "phone": user.phone, "referral_code": user.referral_code, "token": token})
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/protected', methods=['GET'])
def protected():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"message": "Token is missing!"}), 403
    
    user_id = verify_token(token)
    if not user_id:
        return jsonify({"message": "Token is invalid or expired!"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found!"}), 404
    
    # Get the referrals
    referrals = Referral.query.filter_by(referrer_id=user.id).all()
    referral_list = [
        {
            "referred_phone": referral.referred_phone,
            "purchased": referral.purchased,
            "type": referral.type  # Include the 'type' field
        }
        for referral in referrals
    ]
    
    return jsonify({
        "id": user.id,
        "phone": user.phone,
        "referral_code": user.referral_code,
        "referrals": referral_list
    })


@app.route('/send_referral', methods=['POST'])
def send_referral():
    data = request.json
    referred_phone = data.get('referred_phone')
    referral_type = data.get('referral_type')  # New field to capture "Buy" or "Sell"
    referrer_id = verify_token(request.headers.get('Authorization'))

    if not referred_phone or not referral_type or not referrer_id:
        return jsonify({"message": "Referred phone number, referral type, and valid token are required."}), 400

    # Check if the referral already exists for this referrer
    existing_referral = Referral.query.filter_by(referrer_id=referrer_id, referred_phone=referred_phone).first()
    if existing_referral:
        return jsonify({"message": "Referral already exists for this phone number."}), 400

    # Check if the referred phone number is already associated with another referrer
    existing_referred = Referral.query.filter_by(referred_phone=referred_phone).first()
    if existing_referred:
        return jsonify({"message": "This phone number has already been referred by someone else."}), 400

    # Create a new referral with the referral type and timestamp
    referral = Referral(
        referrer_id=referrer_id,
        referred_phone=referred_phone,
        type=referral_type,  # Save the "Buy" or "Sell" type
        timestamp=datetime.datetime.utcnow()  # Set the current timestamp
    )
    db.session.add(referral)
    db.session.commit()

    # # Generate WhatsApp link (optional)
    referrer = User.query.get(referrer_id)
    referral_link = f"-"

    return jsonify({"message": "Referral sent.", "referral_link": referral_link})




@app.route('/update_purchases', methods=['POST'])
def update_purchases():
    data = request.json
    print(data)
    phone_numbers_str = data.get('phone_numbers')

    if not phone_numbers_str:
        return jsonify({"message": "Phone numbers are required."}), 400

    phone_numbers = [phone.strip() for phone in phone_numbers_str.split(',')]
    referrals = Referral.query.filter(Referral.referred_phone.in_(phone_numbers)).all()

    for referral in referrals:
        referral.purchased = True

    db.session.commit()

    return jsonify({"message": "Purchase status updated for referred customers."})


@app.route('/logout', methods=['POST'])
def logout():
    # The token will be cleared on the client-side. No server-side action needed.
    return jsonify({"message": "Logged out successfully."})

@app.route('/download_db', methods=['GET'])
def download_db():
    # Query all users and referrals from the database
    users = User.query.all()
    referrals = Referral.query.all()

    # Create DataFrames from the query results
    users_data = {
        'ID': [user.id for user in users],
        'Phone': [user.phone for user in users],
        'Referral Code': [user.referral_code for user in users],
    }

    referrals_data = {
        'ID': [referral.id for referral in referrals],
        'Referrer ID': [referral.referrer_id for referral in referrals],
        'Referred Phone': [referral.referred_phone for referral in referrals],
        'Purchased': ['Yes' if referral.purchased else 'No' for referral in referrals],
        'Type': [referral.type for referral in referrals],
        'Timestamp': [referral.timestamp.strftime('%Y-%m-%d %H:%M:%S') for referral in referrals]  # Format timestamp
    }

    users_df = pd.DataFrame(users_data)
    referrals_df = pd.DataFrame(referrals_data)

    # Create an Excel writer object
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')

    # Write the dataframes to different sheets
    users_df.to_excel(writer, index=False, sheet_name='Users')
    referrals_df.to_excel(writer, index=False, sheet_name='Referrals')

    # Save the Excel file by closing the writer
    writer.close()
    output.seek(0)

    # Return the Excel file as a response
    return send_file(output, download_name="output.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure database tables are created within the app context
    app.run(host='0.0.0.0', port=5000, debug=True)
