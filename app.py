from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
import hashlib

app = Flask(__name__)
CORS(app)  # Enable CORS for web frontend

# Configuration
UPLOAD_FOLDER = Path('uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)
METADATA_FILE = Path('clips_metadata.json')
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB limit

# Base URL - change this when deploying
BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')

# Initialize metadata file
if not METADATA_FILE.exists():
    with open(METADATA_FILE, 'w') as f:
        json.dump({"clips": []}, f)


def load_metadata():
    """Load clips metadata from JSON file"""
    try:
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"clips": []}


def save_metadata(data):
    """Save clips metadata to JSON file"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def generate_clip_id():
    """Generate unique clip ID"""
    return str(uuid.uuid4())[:8]


def get_file_hash(filepath):
    """Get SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()[:16]


@app.route('/')
def index():
    """API info endpoint"""
    return jsonify({
        "service": "Screen Clip Storage Server",
        "version": "1.0",
        "endpoints": {
            "/upload": "POST - Upload a clip",
            "/clips": "GET - List all clips",
            "/clips/<clip_id>": "GET - Download specific clip",
            "/delete/<clip_id>": "DELETE - Delete a clip"
        }
    })


@app.route('/upload', methods=['POST'])
def upload_clip():
    """Handle clip upload"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Validate file type
        allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({"error": f"Invalid file type. Allowed: {allowed_extensions}"}), 400
        
        # Generate unique clip ID
        clip_id = generate_clip_id()
        
        # Save file
        safe_filename = f"{clip_id}{file_ext}"
        filepath = UPLOAD_FOLDER / safe_filename
        file.save(filepath)
        
        # Get file info
        file_size = filepath.stat().st_size
        file_hash = get_file_hash(filepath)
        
        # Create metadata entry
        clip_data = {
            "clip_id": clip_id,
            "filename": safe_filename,
            "original_filename": file.filename,
            "upload_time": datetime.now().isoformat(),
            "file_size": file_size,
            "file_hash": file_hash,
            "url": f"{BASE_URL}/clips/{clip_id}"
        }
        
        # Update metadata file
        metadata = load_metadata()
        metadata["clips"].append(clip_data)
        save_metadata(metadata)
        
        return jsonify({
            "success": True,
            "clip_id": clip_id,
            "url": f"{BASE_URL}/view/{clip_id}",
            "download_url": f"{BASE_URL}/clips/{clip_id}",
            "message": "Clip uploaded successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/clips', methods=['GET'])
def list_clips():
    """List all uploaded clips"""
    try:
        metadata = load_metadata()
        return jsonify(metadata), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/clips/<clip_id>', methods=['GET'])
def get_clip(clip_id):
    """Download a specific clip"""
    try:
        metadata = load_metadata()
        
        # Find clip
        clip = next((c for c in metadata["clips"] if c["clip_id"] == clip_id), None)
        
        if not clip:
            return jsonify({"error": "Clip not found"}), 404
        
        filepath = UPLOAD_FOLDER / clip["filename"]
        
        if not filepath.exists():
            return jsonify({"error": "File not found on server"}), 404
        
        return send_from_directory(UPLOAD_FOLDER, clip["filename"], as_attachment=False)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/delete/<clip_id>', methods=['DELETE'])
def delete_clip(clip_id):
    """Delete a specific clip"""
    try:
        metadata = load_metadata()
        
        # Find clip
        clip = next((c for c in metadata["clips"] if c["clip_id"] == clip_id), None)
        
        if not clip:
            return jsonify({"error": "Clip not found"}), 404
        
        # Delete file
        filepath = UPLOAD_FOLDER / clip["filename"]
        if filepath.exists():
            filepath.unlink()
        
        # Remove from metadata
        metadata["clips"] = [c for c in metadata["clips"] if c["clip_id"] != clip_id]
        save_metadata(metadata)
        
        return jsonify({
            "success": True,
            "message": f"Clip {clip_id} deleted"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/view/<clip_id>')
def view_clip(clip_id):
    """Serve the web viewer page for a specific clip"""
    # This will be handled by the frontend
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>View Clip - {clip_id}</title>
        <meta http-equiv="refresh" content="0; url=/?clip={clip_id}">
    </head>
    <body>
        <p>Redirecting to viewer...</p>
    </body>
    </html>
    """


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
