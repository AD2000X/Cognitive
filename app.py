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

with open(CLIENT_SECRETS_FILE, 'w') as f:
    json.dump(client_config, f)

def get_google_sheets_data():
    """Fetch data from Google Sheets"""
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

    try:
        service = build('sheets', 'v4', credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])
        
        if not values:
            return pd.DataFrame()
            
        df = pd.DataFrame(values[1:], columns=values[0])
        return df
    except Exception as e:
        print(f"Error fetching Google Sheets data: {e}")
        return None

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/auth')
def auth():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = os.getenv('REDIRECT_URI', 
                                'http://localhost:3000/api/auth/callback/google')
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
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

@app.route('/process', methods=['POST'])
def process():
    print("Received request")
    user_input = request.json
    print("User input:", user_input)
    
    # Get data from Google Sheets
    data = get_google_sheets_data()
    if data is None:
        return jsonify({"error": "Failed to fetch data from Google Sheets"})
        
    # Convert necessary columns to numeric
    numeric_columns = ['age', 'IQ', 'PL', 'PR', 'SE', 'CT', 'AT', 'ABPM', 'EBPM', 'TBPM', 'AV']
    for col in numeric_columns:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    
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
            }
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

    result = {'plot_data': plot_data, 'layout': layout}
    print("Sending response:", result)
    return jsonify(result)

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
