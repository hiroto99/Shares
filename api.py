import sqlite3
import json
from flask import Flask, request, jsonify
from flask_cors import CORS  # 💡追加

app = Flask(__name__)
CORS(app)  # 💡これで全ドメインからのアクセスを許可します。
DB_PATH = r"C:\Users\hirot\open-webui-data\webui.db"

@app.route('/update_by_id', methods=['POST'])
def update_by_id():
    data = request.json
    user_id = data.get('user_id')
    add_amount = int(data.get('credits', 0))

    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()

        # 1. 現在の info カラムを取得
        cursor.execute("SELECT info FROM user WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result is None:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # 2. info カラムを辞書としてロード（空なら新規作成）
        info_raw = result[0]
        if info_raw is None or info_raw == "":
            info = {}
        else:
            try:
                info = json.loads(info_raw)
            except:
                info = {}

        # 3. usage 階層を確実に作成し、クレジットを加算
        # info["usage"]["credits"] の形を保証する
        if "usage" not in info or not isinstance(info["usage"], dict):
            info["usage"] = {}
        
        current_credits = info["usage"].get("credits", 0)
        new_total = current_credits + add_amount
        info["usage"]["credits"] = new_total
        
        # UI表示の互換性のため、直下にも一応置く
        info["credits"] = new_total 

        # 4. DB へ書き戻し
        cursor.execute("UPDATE user SET info = ? WHERE id = ?", (json.dumps(info), user_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Success: User {user_id} updated. New Total: {new_total}")
        return jsonify({"status": "success", "new_total": new_total}), 200

    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/get_credits', methods=['POST'])
def get_credits():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"credits": 0, "error": "No User ID"}), 400

    try:
        # SQLiteに接続して最新の残高を取得
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cursor = conn.cursor()
        
        # Open WebUIのユーザーテーブルからinfoカラム（JSON）を取得
        cursor.execute("SELECT info FROM user WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        credits = 0
        if result and result[0]:
            try:
                info = json.loads(result[0])
                # APIの更新ロジックに合わせて usage.credits を参照
                credits = info.get('usage', {}).get('credits', 0)
            except Exception:
                credits = 0
        
        print(f"🔍 Get Credits: User {user_id} has {credits} c")
        return jsonify({"credits": credits}), 200

    except Exception as e:
        print(f"❌ Get Credits Error: {str(e)}")
        return jsonify({"credits": 0, "error": str(e)}), 500
    
@app.route('/consume_credits', methods=['POST'])
def consume_credits():
    data = request.json
    user_id = data.get('user_id')
    # 💡 強制的に数値(int)に変換する
    try:
        amount = int(data.get('amount', 1))
    except (ValueError, TypeError):
        amount = 1

    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT info FROM user WHERE id = ?", (user_id,))
        result = cursor.fetchone()

        if not result or not result[0]:
            return jsonify({"status": "error", "message": "User not found"}), 404

        info = json.loads(result[0])
        if "usage" not in info: info["usage"] = {}
        
        current = info["usage"].get("credits", 0)
        
        # 減算処理
        new_total = current - amount
        info["usage"]["credits"] = max(0, new_total) # 0以下にならないようにガード
        info["credits"] = max(0, new_total)

        cursor.execute("UPDATE user SET info = ? WHERE id = ?", (json.dumps(info), user_id))
        conn.commit()
        conn.close()

        print(f"📉 Consumed: {user_id} -{amount}c. New Total: {new_total}")
        return jsonify({"status": "success", "new_total": new_total}), 200
    except Exception as e:
        print(f"❌ Consume Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
