<template>
  <div id="app">
    <!-- Conditionally render SummarizationPage or the main content -->
    <SummarizationPage v-if="showSummarizationPage" @go-back="showSummarizationPage = false" />

    <div v-else> <!-- Main OCR content -->
      <div class="header-row">
        <h1>PDF OCR Processor</h1>
        <span class="version-label">v0.15 on 11july2025</span>
      </div>

      <div class="upload-section">
        <label for="file-input">Upload PDF:</label>
        <input type="file" id="file-input" @change="handleFileChange" accept=".pdf" />
      </div>

      <div v-if="pdfFile" class="viewer-section">
        <div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
          <button @click="runOCR" :disabled="ocrRunning || !pdfUploaded">
            {{ ocrRunning ? 'Processing...' : 'Run OCR' }}
          </button>
          <button @click="navigateToProcessPage" v-if="ocrCompleted && aggregatedOcrText" class="process-button" style="margin-left: 10px;">
            Process Text
          </button>
          <span v-if="showTimer" :class="timerStatus === 'running' ? 'timer-running' : 'timer-stopped'" style="margin-left: 10px;">
            Timer: {{ timerValue }}s
          </span>
        </div>
        <p v-if="uploadError" class="error-message">{{ uploadError }}</p>
        <p v-if="ocrError" class="error-message">OCR Error: {{ ocrError }}</p>
        <p v-if="totalPages > 0">Total Pages: {{ totalPages }}</p>
      </div>

      <!-- <div v-if="totalPages > 0 && pageData.length > 0" class="page-status-container">
        <h2>Page Processing Status</h2>
        <ul>
          <li v-for="page in pageData" :key="page.pageNum" :class="`status-${page.status}`">
            Page {{ page.pageNum }}: {{ page.status }}
            <span v-if="page.status === 'error'" class="page-error-details"> - Check console for details if any.</span>
          </li>
        </ul>
      </div> -->

      <div class="content-display">
        <div class="pdf-viewer">
          <h2>PDF Preview</h2>
          <iframe v-if="pdfPreviewUrl" :src="pdfPreviewUrl" width="100%" height="500px"></iframe>
          <p v-else>Select a PDF file to preview.</p>
        </div>

        <div class="ocr-output">
          <h2>OCR Text</h2>
          <textarea v-model="aggregatedOcrText" readonly placeholder="OCR output will appear here..."></textarea>
        </div>
      </div>
    </div> <!-- End of Main OCR content -->
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'; // Import computed
import axios from 'axios';
import SummarizationPage from './components/SummarizationPage.vue'; // Import the new component

const pdfFile       = ref(null);
const pdfPreviewUrl = ref('');
const uploadedFilename = ref('');
const pdfUploaded = ref(false);
const ocrText     = ref('');
const ocrRunning  = ref(false);
const ocrCompleted = ref(false); // Added to track OCR completion for Process button
const uploadError = ref('');
const ocrError    = ref('');
const showSummarizationPage = ref(false); // For conditional rendering

// New reactive variables for multi-page handling
const totalPages  = ref(0);
const pageData    = ref([]); // To store { pageNum: number, status: string, text: string }

// Timer related reactive variables
const timerValue  = ref(0);
const showTimer   = ref(false);
const timerStatus = ref('stopped'); // Can be 'running' or 'stopped'
let timerInterval = null; // To store the interval ID

const FLASK_BASE_URL = 'https://deepseax.natachat.com'; // Assuming Flask runs on port 5000

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
    pdfFile.value          = null;
    pdfPreviewUrl.value    = '';
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
    console.log('File uploaded:', response.data.filename);

    // Fetch PDF info (total pages)
    try {
      const infoResponse = await axios.get(`${FLASK_BASE_URL}/api/pdf-info/${response.data.filename}`);
      totalPages.value = infoResponse.data.totalPages;
      // Initialize pageData based on totalPages
      pageData.value = Array.from({ length: totalPages.value }, (_, i) => ({
        pageNum: i + 1,
        status: 'pending', // Possible statuses: pending, processing, success, success_fallback, error, skipped
        text: ''
      }));
    } catch (infoError) {
      console.error('Error fetching PDF info:', infoError);
      uploadError.value += ` Could not fetch PDF info: ${infoError.response?.data?.error || infoError.message}.`;
      totalPages.value = 0;
      pageData.value = [];
    }

  } catch (error) {
    console.error('Error uploading file:', error);
    pdfUploaded.value = false;
    totalPages.value = 0;
    pageData.value = [];
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

  // Start timer
  showTimer.value = true;
  timerValue.value = 0;
  timerStatus.value = 'running'; // Timer is now running
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    timerValue.value++;
  }, 1000);

  ocrRunning.value = true;
  ocrError.value = '';
  ocrCompleted.value = false; // Reset before new OCR run
  // ocrText.value = ''; // This will be handled by aggregatedOcrText

  // Reset pageData statuses
  pageData.value.forEach(p => {
    p.status = 'pending'; // Reset to pending before new run
    p.text = '';
  });

  // Using fetch for POST request that returns a stream (SSE)
  fetch(`${FLASK_BASE_URL}/api/ocr-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream'
    },
    body: JSON.stringify({ filename: uploadedFilename.value })
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(errData => {
        throw new Error(`Server error: ${response.status}. ${errData.error || JSON.stringify(errData)}`);
      }).catch(() => {
        throw new Error(`Server error: ${response.status} ${response.statusText}.`);
      });
    }
    if (!response.body) {
      throw new Error('Response body is null, cannot read stream.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    function streamData() {
      reader.read().then(({ done, value }) => {
        if (done) {
          console.log('Stream completed.');
          if (ocrRunning.value) { // If not already set to false by a summary or error event
             ocrRunning.value = false;
             if (timerInterval) clearInterval(timerInterval);
             timerStatus.value = 'stopped';
              // Set ocrCompleted to true if there's text and no critical error was flagged by summary
              const successTextExists = pageData.value.some(p => (p.status === 'success' || p.status === 'success_fallback') && p.text && p.text.trim().length > 0);
              if (successTextExists && !ocrError.value) { // Check ocrError in case summary already set it
                 ocrCompleted.value = true;
              } else if (!ocrError.value) { // If no text and no prior error, set a generic one
                 ocrError.value = "OCR process finished, but no text was extracted or an error occurred before summary.";
                 ocrCompleted.value = false;
              }
          }
          return;
        }

        const chunk = decoder.decode(value, { stream: true });
        const eventMessages = chunk.split('\n\n');

        eventMessages.forEach(eventMessage => {
          if (eventMessage.startsWith('data: ')) {
            const jsonString = eventMessage.substring(6).trim();
            if (jsonString) {
              try {
                const data = JSON.parse(jsonString);
                console.log('SSE data:', data);

                if (data.type === 'info') {
                  if (data.totalPages > 0 && totalPages.value !== data.totalPages) {
                    totalPages.value = data.totalPages;
                    pageData.value = Array.from({ length: data.totalPages }, (_, i) => ({
                      pageNum: i + 1, status: 'pending', text: ''
                    }));
                  }
                  if (data.error) { // Early error from pipeline (e.g. PDF read error)
                    ocrError.value = `Pipeline init error: ${data.error}`;
                    ocrRunning.value = false;
                    if (timerInterval) clearInterval(timerInterval); timerStatus.value = 'stopped';
                    reader.cancel(); // Stop the stream
                  }
                } else if (data.type === 'page_event') {
                  const page = pageData.value.find(p => p.pageNum === data.page);
                  if (page) page.status = data.status; // e.g., 'processing'
                } else if (data.type === 'page_result') {
                  const page = pageData.value.find(p => p.pageNum === data.page);
                  if (page) {
                    page.status = data.status; // success, success_fallback, error, skipped
                    page.text = data.text || '';
                    // Optionally log or display per-page errors more prominently
                    if (data.status === 'error' && data.message && !ocrError.value) {
                       // console.warn(`Error on page ${data.page}: ${data.message}`);
                       // ocrError.value = `Error on page ${data.page}: ${data.message}`; // This might be too noisy
                    }
                  }
                } else if (data.type === 'summary') {
                  console.log('OCR Summary:', data);
                  if (data.status === 'error' || data.status === 'error_rate_exceeded' || data.total_errors > 0) {
                    if (!ocrError.value) ocrError.value = `OCR process completed with ${data.total_errors} errors. Status: ${data.status}.`;
                     ocrCompleted.value = false; // OCR had errors or did not complete fully with text
                   } else {
                     // Check if there is actually text from successful pages
                     const successTextExists = pageData.value.some(p => (p.status === 'success' || p.status === 'success_fallback') && p.text && p.text.trim().length > 0);
                     if (successTextExists) {
                         ocrCompleted.value = true;
                     } else {
                         ocrCompleted.value = false;
                         if (!ocrError.value) ocrError.value = "OCR process finished, but no text was extracted.";
                     }
                  }
                  ocrRunning.value = false; // Mark as not running once summary is received
                  if (timerInterval) clearInterval(timerInterval); timerStatus.value = 'stopped';
                } else if (data.type === 'error') { // General stream error from backend
                  ocrError.value = data.message + (data.details ? ` Details: ${data.details}` : '');
                   ocrCompleted.value = false;
                  ocrRunning.value = false;
                  if (timerInterval) clearInterval(timerInterval); timerStatus.value = 'stopped';
                  reader.cancel(); // Stop the stream
                }
              } catch (e) {
                console.error('Error parsing SSE JSON:', e, 'Received:', jsonString);
              }
            }
          }
        });
        streamData(); // Continue reading
      }).catch(error => {
        console.error('Error reading from stream:', error);
        ocrError.value = `Stream reading error: ${error.message}`;
        ocrRunning.value = false;
        if (timerInterval) clearInterval(timerInterval); timerStatus.value = 'stopped';
         ocrCompleted.value = false; // Error in stream
      });
    }
    streamData(); // Start reading the stream
  })
  .catch(error => {
    console.error('Error setting up OCR stream:', error);
    ocrError.value = `Failed to start OCR: ${error.message}`;
    ocrRunning.value = false;
    if (timerInterval) clearInterval(timerInterval);
    timerStatus.value = 'stopped';
    ocrCompleted.value = false; // Error setting up stream
  });
};

const navigateToProcessPage = () => {
  console.log('Navigating to process page...');
  showSummarizationPage.value = true;
};

const aggregatedOcrText = computed(() => {
  // Concatenate text from all pages that have a success status
  return pageData.value
    .filter(p => (p.status === 'success' || p.status === 'success_fallback') && p.text)
    .map(p => `--- Page ${p.pageNum} ---\n${p.text}`) // Add page separator for clarity
    .join('\n\n');
});

</script>

<style>
.page-status-container {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #f9f9f9;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.page-status-container h2 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 1.2em;
}

.page-status-container ul {
  list-style-type: none;
  padding: 0;
  max-height: 200px; /* Example max height for scroll */
  overflow-y: auto; /* Enable scroll if content overflows */
}

.page-status-container li {
  padding: 5px 0;
  border-bottom: 1px solid #eee;
}
.page-status-container li:last-child {
  border-bottom: none;
}

/* Status-specific styling */
.status-pending { color: #757575; } /* Grey */
.status-processing { color: #1976D2; } /* Blue */
.status-success { color: #388E3C; } /* Green */
.status-success_fallback { color: #FFA000; } /* Amber */
.status-error { color: #D32F2F; } /* Red */
.status-skipped { color: #7B1FA2; } /* Purple */

.page-error-details {
  font-style: italic;
  font-size: 0.9em;
}


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

.header-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
  margin-bottom: 0;
}

.header-row h1 {
  margin: 0;
}

.version-label {
  font-size: 1.1em;
  color: #888;
  margin-left: 10px;
  font-weight: normal;
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

.viewer-section .process-button {
  background-color: #007bff; /* Blue */
}

.viewer-section .process-button:hover:not(:disabled) {
  background-color: #0056b3; /* Darker Blue */
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

.timer-running {
  color: green;
}

.timer-stopped {
  color: red;
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
