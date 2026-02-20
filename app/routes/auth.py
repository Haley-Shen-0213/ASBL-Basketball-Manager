# app/routes/auth.py

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from app import db
from app.models.user import User
from app.models.team import Team
from app.models.tactics import TeamTactics
from app.services.team_creator import TeamCreator
from app.services.player_generator import PlayerGenerator
from app.services.league_service import LeagueService
from app.utils.game_config_loader import GameConfigLoader
from app.services.image_generation_service import ImageGenerationService

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    使用者註冊與開隊流程 (取代模式)
    1. 建立 User
    2. 建立全新的 Team (ID Auto Inc)
    3. 生成 15 名球員並寫入
    4. 初始化戰術配置
    5. [關鍵] 呼叫 LeagueService 執行「聯賽席位取代」或「擴充配對」
    """
    data = request.get_json()
    
    # 1. 基礎驗證
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': '請提供使用者名稱、Email 和密碼'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': '使用者名稱已被使用'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email 已被註冊'}), 400

    try:
        # --- Step 1: 建立 User ---
        user = User(
            username=data['username'], 
            email=data['email'],
            is_bot=False,
            last_login=datetime.utcnow()
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush() # 取得 user.id
        
        # --- Step 2: 建立全新的 Team ---
        # 讀取初始設定
        init_settings = GameConfigLoader.get('system.initial_team_settings', {})
        default_name = f"Team_{user.id}"
        team_name = data.get('team_name') or default_name
        
        new_team = Team(
            name=team_name,
            owner=user,
            funds=init_settings.get('funds', 300000),
            reputation=init_settings.get('reputation', 0),
            arena_name=team_name,
            fanpage_name=team_name,
            scout_chances=init_settings.get('scout_chances', 100),
            daily_scout_level=0,
            status='PLAYER',
            is_official=False, # 先預設為 False，稍後由 Service 判斷是否晉升
            season_wins=0,
            season_losses=0
        )
        db.session.add(new_team)
        db.session.flush() # 取得 new_team.id
        
        # --- Step 3: 產生新球員 ---
        PlayerGenerator.initialize_class()
        roster_payloads = TeamCreator.create_valid_roster()
        
        player_ids = []
        for p_data in roster_payloads:
            player, _ = PlayerGenerator.save_to_db(p_data, user_id=user.id, team_id=new_team.id)
            player_ids.append(player.id)

        # --- Step 4: 初始化戰術配置 ---
        tactics = TeamTactics(
            team_id=new_team.id,
            roster_list=player_ids
        )
        db.session.add(tactics)

        # --- Step 5: 執行聯賽席位處理 (取代或擴充) ---
        # 這裡會決定 new_team 是否取代某個 BOT 進入正式聯賽
        LeagueService.process_league_entry(new_team)

        # --- Final: 提交所有變更 ---
        db.session.commit()

        # --- [New] Step 6: 觸發背景圖片生成 ---
        # 傳入 current_app._get_current_object() 以便在執行緒中使用 App Context
        try:
            ImageGenerationService.start_background_generation(
                current_app._get_current_object(), 
                player_ids
            )
        except Exception as img_err:
            print(f"⚠️ [Auth] 觸發圖片生成失敗 (不影響註冊): {img_err}")
        
        return jsonify({
            'message': '註冊成功！球隊已建立並加入聯賽體系。',
            'user_id': user.id,
            'team_id': new_team.id,
            'team_name': new_team.name,
            'is_official': new_team.is_official,
            'roster_count': len(player_ids)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
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