from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import random
import string

app = Flask(__name__)

# Konfigurasi DB & Email
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mahasiswa.db'
app.config['SECRET_KEY'] = 'rahasia'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email SMTP (gunakan akun Gmail pribadi/test)
app.config['MAIL_SERVER']='sandbox.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = '58f0e9529be8fb'
app.config['MAIL_PASSWORD'] = '18fc13d2456d08'
app.config['MAIL_USE_TLS'] = True

# Inisialisasi
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
jwt = JWTManager(app)

# ==================== MODELS ====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    activation_code = db.Column(db.String(6), nullable=True)

class Mahasiswa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    jurusan = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {"id": self.id, "nama": self.nama, "jurusan": self.jurusan}

# ==================== ROUTES ====================

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data['email']
    password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    code = ''.join(random.choices(string.digits, k=6))

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email sudah terdaftar"}), 400

    user = User(email=email, password=password, activation_code=code)
    db.session.add(user)
    db.session.commit()

    # Kirim email aktivasi
    msg = Message('Kode Aktivasi', sender='irfants1710@gmail.com', recipients=[email])
    msg.body = f"Kode aktivasi akun kamu adalah: {code}"
    mail.send(msg)

    return jsonify({"message": "Pendaftaran berhasil. Cek email untuk aktivasi."}), 201

@app.route('/activate', methods=['POST'])
def activate():
    data = request.get_json()
    email = data['email']
    code = data['code']
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"message": "Email tidak ditemukan"}), 404

    if user.activation_code == code:
        user.is_active = True
        user.activation_code = None
        db.session.commit()
        return jsonify({"message": "Akun berhasil diaktivasi"}), 200

    return jsonify({"message": "Kode aktivasi salah"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()

    if not user or not bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({"message": "Email atau password salah"}), 401
    if not user.is_active:
        return jsonify({"message": "Akun belum diaktivasi"}), 403

    token = create_access_token(identity=str(user.id))
    return jsonify(access_token=token)

# ============ ENDPOINT MAHASISWA (PROTEKSI JWT) ============

@app.route('/mahasiswa', methods=['GET'])
@jwt_required()
def get_mahasiswa():
    data = Mahasiswa.query.all()
    return jsonify([m.to_dict() for m in data])

@app.route('/mahasiswa', methods=['POST'])
@jwt_required()
def tambah_mahasiswa():
    data = request.get_json()
    mhs = Mahasiswa(nama=data['nama'], jurusan=data['jurusan'])
    db.session.add(mhs)
    db.session.commit()
    return jsonify({"message": "Data berhasil ditambahkan", "data": mhs.to_dict()}), 201

@app.route('/mahasiswa/<int:id>', methods=['GET'])
@jwt_required()
def get_by_id(id):
    mhs = Mahasiswa.query.get(id)
    if mhs:
        return jsonify(mhs.to_dict())
    return jsonify({"message": "Mahasiswa tidak ditemukan"}), 404

@app.route('/mahasiswa/<int:id>', methods=['DELETE'])
@jwt_required()
def hapus_mhs(id):
    mhs = Mahasiswa.query.get(id)
    if mhs:
        db.session.delete(mhs)
        db.session.commit()
        return jsonify({"message": "Berhasil dihapus"})
    return jsonify({"message": "Mahasiswa tidak ditemukan"}), 404

# =========== SETUP DB ============
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
