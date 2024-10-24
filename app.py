from flask import Flask, request, jsonify, send_from_directory, session, redirect
from flask_cors import CORS
import pandas as pd
import numpy as np
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv
import json
from functools import wraps

load_dotenv()

app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev')
CORS(app, resources={r"/*": {"origins": "*"}})

# Google OAuth configuration
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# 從環境變數創建 client_secrets.json
client_config = {
    "web": {
        "client_id": os.getenv('GOOGLE_CLIENT_ID'),
        "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
        "redirect_uris": [
            "http://localhost:3000/api/auth/callback/google",
            "https://cognitive-eight.vercel.app/api/auth/callback/google"
        ],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}

try:
    with open(CLIENT_SECRETS_FILE, 'w') as f:
        json.dump(client_config, f)
except Exception as e:
    print(f"Error writing client secrets file: {e}")

# 登入驗證裝飾器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return jsonify({"error": "Not authenticated", "redirect": "/auth"}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_sheet_data():
    """從 Google Sheets 獲取數據"""
    try:
        SPREADSHEET_ID = os.getenv('GOOGLE_SHEET_ID')
        RANGE_NAME = 'Sheet1!A:P'

        if 'credentials' not in session:
            return None

        creds = Credentials.from_authorized_user_info(session['credentials'], SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                session['credentials'] = json.loads(creds.to_json())
            else:
                return None

        service = build('sheets', 'v4', credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])
        
        if not values:
            return pd.DataFrame()
            
        df = pd.DataFrame(values[1:], columns=values[0])
        
        # 轉換數值欄位
        numeric_columns = ['age', 'IQ', 'PL', 'PR', 'SE', 'CT', 'AT', 'ABPM', 'EBPM', 'TBPM', 'AV']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df

    except Exception as e:
        print(f"Error in get_sheet_data: {e}")
        return None

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/auth')
def auth():
    """初始化 OAuth 流程"""
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES)
        flow.redirect_uri = os.getenv('REDIRECT_URI', 
                                    'http://localhost:3000/api/auth/callback/google')
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true')

        session['state'] = state
        return redirect(authorization_url)
    except Exception as e:
        print(f"Error in auth: {e}")
        return jsonify({"error": "Authentication failed"}), 500

@app.route('/oauth2callback')
def oauth2callback():
    """處理 OAuth 回調"""
    try:
        state = session['state']
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
        flow.redirect_uri = os.getenv('REDIRECT_URI', 
                                    'http://localhost:3000/api/auth/callback/google')

        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        session['credentials'] = json.loads(credentials.to_json())
        
        return redirect('/')
    except Exception as e:
        print(f"Error in oauth2callback: {e}")
        return jsonify({"error": "OAuth callback failed"}), 500

@app.route('/auth/status')
def auth_status():
    """檢查登入狀態"""
    return jsonify({
        'logged_in': 'credentials' in session
    })

@app.route('/initial-data')
@login_required
def get_initial_data():
    """獲取初始數據統計"""
    try:
        data = get_sheet_data()
        if data is None:
            return jsonify({"error": "Failed to fetch data"}), 500
        
        stats = {
            'total_records': len(data),
            'age_range': {
                'min': int(data['age'].min()),
                'max': int(data['age'].max())
            },
            'iq_range': {
                'min': int(data['IQ'].min()),
                'max': int(data['IQ'].max())
            },
            'construct_ranges': {}
        }
        
        constructs = ['PL', 'PR', 'SE', 'CT', 'AT', 'ABPM', 'EBPM', 'TBPM', 'AV']
        for construct in constructs:
            stats['construct_ranges'][construct] = {
                'min': int(data[construct].min()),
                'max': int(data[construct].max())
            }
        
        return jsonify(stats)
    except Exception as e:
        print(f"Error in get_initial_data: {e}")
        return jsonify({"error": "Failed to process initial data"}), 500

@app.route('/process', methods=['POST'])
@login_required
def process():
    """處理數據並計算 z-scores"""
    try:
        user_input = request.json
        data = get_sheet_data()
        
        if data is None:
            return jsonify({"error": "Failed to fetch data"}), 500

        age = int(user_input['age'])
        iq = int(user_input['iq'])

        # 篩選數據
        filtered_data = data[
            (data['age'] >= age - 2) & (data['age'] <= age + 2) &
            (data['IQ'] >= iq - 5) & (data['IQ'] <= iq + 5)
        ]

        if filtered_data.empty:
            return jsonify({
                'plot_data': [{
                    'x': ['PL', 'PR', 'SE', 'CT', 'AT', 'ABPM', 'EBPM', 'TBPM', 'AV'],
                    'y': [0] * 9,
                    'type': 'bar'
                }],
                'layout': {
                    'title': 'No matching data to display',
                    'xaxis': {'title': 'Cognitive Constructs'},
                    'yaxis': {'title': 'Z-Scores', 'range': [-5, 1]}
                },
                'filtered_count': 0
            })

        # 計算 Z-Scores
        constructs = ['PL', 'PR', 'SE', 'CT', 'AT', 'ABPM', 'EBPM', 'TBPM', 'AV']
        z_scores = {}
        for construct in constructs:
            mean = filtered_data[construct].mean()
            std = filtered_data[construct].std()
            user_score = float(user_input[construct])
            z_scores[construct] = (user_score - mean) / std if std > 0 else 0

        # 準備圖表數據
        plot_data = [{
            'x': list(z_scores.keys()),
            'y': list(z_scores.values()),
            'type': 'bar'
        }]

        layout = {
            'title': 'Z-Scores of Cognitive Constructs',
            'xaxis': {'title': 'Cognitive Constructs'},
            'yaxis': {'title': 'Z-Scores', 'range': [-5, 1]}
        }

        result = {
            'plot_data': plot_data,
            'layout': layout,
            'filtered_count': len(filtered_data),
            'statistics': {
                'filtered_age_range': [int(filtered_data['age'].min()), int(filtered_data['age'].max())],
                'filtered_iq_range': [int(filtered_data['IQ'].min()), int(filtered_data['IQ'].max())]
            }
        }
        
        return jsonify(result)

    except Exception as e:
        print(f"Error in process: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
