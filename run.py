# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    # debug=True 代表開發模式，程式碼修改後會自動重啟，且報錯會顯示詳細資訊
    print("🚀 ASBL 伺服器啟動中... http://127.0.0.1:5000")
    app.run(debug=True)