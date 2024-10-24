from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import numpy as np
from flask_cors import CORS
import os
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/*": {"origins": "*"}})

def get_sheet_data():
    """從公開 CSV URL 讀取資料"""
    try:
        csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS1ez27gqCLgeSuBf_UjY9PR99hkBZdpsFU7HbnCBL5UiAnCQ7mHTOcccu0wP3g2y9g8CFvnPIkdel3/pub?output=csv"
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/initial-data')
def get_initial_data():
    """獲取初始統計資料"""
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
def process():
    """處理數據並計算 z-scores"""
    try:
        user_input = request.json
        data = get_sheet_data()
        
        if data is None:
            return jsonify({"error": "Failed to fetch data"}), 500

        # 轉換輸入數據類型
        age = int(user_input['age'])
        iq = int(user_input['iq'])

        # 篩選數據
        filtered_data = data[
            (data['age'] >= age - 2) & (data['age'] <= age + 2) &
            (data['IQ'] >= iq - 5) & (data['IQ'] <= iq + 5)
        ]

        # 處理空數據情況
        if len(filtered_data) == 0:
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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
