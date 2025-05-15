# Mr.Frenzy - Website Penjualan Voucher Game
# Dibuat dengan Flask + SQLite + Keamanan Dasar

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

# Konfigurasi Aplikasi
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voucher_game.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # Maks 2 MB

# Inisialisasi Extensions
csrf = CSRFProtect(app)
db = SQLAlchemy(app)

# =======================
#        MODELS
# =======================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Voucher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_game = db.Column(db.String(100), nullable=False)
    nominal = db.Column(db.Integer, nullable=False)
    harga = db.Column(db.Integer, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    voucher_id = db.Column(db.Integer, db.ForeignKey('voucher.id'))
    status = db.Column(db.String(50), default='pending')
    user = db.relationship('User', backref='orders')
    voucher = db.relationship('Voucher', backref='orders')

# =======================
#     DECORATORS
# =======================

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash("Login terlebih dahulu.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user = User.query.get(session.get('user_id'))
        if not user or not user.is_admin:
            flash("Akses admin saja.")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrap

# =======================
#        ROUTES
# =======================

@app.route('/')
def index():
    vouchers = Voucher.query.all()
    return render_template('index.html', vouchers=vouchers)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash("Login berhasil.")
            return redirect(url_for('index'))
        flash("Username atau password salah.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logout berhasil.")
    return redirect(url_for('index'))

@app.route('/order/<int:voucher_id>')
@login_required
def order(voucher_id):
    voucher = Voucher.query.get_or_404(voucher_id)
    new_order = Order(user_id=session['user_id'], voucher_id=voucher_id)
    db.session.add(new_order)
    db.session.commit()
    flash("Order berhasil dibuat.")
    return redirect(url_for('index'))

# =======================
#        ADMIN
# =======================

@app.route('/admin')
@admin_required
def admin_panel():
    vouchers = Voucher.query.all()
    total_orders = Order.query.count()
    total_users = User.query.count()
    total_income = db.session.query(db.func.sum(Voucher.harga)).join(Order).scalar() or 0
    return render_template('admin.html', vouchers=vouchers, total_orders=total_orders,
                           total_users=total_users, total_income=total_income)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = Order.query.all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/tambah_voucher', methods=['POST'])
@admin_required
def tambah_voucher():
    try:
        nama = request.form['nama_game'].strip()
        nominal = int(request.form['nominal'])
        harga = int(request.form['harga'])

        if not nama or nominal <= 0 or harga <= 0:
            raise ValueError("Data tidak valid")

        new_voucher = Voucher(nama_game=nama, nominal=nominal, harga=harga)
        db.session.add(new_voucher)
        db.session.commit()
        flash("Voucher berhasil ditambahkan.")
    except Exception as e:
        flash(f"Gagal menambahkan voucher: {str(e)}")
    return redirect(url_for('admin_panel'))

# =======================
#     CLI & START
# =======================

@app.cli.command('create-admin')
def create_admin():
    """Buat akun admin melalui CLI"""
    username = input("Username admin: ").strip()
    password = input("Password: ").strip()
    if User.query.filter_by(username=username).first():
        print("Admin sudah ada.")
        return
    hashed_pw = generate_password_hash(password)
    admin_user = User(username=username, password=hashed_pw, is_admin=True)
    db.session.add(admin_user)
    db.session.commit()
    print("Admin berhasil dibuat.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Buat admin default kalau belum ada
        default_admin = 'zeinhafizputra@gmail.com'
        if not User.query.filter_by(username=default_admin).first():
            admin_user = User(
                username=default_admin,
                password=generate_password_hash('admin1234'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin default berhasil dibuat.")
        else:
            print("Admin default sudah ada.")

    app.run(debug=True)
