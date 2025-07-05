# Web UI for OLMOCR

This directory contains a Flask backend and a Vue.js (Vite + Vue3) frontend
to provide a web-based interface for the OLMOCR PDF processing tool.

## Project Structure

- `backend/`: Contains the Flask application.
  - `app.py`: The main Flask application file.
  - `requirements.txt`: Python dependencies for the backend.
  - `uploads/`: Directory where uploaded PDF files are temporarily stored.
  - `localworkspace/`: Directory used by the `olmocr.pipeline` for its processing.
- `frontend/`: Contains the Vue.js frontend application.
  - `src/`: Vue application source files.
  - `public/`: Static assets for the frontend.
  - `index.html`: Main HTML file for the Vue app.
  - `package.json`: Node.js dependencies and scripts for the frontend.

## Prerequisites

- Python 3.7+
- Node.js and npm (or yarn)
- The `olmocr` module and its dependencies must be installed in the Python environment you use to run the backend. This includes the OCR model specified in the command (e.g., `scb10x/typhoon-ocr-7b`). Ensure `olmocr` is runnable from the project root (e.g., `python -m olmocr.pipeline ...`).

## Setup and Running

### Backend (Flask)

1.  **Navigate to the backend directory:**
    ```bash
    cd web_ui/backend
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Flask development server:**
    The Flask app `app.py` is configured to run from the `web_ui/backend` directory.
    The OCR command it constructs assumes it's being run from the project root (`../../` from `web_ui/backend`).
    ```bash
    flask run --host=0.0.0.0 --port=5000
    ```
    Or directly:
    ```bash
    python app.py
    ```
    The backend server will start, typically on `http://localhost:5000`.

### Frontend (Vue3 + Vite)

1.  **Navigate to the frontend directory:**
    (From the project root)
    ```bash
    cd web_ui/frontend
    ```

2.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```
    (If you prefer yarn: `yarn install`)

3.  **Run the Vue development server:**
    ```bash
    npm run dev
    ```
    (If you prefer yarn: `yarn dev`)

    The frontend development server will start, typically on `http://localhost:5173` (Vite's default) or another port if 5173 is busy. Open this URL in your browser.

## Usage

1.  Ensure both the backend and frontend servers are running.
2.  Open the frontend URL in your web browser.
3.  Click "Upload PDF" and select a PDF file.
    - The PDF will be previewed on the page.
    - The file will be automatically uploaded to the backend.
4.  Once the file is uploaded and appears in the preview, click the "Run OCR" button.
5.  The OCR text extracted by `olmocr.pipeline` will appear in the text area.

## Notes

-   The Flask backend uses CORS to allow requests from the frontend development server.
-   Uploaded PDFs are stored in `web_ui/backend/uploads/`. You might want to implement a cleanup strategy for these files in a production environment.
-   The `olmocr.pipeline` command is executed by the backend. Ensure the model (`scb10x/typhoon-ocr-7b`) is accessible/downloaded by `olmocr` or adjust the model name in `web_ui/backend/app.py` if needed.
-   Error handling is basic. More robust error reporting and user feedback can be added.
-   For production, the Vue app should be built (`npm run build`) and the static files served by a production-grade web server (or by Flask itself, though less ideal for performance).
