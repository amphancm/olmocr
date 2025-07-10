import os
import logging
import subprocess
from flask_cors import CORS
from flask import Flask, request, jsonify, send_from_directory


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

UPLOAD_FOLDER          = 'uploads'
LOCAL_WORKSPACE_FOLDER = 'localworkspace'
ALLOWED_EXTENSIONS     = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['LOCAL_WORKSPACE_FOLDER'] = LOCAL_WORKSPACE_FOLDER

# Ensure upload and workspace directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOCAL_WORKSPACE_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        logger.warning("No file part in request")
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        logger.warning("No selected file")
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        original_filename = file.filename # In a real app, sanitize this
        filename = original_filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Handle duplicate filenames
        counter = 1
        name, ext = os.path.splitext(filename)
        while os.path.exists(filepath):
            filename = f"{name}_{counter}{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter += 1
            
        try:
            file.save(filepath)
            logger.info(f"File '{filename}' uploaded successfully to '{filepath}'")
            return jsonify({"message": "File uploaded successfully", "filename": filename}), 200
        except Exception as e:
            logger.error(f"Error saving file '{filename}': {e}")
            return jsonify({"error": f"Error saving file: {e}"}), 500
    else:
        logger.warning(f"File type not allowed: {file.filename}")
        return jsonify({"error": "File type not allowed"}), 400

@app.route('/api/ocr', methods=['POST'])
def ocr_file():
    data = request.get_json()
    if not data or 'filename' not in data:
        logger.warning("No filename provided for OCR")
        return jsonify({"error": "No filename provided"}), 400

    filename = data['filename']
    # Basic security check: ensure filename is not trying to escape the uploads directory
    if ".." in filename or filename.startswith("/"):
        logger.warning(f"Invalid filename for OCR: {filename}")
        return jsonify({"error": "Invalid filename"}), 400

    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(pdf_path):
        logger.warning(f"PDF file not found for OCR: {pdf_path}")
        return jsonify({"error": "PDF file not found"}), 404

    # The command expects paths relative to where it's run.
    # We are in web_ui/backend/, so uploads/ is ./uploads and localworkspace/ is ./localworkspace
    # The olmocr module is in the parent directory.
    # The command needs to be run from the project root for `python -m olmocr.pipeline` to work
    # Or, we adjust python path or call the script directly.
    # For simplicity, let's assume `python -m olmocr.pipeline` can be found if we run from backend/
    # and the module path is correctly set up in the environment.
    # Paths for the command:
    #   localworkspace: ./localworkspace (relative to backend/)
    #   pdfs: ./uploads/<filename> (relative to backend/)

    # Command construction
    # Assuming olmocr is installed in the environment or PYTHONPATH is set up
    # The module `olmocr.pipeline` is in the parent directory from `web_ui/backend`
    # We need to run the command from the root of the project for `python -m olmocr.pipeline` to work as intended.
    # The paths in the command should be relative to the project root.

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    # Correct paths relative to project_root
    olmocr_workspace_path     = os.path.join('web_ui', 'backend', LOCAL_WORKSPACE_FOLDER)
    pdf_file_path_for_command = os.path.join('web_ui', 'backend', UPLOAD_FOLDER, filename)

    # Command to be executed from project_root
    # Make sure the model name is correct and it's accessible
    command = [
        "python", "-m", "olmocr.pipeline",
        olmocr_workspace_path,
        "--pdfs", pdf_file_path_for_command,
        "--model", "Adun/olmOCR-7B-thai-v3.2", 
        "--output-to-stdout"
    ]

    logger.info(f"Running OCR command: {' '.join(command)}")
    logger.info(f"Executing from directory: {project_root}")

    try:
        # Execute the command from the project root
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=project_root)
        stdout, stderr = process.communicate(timeout=300) # 5 minutes timeout

        if process.returncode == 0:
            logger.info(f"OCR command successful for '{filename}'. Output length: {len(stdout)}")
            # Clean up the uploaded file after successful OCR
            # os.remove(pdf_path) # Optional: remove file after processing
            return jsonify({"ocr_text": stdout}), 200
        else:
            logger.error(f"OCR command failed for '{filename}'. Return code: {process.returncode}")
            logger.error(f"Stderr: {stderr}")
            return jsonify({"error": "OCR processing failed", "details": stderr}), 500
    except subprocess.TimeoutExpired:
        logger.error(f"OCR command timed out for '{filename}'")
        process.kill()
        stdout, stderr = process.communicate()
        return jsonify({"error": "OCR command timed out", "details": stderr}), 500
    except Exception as e:
        logger.error(f"Exception during OCR processing for '{filename}': {e}")
        return jsonify({"error": f"An error occurred during OCR processing: {e}"}), 500

# Simple endpoint to serve uploaded PDFs to be displayed in an iframe
@app.route('/uploads/<filename>')
def send_uploaded_file(filename):
    # Security: Ensure filename is safe and only serves from UPLOAD_FOLDER
    if ".." in filename or filename.startswith("/"):
        return "Invalid filename", 400

    logger.info(f"Serving file: {filename} from {app.config['UPLOAD_FOLDER']}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
