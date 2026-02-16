# app/routes/auth.py
from flask import Blueprint, request, jsonify
from datetime import datetime
from app import db
from app.models.user import User
from app.models.team import Team
from app.services.team_creator import TeamCreator
from app.services.player_generator import PlayerGenerator
from app.utils.game_config_loader import GameConfigLoader # [新增]

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # 1. 檢查必要欄位
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': '請提供使用者名稱、Email 和密碼'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': '使用者名稱已被使用'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email 已被註冊'}), 400

    try:
        # 2. 建立使用者
        user = User(username=data['username'], email=data['email'])
        user.set_password(data['password'])
        user.last_login = datetime.utcnow()
        
        db.session.add(user)
        db.session.flush() # 取得 user.id
        
        # 3. 讀取初始化設定
        init_settings = GameConfigLoader.get('system.initial_team_settings', {})
        init_funds = init_settings.get('funds', 300000)
        init_rep = init_settings.get('reputation', 0)
        init_scout = init_settings.get('scout_chances', 100)
        
        # 4. 設定球隊名稱 (預設為 Team_{ID})
        # 規則: 初始化的內容，球隊名稱=場館名稱=粉絲團
        default_name = f"Team_{user.id}"
        team_name = data.get('team_name') or default_name
        
        team = Team(
            name=team_name, 
            owner=user,
            funds=init_funds,
            reputation=init_rep,
            arena_name=team_name,    # 同步設定
            fanpage_name=team_name,  # 同步設定
            scout_chances=init_scout
        )
        db.session.add(team)
        db.session.flush() # 取得 team.id

        # 5. 生成初始 15 人名單
        PlayerGenerator.initialize_class()
        
        # [修改] max_attempts 採預設值 (100萬次)，若失敗會拋出 Exception
        roster_payloads = TeamCreator.create_valid_roster()
        
        for p_data in roster_payloads:
            PlayerGenerator.save_to_db(p_data, user_id=user.id, team_id=team.id)

        db.session.commit()
        
        return jsonify({
            'message': '註冊成功！球隊與初始球員已建立。',
            'user_id': user.id,
            'team_id': team.id,
            'team_name': team.name,
            'roster_count': len(roster_payloads)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'註冊失敗: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '請提供帳號密碼'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if user and user.check_password(data['password']):
        user.last_login = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': '登入成功',
            'user_id': user.id,
            'username': user.username,
            'team_id': user.team.id if user.team else None
        }), 200
    else:
        return jsonify({'error': '帳號或密碼錯誤'}), 401