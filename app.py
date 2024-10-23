from flask import Flask, request, jsonify, send_from_directory, session, redirect
import pandas as pd
import numpy as np
from flask_cors import CORS
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv
import json
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev')
CORS(app, resources={r"/*": {"origins": "*"}})

# Google OAuth configuration
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Create client_secrets.json from environment variables
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

# Write client secrets to file
try:
    with open(CLIENT_SECRETS_FILE, 'w') as f:
        json.dump(client_config, f)
except Exception as e:
    print(f"Error writing client secrets file: {e}")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return jsonify({"error": "Not authenticated", "redirect": "/auth"}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_google_sheets_data():
    """Fetch and process data from Google Sheets"""
    try:
        SPREADSHEET_ID = os.getenv('GOOGLE_SHEET_ID')
        RANGE_NAME = 'Sheet1!A:P'  # Adjust based on your sheet's range

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
            print("No data found in Google Sheets")
            return pd.DataFrame()
            
        df = pd.DataFrame(values[1:], columns=values[0])
        
        # Convert numeric columns
        numeric_columns = ['age', 'IQ', 'PL', 'PR', 'SE', 'CT', 'AT', 'ABPM', 'EBPM', 'TBPM', 'AV']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df

    except Exception as e:
        print(f"Error in get_google_sheets_data: {e}")
        return None

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/auth')
def auth():
    """Initiate the OAuth flow"""
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
        print(f"Error in auth route: {e}")
        return jsonify({"error": "Authentication failed"}), 500

@app.route('/oauth2callback')
def oauth2callback():
    """Handle the OAuth callback"""
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
    """Check authentication status"""
    return jsonify({
        'logged_in': 'credentials' in session
    })

@app.route('/initial-data')
@login_required
def get_initial_data():
    """Get initial data statistics"""
    try:
        data = get_google_sheets_data()
        if data is None:
            return jsonify({"error": "Failed to fetch data"}), 500
        
        # Calculate basic statistics
        stats = {
            'total_records': len(data),
            'age_range': {
                'min': data['age'].min(),
                'max': data['age'].max()
            },
            'iq_range': {
                'min': data['IQ'].min(),
                'max': data['IQ'].max()
            },
            'construct_ranges': {}
        }
        
        # Calculate ranges for all constructs
        constructs = ['PL', 'PR', 'SE', 'CT', 'AT', 'ABPM', 'EBPM', 'TBPM', 'AV']
        for construct in constructs:
            stats['construct_ranges'][construct] = {
                'min': data[construct].min(),
                'max': data[construct].max()
            }
        
        return jsonify(stats)
    except Exception as e:
        print(f"Error in get_initial_data: {e}")
        return jsonify({"error": "Failed to process initial data"}), 500

@app.route('/process', methods=['POST'])
@login_required
def process():
    """Process data and calculate z-scores"""
    try:
        print("Received request")
        user_input = request.json
        print("User input:", user_input)
        
        # Get data from Google Sheets
        data = get_google_sheets_data()
        if data is None:
            return jsonify({"error": "Failed to fetch data from Google Sheets"}), 500
        
        age = int(user_input['age'])
        iq = int(user_input['iq'])

        # Filter data using age and IQ ranges
        filtered_data = data[
            (data['age'] >= age - 2) & (data['age'] <= age + 2) &
            (data['IQ'] >= iq - 5) & (data['IQ'] <= iq + 5)
        ]

        # If filtered data is empty
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

        # Calculate Z-Scores
        constructs = ['PL', 'PR', 'SE', 'CT', 'AT', 'ABPM', 'EBPM', 'TBPM', 'AV']
        z_scores = {}
        for construct in constructs:
            mean = filtered_data[construct].mean()
            std = filtered_data[construct].std()
            user_score = float(user_input[construct])
            z_scores[construct] = (user_score - mean) / std if std > 0 else 0

        # Prepare plot data
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
                'filtered_age_range': [filtered_data['age'].min(), filtered_data['age'].max()],
                'filtered_iq_range': [filtered_data['IQ'].min(), filtered_data['IQ'].max()]
            }
        }
        
        print("Sending response:", result)
        return jsonify(result)

    except Exception as e:
        print(f"Error in process route: {e}")
        return jsonify({"error": "Failed to process data"}), 500

@app.errorhandler(404)
def not_found(e):
    return "404: Page Not Found - Please make sure index.html is in the static folder", 404

@app.errorhandler(500)
def internal_server_error(e):
    return "500: Internal Server Error", 500

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
