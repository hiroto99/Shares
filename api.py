import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = r"C:\Users\hirot\open-webui-data\webui.db"

@app.route('/update_by_id', methods=['POST'])
def update_by_id():
    data = request.json
    user_id = data.get('user_id')
    add_amount = int(data.get('credits', 0))

    try:
        # 20秒間、他のプロセス（Docker）が離すのを待機する設定
        conn = sqlite3.connect(DB_PATH, timeout=20)
        # WALモード（書き込みと読み込みを並行できるモード）を有効化
        conn.execute('PRAGMA journal_mode=WAL;')
        cursor = conn.cursor()

        # 1. ユーザー取得（結果はタプル (info_str,) または None）
        cursor.execute("SELECT info FROM user WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result is None:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # 2. タプルの中身(0番目)を取り出し、型を強制的に辞書にする
        info_raw = result[0]
        
        info = {}
        if info_raw: # info_raw が None や空文字でない場合のみパース
            try:
                info = json.loads(info_raw)
                if not isinstance(info, dict): # 万が一リスト等だった場合のガード
                    info = {}
            except:
                info = {}

        # 3. usage の階層を「力技」で作る（.get を使わない）
        if 'usage' not in info:
            # もし info 直下に credits があるパターンならそれを採用
            current_credits = info.get('credits', 0)
            info['usage'] = {'credits': current_credits + add_amount}
        else:
            # usage 階層があるパターン
            current_credits = info['usage'].get('credits', 0)
            info['usage']['credits'] = current_credits + add_amount
        
        # UIに反映させるため、念のため info 直下にも credits を置いておく（互換性）
        info['credits'] = info['usage']['credits']
        
        current_credits = info['usage'].get('credits', 0)
        info['usage']['credits'] = current_credits + add_amount

        # SELECTした直後に入れてください
        print(f"DEBUG: 現在のinfoの中身はこれです -> {info_raw}")

        # 4. DB書き込み
        cursor.execute("UPDATE user SET info = ? WHERE id = ?", (json.dumps(info), user_id))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "new_total": info['usage']['credits']}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
