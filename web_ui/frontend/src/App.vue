<template>
  <div id="app">
    <h1>PDF OCR Processor</h1>

    <div class="upload-section">
      <label for="file-input">Upload PDF:</label>
      <input type="file" id="file-input" @change="handleFileChange" accept=".pdf" />
    </div>

    <div v-if="pdfFile" class="viewer-section">
      <button @click="runOCR" :disabled="ocrRunning || !pdfUploaded">
        {{ ocrRunning ? 'Processing...' : 'Run OCR' }}
      </button>
      <p v-if="uploadError" class="error-message">{{ uploadError }}</p>
      <p v-if="ocrError" class="error-message">OCR Error: {{ ocrError }}</p>
    </div>

    <div class="content-display">
      <div class="pdf-viewer">
        <h2>PDF Preview</h2>
        <iframe v-if="pdfPreviewUrl" :src="pdfPreviewUrl" width="100%" height="500px"></iframe>
        <p v-else>Select a PDF file to preview.</p>
      </div>

      <div class="ocr-output">
        <h2>OCR Text</h2>
        <textarea v-model="ocrText" readonly placeholder="OCR output will appear here..."></textarea>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const pdfFile       = ref(null);
const pdfPreviewUrl = ref('');
const uploadedFilename = ref('');
const pdfUploaded = ref(false);
const ocrText     = ref('');
const ocrRunning  = ref(false);
const uploadError = ref('');
const ocrError    = ref('');

const FLASK_BASE_URL = 'http://localhost:5000'; // Assuming Flask runs on port 5000

const handleFileChange = async (event) => {
  const file = event.target.files[0];
  if (file && file.type === 'application/pdf') {
    pdfFile.value     = file;
    pdfUploaded.value = false;
    ocrText.value     = ''; // Clear previous OCR text
    uploadError.value = '';
    ocrError.value    = '';

    // Create a URL for the iframe preview
    pdfPreviewUrl.value = URL.createObjectURL(file);

    // Immediately upload the file
    await uploadPdf();
  } else {
    pdfFile.value = null;
    pdfPreviewUrl.value = '';
    uploadedFilename.value = '';
    pdfUploaded.value = false;
    uploadError.value = 'Please select a valid PDF file.';
  }
};

const uploadPdf = async () => {
  if (!pdfFile.value) return;

  const formData = new FormData();
  formData.append('file', pdfFile.value);

  try {
    uploadError.value = '';
    const response = await axios.post(`${FLASK_BASE_URL}/api/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    uploadedFilename.value = response.data.filename;
    pdfUploaded.value = true;
    // Update iframe to point to the served PDF after successful upload,
    // so it works even if object URL has issues or for consistency.
    // pdfPreviewUrl.value = `${FLASK_BASE_URL}/uploads/${response.data.filename}`;
    // Sticking with object URL for immediate preview, flask endpoint is a fallback or for non-browser display
    console.log('File uploaded:', response.data.filename);
  } catch (error) {
    console.error('Error uploading file:', error);
    pdfUploaded.value = false;
    if (error.response) {
      uploadError.value = `Upload failed: ${error.response.data.error || 'Server error'}`;
    } else {
      uploadError.value = 'Upload failed: Network error or server not reachable.';
    }
    // Clear preview if upload fails
    // pdfPreviewUrl.value = ''; // Keep preview for now, user can re-attempt OCR
  }
};

const runOCR = async () => {
  if (!pdfUploaded.value || !uploadedFilename.value) {
    ocrError.value = 'PDF has not been successfully uploaded yet.';
    return;
  }

  ocrRunning.value = true;
  ocrError.value = '';
  ocrText.value = '';

  try {
    const response = await axios.post(`${FLASK_BASE_URL}/api/ocr`, {
      filename: uploadedFilename.value,
    });
    ocrText.value = response.data.ocr_text;
    ocrError.value = ''; // Explicitly clear error on successful data retrieval
  } catch (error) {
    console.error('Error running OCR:', error);
    if (error.response) {
      ocrError.value = `OCR failed: ${error.response.data.error || 'Server error'}. Details: ${error.response.data.details || ''}`;
    } else {
      ocrError.value = 'OCR failed: Network error or server not reachable.';
    }
    ocrText.value = ''; // Clear any partial OCR text if an error occurred
  } finally {
    ocrRunning.value = false;
  }
};

</script>

<style>
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
}

#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  min-height: 100vh;
  min-width: 100vw;
  box-sizing: border-box;
  margin: 0;
  padding: 0 10px;
  display: flex;
  flex-direction: column;
}

h1 {
  text-align: center;
  margin-top: 20px;
}

.upload-section,
.viewer-section {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #f9f9f9;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.viewer-section {
  background-color: #f0f0f0;
  text-align: center;
}

.viewer-section button {
  padding: 10px 20px;
  font-size: 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.viewer-section button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.viewer-section button:hover:not(:disabled) {
  background-color: #45a049;
}

.content-display {
  display: flex;
  gap: 20px;
  flex: 1 1 0;
  min-height: 0;
  margin-bottom: 20px;
}

.pdf-viewer, .ocr-output {
  flex: 1 1 0;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  min-width: 0;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.pdf-viewer h2, .ocr-output h2 {
  margin-top: 0;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
  margin-bottom: 15px;
}

.ocr-output textarea {
  width: 100%;
  height: 100%;
  min-height: 200px;
  box-sizing: border-box;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 10px;
  font-family: monospace;
  resize: vertical;
  flex: 1 1 0;
}

iframe {
  border: 1px solid #ccc;
  width: 100%;
  height: 500px;
  flex: 1 1 0;
}

.error-message {
  color: red;
  margin-top: 10px;
}

/* Responsive Design */
@media (max-width: 900px) {
  .content-display {
    flex-direction: column;
    gap: 10px;
  }
  .pdf-viewer, .ocr-output {
    min-width: 0;
    width: 100%;
  }
  iframe, .ocr-output textarea {
    height: 300px;
  }
}

@media (max-width: 600px) {
  #app {
    padding: 0 2px;
  }
  .upload-section,
  .viewer-section {
    padding: 10px;
    max-width: 100%;
  }
  .pdf-viewer, .ocr-output {
    padding: 10px;
  }
  iframe, .ocr-output textarea {
    height: 200px;
  }
}
</style>