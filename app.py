from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Endpoints
LOGIN_URL = "https://auth-api.pijarsekolah.id/student/login"
SCORE_URL = "https://api.pijarsekolah.id/exam/v2/score?page=1&size=50&mapel=&jenis_ujian=non-akm&sort_by=terbaru&tahun=2025"
STATUS_URL = "https://auth-api.pijarsekolah.id/student/status"

# Headers for API requests
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Authorization': 'Basic cGlqYXJza2xoOmJkMjdmM2E5LTk1Y2MtNDdlMS04Y2IzLTBkYmY2NjVhMWYzOQ==',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Origin': 'https://siswa.pijarsekolah.id',
    'Referer': 'https://siswa.pijarsekolah.id/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    'sec-ch-ua': '"Not-A.Brand";v="99", "Chromium";v="124"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"'
}

def try_login(nisn):
    """Attempt to login with NISN"""
    try:
        # Format NISN with leading zeros if needed
        if len(nisn) < 10:
            nisn = nisn.zfill(10)
        
        login_data = {
            "username": nisn,
            "password": nisn,
            "remember": False,
            "school": "https://siswa.pijarsekolah.id/sman3pati"
        }
        
        response = requests.post(LOGIN_URL, json=login_data, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success') == True and 'data' in response_data:
                token = response_data['data'].get('token')
                return token
        
        return None
    except Exception as e:
        logger.error(f"Login error for NISN {nisn}: {str(e)}")
        return None

def get_user_status(token):
    """Get user profile information"""
    try:
        headers = HEADERS.copy()
        headers['Authorization'] = f"Bearer {token}"
        
        response = requests.get(STATUS_URL, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        
        return None
    except Exception as e:
        logger.error(f"Status error: {str(e)}")
        return None

def get_user_scores(token):
    """Get user scores"""
    try:
        headers = HEADERS.copy()
        headers['Authorization'] = f"Bearer {token}"
        
        response = requests.get(SCORE_URL, headers=headers, timeout=10)
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success') == True and 'data' in response_data:
                return response_data
        
        return None
    except Exception as e:
        logger.error(f"Scores error: {str(e)}")
        return None

def calculate_statistics(scores_data):
    """Calculate score statistics"""
    try:
        scores = []
        for score in scores_data:
            try:
                score_val = float(score.get('hasil_penilaian', 0))
                scores.append(score_val)
            except ValueError:
                continue
        
        if not scores:
            return None
        
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        passed = len([s for s in scores if s >= 70])
        
        return {
            'average': round(avg_score, 2),
            'highest': round(max_score, 2),
            'lowest': round(min_score, 2),
            'passed': passed,
            'total': len(scores),
            'pass_percentage': round((passed / len(scores)) * 100, 2)
        }
    except Exception as e:
        logger.error(f"Statistics calculation error: {str(e)}")
        return None

@app.route('/')
def home():
    """Home endpoint with API documentation"""
    return jsonify({
        'status': 'success',
        'message': 'Pijar Score API',
        'version': '1.0.0',
        'endpoints': {
            '/getscore': {
                'method': 'GET',
                'params': {
                    'nisn': 'required - Student NISN number'
                },
                'example': '/getscore?nisn=0081992381'
            },
            '/health': {
                'method': 'GET',
                'description': 'Check API health status'
            }
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/getscore')
def get_score():
    """Main endpoint to get student scores by NISN"""
    
    # Get NISN from query parameter
    nisn = request.args.get('nisn')
    
    # Validate NISN parameter
    if not nisn:
        return jsonify({
            'status': 'error',
            'message': 'NISN parameter is required',
            'example': '/getscore?nisn=0081992381'
        }), 400
    
    # Validate NISN format
    if not nisn.isdigit():
        return jsonify({
            'status': 'error',
            'message': 'NISN must be numeric',
            'provided': nisn
        }), 400
    
    logger.info(f"Processing request for NISN: {nisn}")
    
    # Try to login
    token = try_login(nisn)
    
    if not token:
        return jsonify({
            'status': 'error',
            'message': 'Failed to authenticate. Invalid NISN or login credentials',
            'nisn': nisn
        }), 401
    
    # Get user profile
    profile_data = get_user_status(token)
    
    # Get scores
    score_data = get_user_scores(token)
    
    if not score_data or not score_data.get('data'):
        return jsonify({
            'status': 'error',
            'message': 'No score data found for this NISN',
            'nisn': nisn
        }), 404
    
    # Extract student information
    student_info = {
        'nisn': nisn,
        'name': 'Unknown',
        'class': 'Unknown'
    }
    
    if profile_data and profile_data.get('success') == True and 'data' in profile_data:
        user_data = profile_data['data']
        student_info['name'] = user_data.get('fullName', 'Unknown')
        student_info['class'] = user_data.get('className', 'Unknown')
    elif len(score_data['data']) > 0:
        student_info['name'] = score_data['data'][0].get('nama', 'Unknown')
        # Extract class from nama_paket
        nama_paket = score_data['data'][0].get('nama_paket', '')
        if 'XI' in nama_paket:
            parts = nama_paket.split()
            for i, part in enumerate(parts):
                if part == 'XI' and i + 1 < len(parts):
                    student_info['class'] = f"XI {parts[i+1]}"
                    break
    
    # Process scores data
    scores_list = []
    for idx, score in enumerate(score_data['data'], 1):
        score_item = {
            'no': idx,
            'subject': score.get('nama_pelajaran', 'N/A'),
            'score': score.get('hasil_penilaian', 'N/A'),
            'exam_type': score.get('jenis_ujian', 'N/A'),
            'teacher': score.get('guru_pembuat', 'N/A'),
            'status': score.get('status_penilaian', 'N/A'),
            'exam_name': score.get('nama_paket', 'N/A')
        }
        scores_list.append(score_item)
    
    # Calculate statistics
    statistics = calculate_statistics(score_data['data'])
    
    # Build response
    response = {
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'student': student_info,
        'scores': {
            'total': len(scores_list),
            'data': scores_list
        }
    }
    
    if statistics:
        response['statistics'] = statistics
    
    logger.info(f"Successfully retrieved data for NISN: {nisn}")
    
    return jsonify(response)

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found',
        'available_endpoints': ['/getscore', '/health', '/']
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)
