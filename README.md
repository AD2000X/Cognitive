# Cognitive Structure Dashboard

A web application for visualizing and analyzing cognitive structure data using Google Sheets integration.

## Setup

1. Clone the repository
```bash
git clone <repository-url>
cd cognitive-structure-dashboard
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create `.env` file with required environment variables:
```
FLASK_SECRET_KEY=your_secret_key
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
REDIRECT_URI=your_redirect_uri
```

5. Run the application locally
```bash
python app.py
```

## Deployment

1. Install Vercel CLI
```bash
npm i -g vercel
```

2. Deploy to Vercel
```bash
vercel
```

## Features

- Google OAuth Authentication
- Real-time data fetching from Google Sheets
- Interactive data visualization
- Dynamic filtering and analysis
- Z-score calculations
- Responsive design

## Technology Stack

- Backend: Flask
- Frontend: HTML, CSS, JavaScript
- Data Visualization: Plotly.js
- Authentication: Google OAuth
- Data Source: Google Sheets API
- Deployment: Vercel

## Environment Variables

- `FLASK_SECRET_KEY`: Flask session security key
- `GOOGLE_SHEET_ID`: ID of the Google Sheet containing data
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `REDIRECT_URI`: OAuth callback URL

## Directory Structure

```
.
├── static/
│   └── index.html
├── app.py
├── requirements.txt
├── vercel.json
├── .env
└── .gitignore
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.


