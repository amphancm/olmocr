<template>
  <div id="ocr-page-content"> <!-- Changed id to avoid conflict if #app is global -->
    <div class="header-row">
      <h1>PDF OCR Processor</h1>
      <span class="version-label">v0.15 on 10july2025</span>
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
        <button v-if="showProcessButton" @click="navigateToProcessPage" :disabled="ocrRunning">
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
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router'; // Import useRouter for navigation

import axios from 'axios';

const router = useRouter(); // Initialize router

const pdfFile       = ref(null);
const pdfPreviewUrl = ref('');
const uploadedFilename = ref('');
const pdfUploaded = ref(false);
const ocrRunning  = ref(false);
const uploadError = ref('');
const ocrError    = ref('');

const totalPages  = ref(0);
const pageData    = ref([]);

const timerValue  = ref(0);
const showTimer   = ref(false);
const timerStatus = ref('stopped');
let timerInterval = null;

// Reactive variables for the "Process" button logic
const ocrCompletedSuccessfully = ref(false);
const showProcessButton = ref(false);

const FLASK_BASE_URL = 'https://deepseax.natachat.com';

const handleFileChange = async (event) => {
  const file = event.target.files[0];
  if (file && file.type === 'application/pdf') {
    pdfFile.value     = file;
    pdfUploaded.value = false;
    uploadError.value = '';
    ocrError.value    = '';

    // Reset states for new file
    ocrCompletedSuccessfully.value = false;
    showProcessButton.value = false;
    totalPages.value = 0;
    pageData.value = [];
    if (timerInterval) clearInterval(timerInterval);
    showTimer.value = false;
    timerValue.value = 0;


    pdfPreviewUrl.value = URL.createObjectURL(file);
    await uploadPdf();
  } else {
    pdfFile.value          = null;
    pdfPreviewUrl.value    = '';
    uploadedFilename.value = '';
    pdfUploaded.value      = false;
    uploadError.value      = 'Please select a valid PDF file.';
    ocrCompletedSuccessfully.value = false;
    showProcessButton.value = false;
  }
};

const uploadPdf = async () => {
  if (!pdfFile.value) return;
  const formData = new FormData();
  formData.append('file', pdfFile.value);

  // Reset relevant states before new upload attempt
  ocrCompletedSuccessfully.value = false;
  showProcessButton.value = false;
  ocrError.value = ''; // Clear previous OCR errors specifically

  try {
    uploadError.value = ''; // Clear upload error before attempt
    const response = await axios.post(`${FLASK_BASE_URL}/api/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    uploadedFilename.value = response.data.filename;
    pdfUploaded.value = true;
    console.log('File uploaded:', response.data.filename);

    const infoResponse = await axios.get(`${FLASK_BASE_URL}/api/pdf-info/${response.data.filename}`);
    totalPages.value = infoResponse.data.totalPages;
    pageData.value = Array.from({ length: totalPages.value }, (_, i) => ({
      pageNum: i + 1, status: 'pending', text: ''
    }));
  } catch (error) {
    console.error('Error during upload or fetching PDF info:', error);
    pdfUploaded.value = false;
    totalPages.value = 0;
    pageData.value = [];
    if (error.response) {
      uploadError.value = `Upload failed: ${error.response.data.error || 'Server error'}`;
    } else {
      uploadError.value = 'Upload failed: Network error or server not reachable.';
    }
  }
};

const runOCR = async () => {
  if (!pdfUploaded.value || !uploadedFilename.value) {
    ocrError.value = 'PDF has not been successfully uploaded yet.';
    return;
  }

  // Reset states for new OCR run
  ocrError.value = '';
  ocrCompletedSuccessfully.value = false;
  showProcessButton.value = false;
  pageData.value.forEach(p => {
    p.status = 'pending';
    p.text = '';
  });

  showTimer.value = true;
  timerValue.value = 0;
  timerStatus.value = 'running';
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => { timerValue.value++; }, 1000);

  ocrRunning.value = true;

  fetch(`${FLASK_BASE_URL}/api/ocr-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
    body: JSON.stringify({ filename: uploadedFilename.value })
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(errData => { throw new Error(`Server error: ${response.status}. ${errData.error || JSON.stringify(errData)}`); })
                     .catch(() => { throw new Error(`Server error: ${response.status} ${response.statusText}.`); });
    }
    if (!response.body) throw new Error('Response body is null.');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    function streamData() {
      reader.read().then(({ done, value }) => {
        if (done) {
          console.log('Stream completed.');
          if (ocrRunning.value) {
             ocrRunning.value = false;
             if (timerInterval) clearInterval(timerInterval);
             timerStatus.value = 'stopped';

             // Final check for success after stream completion
             if (aggregatedOcrText.value && !ocrError.value) {
               ocrCompletedSuccessfully.value = true;
               showProcessButton.value = true;
             } else {
               ocrCompletedSuccessfully.value = false;
               showProcessButton.value = false;
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
                    pageData.value = Array.from({ length: data.totalPages }, (_, i) => ({ pageNum: i + 1, status: 'pending', text: '' }));
                  }
                  if (data.error) {
                    ocrError.value = `Pipeline init error: ${data.error}`;
                    ocrRunning.value = false; if (timerInterval) clearInterval(timerInterval); timerStatus.value = 'stopped'; reader.cancel();
                  }
                } else if (data.type === 'page_event') {
                  const page = pageData.value.find(p => p.pageNum === data.page);
                  if (page) page.status = data.status;
                } else if (data.type === 'page_result') {
                  const page = pageData.value.find(p => p.pageNum === data.page);
                  if (page) { page.status = data.status; page.text = data.text || ''; }
                } else if (data.type === 'summary') {
                  console.log('OCR Summary:', data);
                  if (data.status === 'error' || data.status === 'error_rate_exceeded' || data.total_errors > 0) {
                    if (!ocrError.value) ocrError.value = `OCR completed with ${data.total_errors} errors. Status: ${data.status}.`;
                    // ocrCompletedSuccessfully.value = false; // Ensure this is false
                    // showProcessButton.value = false;
                  } else if (aggregatedOcrText.value) { // Success and has text
                    // ocrCompletedSuccessfully.value = true;
                    // showProcessButton.value = true;
                  } else { // Succeeded but no text somehow
                     // ocrCompletedSuccessfully.value = false;
                     // showProcessButton.value = false;
                  }
                  ocrRunning.value = false; if (timerInterval) clearInterval(timerInterval); timerStatus.value = 'stopped';
                } else if (data.type === 'error') {
                  ocrError.value = data.message + (data.details ? ` Details: ${data.details}` : '');
                  ocrRunning.value = false; if (timerInterval) clearInterval(timerInterval); timerStatus.value = 'stopped'; reader.cancel();
                  // ocrCompletedSuccessfully.value = false;
                  // showProcessButton.value = false;
                }
              } catch (e) { console.error('Error parsing SSE JSON:', e, 'Received:', jsonString); }
            }
          }
        });
        streamData();
      }).catch(error => {
        console.error('Error reading from stream:', error);
        ocrError.value = `Stream reading error: ${error.message}`;
        ocrRunning.value = false; if (timerInterval) clearInterval(timerInterval); timerStatus.value = 'stopped';
        // ocrCompletedSuccessfully.value = false;
        // showProcessButton.value = false;
      });
    }
    streamData();
  })
  .catch(error => {
    console.error('Error setting up OCR stream:', error);
    ocrError.value = `Failed to start OCR: ${error.message}`;
    ocrRunning.value = false; if (timerInterval) clearInterval(timerInterval); timerStatus.value = 'stopped';
    // ocrCompletedSuccessfully.value = false;
    // showProcessButton.value = false;
  });
};

const aggregatedOcrText = computed(() => {
  return pageData.value
    .filter(p => (p.status === 'success' || p.status === 'success_fallback') && p.text)
    .map(p => `--- Page ${p.pageNum} ---\n${p.text}`)
    .join('\n\n');
});

const navigateToProcessPage = () => {
  if (ocrCompletedSuccessfully.value && aggregatedOcrText.value) {
    router.push({ name: 'Process', query: { ocrText: aggregatedOcrText.value } });
  } else {
    console.warn("Navigation to process page aborted: OCR not successful or no text.");
    // Optionally, provide user feedback here if the button was somehow visible yet conditions not met
    // For example, if the button was visible but aggregatedOcrText became empty due to some race condition (unlikely here)
    // or if ocrCompletedSuccessfully was true but there's no text.
    if (!aggregatedOcrText.value) {
        ocrError.value = "Cannot process: No text was extracted from the OCR.";
    } else if (!ocrCompletedSuccessfully.value) {
        ocrError.value = "Cannot process: OCR was not completed successfully.";
    }
  }
};

</script>

<style scoped> /* Changed to scoped to ensure styles are for this component */
/* Styles from App.vue, assuming they are relevant for this page layout */
#ocr-page-content { /* Ensure this matches the root element's id/class if needed for specific global styles */
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  /* min-height: 100vh; */ /* This might be handled by App.vue now */
  /* min-width: 100vw; */ /* This might be handled by App.vue now */
  box-sizing: border-box;
  padding: 0 10px; /* Or adjust as needed if App.vue provides padding */
  display: flex;
  flex-direction: column;
}

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
  max-height: 200px;
  overflow-y: auto;
}

.page-status-container li {
  padding: 5px 0;
  border-bottom: 1px solid #eee;
}
.page-status-container li:last-child {
  border-bottom: none;
}

.status-pending { color: #757575; }
.status-processing { color: #1976D2; }
.status-success { color: #388E3C; }
.status-success_fallback { color: #FFA000; }
.status-error { color: #D32F2F; }
.status-skipped { color: #7B1FA2; }

.page-error-details {
  font-style: italic;
  font-size: 0.9em;
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
  /* #ocr-page-content might need adjustment if App.vue's #app style was applying padding */
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
