# app/routes/auth.py
from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User, Team

# 定義藍圖，名稱為 'auth'，前綴為 '/api/auth'
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # 1. 檢查必要欄位
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': '請提供使用者名稱、Email 和密碼'}), 400

    # 2. 檢查是否重複註冊
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': '使用者名稱已被使用'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email 已被註冊'}), 400

    # 3. 建立使用者
    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    
    # 4. 自動建立一支球隊 (預設名稱: username 的球隊)
    team_name = data.get('team_name') or f"{data['username']} 的球隊"
    team = Team(name=team_name, owner=user)

    try:
        db.session.add(user)
        db.session.add(team)
        db.session.commit()
        
        return jsonify({
            'message': '註冊成功！',
            'user_id': user.id,
            'team_id': team.id,
            'team_name': team.name
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '請提供帳號密碼'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if user and user.check_password(data['password']):
        # 這裡暫時只回傳成功訊息，未來會加入 Token (JWT)
        return jsonify({
            'message': '登入成功',
            'user_id': user.id,
            'username': user.username,
            'team_id': user.team.id
        }), 200
    else:
        return jsonify({'error': '帳號或密碼錯誤'}), 401