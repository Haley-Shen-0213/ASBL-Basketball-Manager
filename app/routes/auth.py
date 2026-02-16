# app/routes/auth.py
from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User
from app.models.team import Team
# 引入生成服務
from app.services.team_creator import TeamCreator
from app.services.player_generator import PlayerGenerator

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

    try:
        # 3. 建立使用者
        user = User(username=data['username'], email=data['email'])
        user.set_password(data['password'])
        db.session.add(user)
        db.session.flush() # 先 flush 以取得 user.id
        
        # 4. 自動建立一支球隊
        team_name = data.get('team_name') or f"{data['username']} 的球隊"
        team = Team(name=team_name, owner=user)
        db.session.add(team)
        db.session.flush() # 先 flush 以取得 team.id

        # 5. [核心新增] 生成初始 15 人名單
        # 初始化生成器 (確保快取載入)
        PlayerGenerator.initialize_class()
        
        # 生成符合規則 (C>=2, PG>=2...) 的名單 Payload
        roster_payloads = TeamCreator.create_valid_roster()
        
        # 將球員寫入資料庫
        for p_data in roster_payloads:
            PlayerGenerator.save_to_db(p_data, user_id=user.id, team_id=team.id)

        # 6. 提交所有變更
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
        # 在生產環境建議記錄詳細 Log，這裡回傳錯誤訊息方便除錯
        return jsonify({'error': f'註冊失敗: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '請提供帳號密碼'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if user and user.check_password(data['password']):
        return jsonify({
            'message': '登入成功',
            'user_id': user.id,
            'username': user.username,
            'team_id': user.team.id if user.team else None
        }), 200
    else:
        return jsonify({'error': '帳號或密碼錯誤'}), 401