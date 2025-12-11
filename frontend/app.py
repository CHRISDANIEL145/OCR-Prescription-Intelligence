import os
import sys
import json
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Backend API URL
BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:5000')

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'danielchristopher22@karunya.edu.in')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', 'your-app-password')


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def call_backend_api(endpoint, method='POST', data=None, files=None):
    """
    Call backend API with error handling
    Args:
        endpoint: API endpoint path (e.g., '/api/process-text')
        method: HTTP method (GET, POST, etc.)
        data: JSON data for POST requests
        files: Files for multipart requests

    Returns:
        dict: Response from API or error message
    """
    try:
        url = f"{BACKEND_API_URL}{endpoint}"

        if method == 'POST':
            if files:
                response = requests.post(url, files=files, timeout=300)
            else:
                response = requests.post(url, json=data, timeout=300)
        else:
            response = requests.get(url, timeout=300)

        if response.status_code == 200:
            return {'success': True, 'data': response.json()}
        else:
            return {
                'success': False,
                'error': response.json().get('error', 'API Error'),
                'status_code': response.status_code
            }

    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'error': f'Cannot connect to backend API at {BACKEND_API_URL}. Ensure backend is running.'
        }
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Backend API request timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def send_medication_alert(patient_email, medications, frequencies):
    """
    Send medication reminder email to patient
    Args:
        patient_email: Patient's email address
        medications: List of medications
        frequencies: List of frequencies
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        subject = "Medication Reminder - OCR Prescription Intelligence"
        body = f"""
        <html>
            <body>
                <h2>Medication Reminder</h2>
                <p>Dear Patient,</p>
                <p>Here are your prescribed medications:</p>
                <ul>
                    <li><strong>Medications:</strong> {', '.join(medications)}</li>
                    <li><strong>Frequencies:</strong> {', '.join(frequencies)}</li>
                </ul>
                <p>Please take your medications as prescribed by your doctor.</p>
                <p>Best regards,<br>OCR Prescription Intelligence Team</p>
            </body>
        </html>
        """

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = patient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


# ============================================================================
# ROUTES - PAGES
# ============================================================================

@app.route('/')
def home():
    """Home page"""
    return render_template('index.html')


@app.route('/upload')
def upload():
    """Upload/Analyze page"""
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """Dashboard page"""
    return render_template('index.html')


@app.route('/about')
def about():
    """About page"""
    return render_template('index.html')


@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('index.html')


# ============================================================================
# API ROUTES - PRESCRIPTION PROCESSING
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Check health status"""
    backend_status = call_backend_api('/api/health', method='GET')
    return jsonify({
        'frontend': 'running',
        'backend': backend_status,
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/process-text', methods=['POST'])
def process_text():
    """
    Process prescription text with NER

    Request body:
    {
        "text": "prescription text",
        "patient_email": "optional@email.com"
    }

    Response:
    {
        "success": true,
        "data": {
            "medications": [...],
            "doses": [...],
            "routes": [...],
            "frequencies": [...],
            "raw_text": "..."
        }
    }
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing "text" field in request body'
            }), 400

        text = data.get('text', '').strip()
        if not text:
            return jsonify({
                'success': False,
                'error': 'Prescription text cannot be empty'
            }), 400

        # Call backend API
        result = call_backend_api('/api/process-text', data={'text': text})

        if result['success']:
            response_data = result['data']

            # Optional: Send email alert
            medications = response_data.get('medications', [])
            frequencies = response_data.get('frequencies', [])
            patient_email = data.get('patient_email')

            if patient_email and medications:
                email_sent = send_medication_alert(patient_email, medications, frequencies)
                response_data['email_sent'] = email_sent

            return jsonify({'success': True, 'data': response_data}), 200
        else:
            return jsonify({'success': False, 'error': result['error']}), 400

    except Exception as e:
        print(f"Error in /api/process-text: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/process-image', methods=['POST'])
def process_image():
    """
    Process prescription image using AWS Textract + NER

    Request: multipart/form-data with 'file' field
    Optional: 'patient_email' field for alerts

    Response:
    {
        "success": true,
        "data": {
            "medications": [...],
            "doses": [...],
            "routes": [...],
            "frequencies": [...],
            "raw_text": "..."
        },
        "filename": "..."
    }
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # Save file temporarily
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], timestamp + filename)
        file.save(filepath)

        print(f"File saved to: {filepath}")

        # Call backend API
        with open(filepath, 'rb') as f:
            files = {'file': f}
            result = call_backend_api('/api/process-image', data=None, files=files)

        # Clean up temporary file
        try:
            os.remove(filepath)
            print(f"Cleaned up: {filepath}")
        except Exception as e:
            print(f"Error cleaning up file: {e}")

        if result['success']:
            response_data = result['data']

            # Optional: Send email alert
            medications = response_data.get('medications', [])
            frequencies = response_data.get('frequencies', [])
            patient_email = request.form.get('patient_email')

            if patient_email and medications:
                email_sent = send_medication_alert(patient_email, medications, frequencies)
                response_data['email_sent'] = email_sent

            return jsonify({
                'success': True,
                'data': response_data,
                'filename': filename
            }), 200
        else:
            return jsonify({'success': False, 'error': result['error']}), 400

    except Exception as e:
        print(f"Error in /api/process-image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/extract-entities', methods=['POST'])
def extract_entities():
    """
    Extract specific entities from prescription text

    Request body:
    {
        "text": "prescription text"
    }

    Response:
    {
        "success": true,
        "entities": {
            "medications": [...],
            "doses": [...],
            "routes": [...],
            "frequencies": [...]
        }
    }
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing "text" field'
            }), 400

        result = call_backend_api('/api/extract-entities', data=data)

        if result['success']:
            return jsonify(result['data']), 200
        else:
            return jsonify({'success': False, 'error': result['error']}), 400

    except Exception as e:
        print(f"Error in /api/extract-entities: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/batch-process', methods=['POST'])
def batch_process():
    """
    Process multiple prescriptions in batch

    Request body:
    {
        "prescriptions": [
            {"id": "1", "text": "prescription 1"},
            {"id": "2", "text": "prescription 2"}
        ]
    }

    Response:
    {
        "success": true,
        "count": 2,
        "results": [...]
    }
    """
    try:
        data = request.get_json()

        if not data or 'prescriptions' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing "prescriptions" field'
            }), 400

        result = call_backend_api('/api/batch-process', data=data)

        if result['success']:
            return jsonify(result['data']), 200
        else:
            return jsonify({'success': False, 'error': result['error']}), 400

    except Exception as e:
        print(f"Error in /api/batch-process: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get processing history"""
    try:
        return jsonify({
            'success': True,
            'history': [],
            'message': 'History feature coming soon'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/contact', methods=['POST'])
def contact_submit():
    """
    Handle contact form submission

    Request body:
    {
        "name": "...",
        "email": "...",
        "message": "..."
    }
    """
    try:
        data = request.get_json()

        required_fields = ['name', 'email', 'message']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, email, message'
            }), 400

        # TODO: Send contact email or save to database
        return jsonify({
            'success': True,
            'message': 'Contact form submitted successfully'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# STATIC FILES & REDIRECTS
# ============================================================================

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    try:
        return send_from_directory('static', 'favicon.ico')
    except:
        return '', 204  # No content


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Page not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors"""
    return jsonify({
        'success': False,
        'error': f'File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB'
    }), 413


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("OCR Prescription Intelligence Frontend - Simplified Structure")
    print("="*70)
    print(f"Backend API URL: {BACKEND_API_URL}")
    print(f"Email Configuration: {SENDER_EMAIL}")
    print(f"Upload Folder: {os.path.abspath(app.config['UPLOAD_FOLDER'])}")
    print("\nActive Routes:")
    print("  GET  /              - Home page")
    print("  GET  /upload        - Upload/Analyze page")
    print("  GET  /dashboard     - System dashboard")
    print("  GET  /about         - About page")
    print("  GET  /contact       - Contact page")
    print("\nAPI Routes:")
    print("  POST /api/process-text      - Process text")
    print("  POST /api/process-image     - Process image")
    print("  POST /api/extract-entities  - Extract entities")
    print("  POST /api/batch-process     - Batch process")
    print("  POST /api/contact           - Contact form")
    print("  GET  /api/health            - Health check")
    print("\nStarting Flask server on http://0.0.0.0:3000")
    print("="*70 + "\n")

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=3000,
        debug=True,
        use_reloader=False
    )