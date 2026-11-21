from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////root/.picoclaw/workspace/dashboards/study-monitor/users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-focus-pulse-key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=30)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    study_data = db.relationship('StudyData', backref='user', uselist=False)

class StudyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_minutes = db.Column(db.Integer, default=0)
    tasks_completed = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    tasks_json = db.Column(db.Text, default='[]') # JSON string of tasks
    last_updated = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Create DB
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"msg": "Username already exists"}), 400
    
    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = User(username=data['username'], password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    
    # Initialize study data
    new_data = StudyData(user_id=new_user.id)
    db.session.add(new_data)
    db.session.commit()
    
    return jsonify({"msg": "User created successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify(access_token=access_token, username=user.username), 200
    return jsonify({"msg": "Invalid credentials"}), 401

@app.route('/api/data', methods=['GET'])
@jwt_required()
def get_data():
    user_id = get_jwt_identity()
    data = StudyData.query.filter_by(user_id=user_id).first()
    return jsonify({
        "total_minutes": data.total_minutes,
        "tasks_completed": data.tasks_completed,
        "streak": data.streak,
        "tasks": data.tasks_json
    })

@app.route('/api/data', methods=['POST'])
@jwt_required()
def save_data():
    user_id = get_jwt_identity()
    incoming = request.get_json()
    data = StudyData.query.filter_by(user_id=user_id).first()
    
    if 'total_minutes' in incoming: data.total_minutes = incoming['total_minutes']
    if 'tasks_completed' in incoming: data.tasks_completed = incoming['tasks_completed']
    if 'streak' in incoming: data.streak = incoming['streak']
    if 'tasks' in incoming: data.tasks_json = incoming['tasks']
    
    data.last_updated = datetime.datetime.utcnow()
    db.session.commit()
    return jsonify({"msg": "Data saved"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8101)))
