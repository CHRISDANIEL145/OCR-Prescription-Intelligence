import os
import sys
import io
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from dotenv import load_dotenv
import tempfile
import uuid

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Create uploads directory for temporary files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize NER Model
print("Loading spaCy model...")
print("Loading medical NER transformer model...")

try:
    from ml_model.ner import ner_model
    print("NER Model initialized successfully!")
except Exception as e:
    print(f"Error loading NER model: {e}")
    ner_model = None

# Initialize AWS Textract
try:
    AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

    textract_client = boto3.client(
        'textract',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    print("✓ AWS Textract client initialized")
except Exception as e:
    print(f"Warning: AWS Textract not configured: {e}")
    textract_client = None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_text_from_image(image_bytes):
    """Extract text from image using AWS Textract"""
    try:
        if not textract_client:
            return "AWS Textract not configured"

        response = textract_client.detect_document_text(
            Document={'Bytes': image_bytes}
        )

        # Extract text from blocks
        text_lines = []
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_lines.append(block['Text'])

        return '\n'.join(text_lines)

    except Exception as e:
        print(f"Error in Textract: {e}")
        return f"Error extracting text: {str(e)}"


def process_with_ner(text):
    """Process text with NER model to extract entities"""
    try:
        if not ner_model:
            return {
                'medications': [],
                'doses': [],
                'routes': [],
                'frequencies': [],
                'raw_text': text
            }

        # Use NER model to extract entities
        result = ner_model.extract_entities(text)

        return {
            'medications': result.get('medications', []),
            'doses': result.get('doses', []),
            'routes': result.get('routes', []),
            'frequencies': result.get('frequencies', []),
            'raw_text': text
        }

    except Exception as e:
        print(f"Error in NER processing: {e}")
        return {
            'medications': [],
            'doses': [],
            'routes': [],
            'frequencies': [],
            'raw_text': text,
            'error': str(e)
        }


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'components': {
            'flask': 'running',
            'ner_model': 'initialized' if ner_model else 'not_loaded',
            'textract': 'configured' if textract_client else 'not_configured'
        },
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/process-text', methods=['POST'])
def process_text():
    """
    Process prescription text with NER

    Request body:
    {
        "text": "prescription text"
    }

    Response:
    {
        "success": true,
        "medications": [...],
        "doses": [...],
        "routes": [...],
        "frequencies": [...],
        "raw_text": "..."
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

        # Process with NER
        result = process_with_ner(text)

        return jsonify({
            'success': True,
            **result
        }), 200

    except Exception as e:
        print(f"Error in /api/process-text: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/process-image', methods=['POST'])
def process_image():
    """
    Process prescription image with AWS Textract + NER

    Request: multipart/form-data with 'file' field

    Response:
    {
        "success": true,
        "medications": [...],
        "doses": [...],
        "routes": [...],
        "frequencies": [...],
        "raw_text": "..."
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

        # Read file bytes
        image_bytes = file.read()

        # Save temporarily (Windows-compatible path)
        temp_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{file.filename}"
        temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)

        print(f"Saving file to: {temp_path}")

        # Save file
        with open(temp_path, 'wb') as f:
            f.write(image_bytes)

        # Extract text using AWS Textract
        extracted_text = extract_text_from_image(image_bytes)

        # Clean up temporary file
        try:
            os.remove(temp_path)
            print(f"Cleaned up: {temp_path}")
        except Exception as e:
            print(f"Error cleaning up file: {e}")

        # Process with NER
        result = process_with_ner(extracted_text)

        return jsonify({
            'success': True,
            **result
        }), 200

    except Exception as e:
        print(f"Error in /api/process-image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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

        text = data.get('text', '').strip()

        if not text:
            return jsonify({
                'success': False,
                'error': 'Text cannot be empty'
            }), 400

        # Process with NER
        result = process_with_ner(text)

        return jsonify({
            'success': True,
            'entities': {
                'medications': result.get('medications', []),
                'doses': result.get('doses', []),
                'routes': result.get('routes', []),
                'frequencies': result.get('frequencies', [])
            },
            'raw_text': result.get('raw_text', text)
        }), 200

    except Exception as e:
        print(f"Error in /api/extract-entities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        "results": [
            {"id": "1", "medications": [...], ...},
            {"id": "2", "medications": [...], ...}
        ]
    }
    """
    try:
        data = request.get_json()

        if not data or 'prescriptions' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing "prescriptions" field'
            }), 400

        prescriptions = data.get('prescriptions', [])

        if not isinstance(prescriptions, list):
            return jsonify({
                'success': False,
                'error': '"prescriptions" must be a list'
            }), 400

        results = []
        for prescription in prescriptions:
            prescription_id = prescription.get('id', 'unknown')
            text = prescription.get('text', '')

            if text:
                result = process_with_ner(text)
                results.append({
                    'id': prescription_id,
                    **result
                })

        return jsonify({
            'success': True,
            'count': len(results),
            'results': results
        }), 200

    except Exception as e:
        print(f"Error in /api/batch-process: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/', methods=['GET'])
def index():
    """API documentation endpoint"""
    return jsonify({
        'name': 'OCR Prescription Intelligence API',
        'version': '1.0.0',
        'description': 'Prescription digitization with NER',
        'endpoints': {
            'GET /api/health': 'Health check',
            'POST /api/process-text': 'Process prescription text',
            'POST /api/process-image': 'Process prescription image',
            'POST /api/extract-entities': 'Extract entities from text',
            'POST /api/batch-process': 'Batch process prescriptions'
        },
        'status': 'running'
    }), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
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
        'error': 'File too large'
    }), 413


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("OCR Prescription Intelligence API - Python-based NER Version")
    print("="*70)
    print(f"✓ NER Model: {'Initialized' if ner_model else 'Not loaded'}")
    print(f"✓ AWS Textract: {'Configured' if textract_client else 'Not configured'}")
    print(f"\nUpload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print("\nStarting Flask server on http://0.0.0.0:5000")
    print("="*70 + "\n")

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False
    )
