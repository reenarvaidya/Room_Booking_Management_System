from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os

secret_key = os.getenv("SECRET_KEY")


app = Flask(__name__)
app.secret_key = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Booking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    # Make email optional to fix the NOT NULL constraint error
    email = db.Column(db.String(120), unique=True, nullable=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    user_number = db.Column(db.String(15), nullable=False)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Functions to initialize admin user
def init_admin_user():
    """Create admin user if it doesn't exist"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        # Create admin user with default password 'admin123'
        # You should change this password after first login
        hashed_password = generate_password_hash('admin123')
        # Add a default email to fix NOT NULL constraint
        admin = User(username='admin', password=hashed_password, email='admin@example.com')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created!")

# Authentication route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('availability'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['logged_in'] = True
            session['username'] = user.username
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('availability'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Routes
@app.route('/')
def index():
    session.clear()  # force logout on every visit to root for testing
    print("Session forcibly cleared.")
    return redirect(url_for('login'))


@app.route('/availability', methods=['GET', 'POST'])
@login_required
def availability():
    # Handle POST requests first
    if request.method == 'POST':
        room_id = request.form.get('room_id')
        action = request.form.get('action')
        form_date = request.form.get('start_date')
        
        try:
            # Parse the date from form
            start_date = datetime.strptime(form_date, '%d-%m-%Y').date()
            
            if room_id and action:
                room_id = int(room_id)
                if action == 'book':
                    user_name = request.form.get('user_name')
                    user_number = request.form.get('user_number')
                    
                    if not user_name or not user_number:
                        flash("Name and phone number are required to book a room.", "error")
                    else:
                        existing_booking = Booking.query.filter_by(room_id=room_id, start_date=start_date).first()
                        if not existing_booking:
                            new_booking = Booking(
                                room_id=room_id,
                                start_date=start_date,
                                user_name=user_name,
                                user_number=user_number
                            )
                            db.session.add(new_booking)
                            db.session.commit()
                            flash(f"Room {room_id} booked successfully!", "success")
                        else:
                            flash(f"Room {room_id} is already booked for this date.", "error")
                elif action == 'cancel':
                    existing_booking = Booking.query.filter_by(room_id=room_id, start_date=start_date).first()
                    if existing_booking:
                        db.session.delete(existing_booking)
                        db.session.commit()
                        flash(f"Booking for Room {room_id} canceled successfully.", "success")
            
            # Redirect with the date as a query parameter
            return redirect(url_for('availability', date=form_date))
            
        except ValueError:
            flash("Invalid date format in form submission.", "error")
            return redirect(url_for('availability'))
    
    # For GET requests, get the date from URL parameters
    date_param = request.args.get('date')
    
    if date_param:
        try:
            selected_date = datetime.strptime(date_param, '%d-%m-%Y').date()
        except ValueError:
            flash("Invalid date format in URL.", "error")
            selected_date = datetime.now().date()
    else:
        # If no date parameter, use today's date
        selected_date = datetime.now().date()

    rooms = [
        {'id': 1, 'name': 'Room 1'},
        {'id': 2, 'name': 'Room 2'},
        {'id': 3, 'name': 'Room 3'},
        {'id': 4, 'name': 'Room 4'},
        {'id': 5, 'name': 'Room 5'},
        {'id': 6, 'name': 'Room 6'},
        {'id': 7, 'name': 'Room 7'},
    ]

    booked_rooms = Booking.query.filter(Booking.start_date == selected_date).all()
    booked_ids = [booking.room_id for booking in booked_rooms]
    bookings = {booking.room_id: booking for booking in booked_rooms}

    # Format the selected date to string format for the template
    formatted_date = selected_date.strftime('%d-%m-%Y')

    return render_template(
        'availability.html',
        rooms=rooms,
        booked_ids=booked_ids,
        bookings=bookings,
        selected_date=selected_date,
        formatted_date=formatted_date,  # Pass formatted date string
        username=session.get('username')
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create all tables if they don't exist
        init_admin_user()  # Initialize admin user
    app.run(debug=True, port=4000)