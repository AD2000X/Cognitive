from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import numpy as np
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/*": {"origins": "*"}})

# Assume we have a pre-prepared dataset
data = pd.DataFrame({
    'age': np.random.randint(18, 80, 1000),
    'IQ': np.random.normal(100, 15, 1000),
    'PL': np.random.normal(100, 15, 1000),
    'PR': np.random.normal(100, 15, 1000),
    'SE': np.random.normal(100, 15, 1000),
    'CT': np.random.normal(100, 15, 1000),
    'AT': np.random.normal(100, 15, 1000),
    'ABPM': np.random.normal(100, 15, 1000),
    'EBPM': np.random.normal(100, 15, 1000),
    'TBPM': np.random.normal(100, 15, 1000),
    'AV': np.random.normal(100, 15, 1000),
})

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/process', methods=['POST'])
def process():
    print("Received request")
    user_input = request.json
    print("User input:", user_input)
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
            'plot_data': [{'x': ['PL', 'PR', 'SE', 'CT', 'AT', 'ABPM', 'EBPM', 'TBPM', 'AV'], 'y': [0] * 9, 'type': 'bar'}],
            'layout': {'title': 'No matching data to display', 'xaxis': {'title': 'Cognitive Constructs'}, 'yaxis': {'title': 'Z-Scores', 'range': [-5, 1]}
            }
        })

    # Calculate Z-Scores
    constructs = ['PL', 'PR', 'SE', 'CT', 'AT', 'ABPM', 'EBPM', 'TBPM', 'AV']
    z_scores = {}
    for construct in constructs:
        mean = filtered_data[construct].mean()
        std = filtered_data[construct].std()
        user_score = float(user_input[construct])
        z_scores[construct] = (user_score - mean) / std if std > 0 else 0  # Prevent division by 0

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

@app.errorhandler(404)
def not_found(e):
    return "404: Page Not Found - Please make sure index.html is in the static folder", 404

@app.errorhandler(500)
def internal_server_error(e):
    return "500: Internal Server Error", 500

if __name__ == '__main__':
    app.run(debug=True)
