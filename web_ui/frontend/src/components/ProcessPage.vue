<template>
  <div class="process-page-container">
    <div class="header-controls">
      <h1>Processing Results</h1>
      <button @click="goBack" class="back-button">Back to OCR</button>
    </div>

    <div class="text-section">
      <h2>Original OCR Text</h2>
      <textarea :value="ocrText" readonly class="text-display ocr-text-display"></textarea>
    </div>

    <div class="text-section">
      <h2>Summarized Text</h2>
      <textarea readonly class="text-display summary-text-display" placeholder="Summarization output will appear here..."></textarea>
      <p v-if="!summarizedText" class="placeholder-message">
        Summarization logic is not yet implemented. This is a placeholder.
      </p>
    </div>

    <div class="text-section">
      <h2>Output Prediction Text</h2>
      <textarea readonly class="text-display prediction-text-display" placeholder="Prediction output will appear here..."></textarea>
      <p v-if="!predictionText" class="placeholder-message">
        Prediction logic is not yet implemented. This is a placeholder.
      </p>
    </div>
  </div>
</template>

<script setup>
import { defineProps, ref } from 'vue';
import { useRouter } from 'vue-router';

const props = defineProps({
  ocrText: {
    type: String,
    default: 'No OCR text received.'
  }
});

const router = useRouter();

// Placeholders for future data
const summarizedText = ref(''); // This would be populated by a summarization function
const predictionText = ref(''); // This would be populated by a prediction function

const goBack = () => {
  router.push({ name: 'Home' }); // Navigate to the route named 'Home' (path: '/')
};

// In a real scenario, you might have functions here to call a backend for summarization/prediction
// e.g., onMounted or when a button is clicked on this page:
// import { onMounted } from 'vue';
// onMounted(async () => {
//   if (props.ocrText) {
//     // summarizedText.value = await fetchSummary(props.ocrText);
//     // predictionText.value = await fetchPrediction(props.ocrText);
//   }
// });
</script>

<style scoped>
.process-page-container {
  padding: 20px;
  font-family: Avenir, Helvetica, Arial, sans-serif;
  color: #2c3e50;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1000px;
  margin: 0 auto; /* Center the content */
}

.header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
  padding-bottom: 15px;
  margin-bottom: 10px;
}

.header-controls h1 {
  margin: 0;
  font-size: 1.8em;
}

.back-button {
  padding: 8px 15px;
  font-size: 1em;
  background-color: #5c6bc0; /* Indigo like */
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.back-button:hover {
  background-color: #3f51b5; /* Darker indigo */
}

.text-section {
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #f9f9f9;
}

.text-section h2 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 1.3em;
  color: #333;
}

.text-display {
  width: 100%;
  min-height: 150px;
  box-sizing: border-box;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 10px;
  font-family: monospace;
  resize: vertical;
  background-color: #fff; /* White background for text areas */
}

.ocr-text-display {
  min-height: 200px; /* OCR text might be longer */
}

.placeholder-message {
  font-style: italic;
  color: #757575; /* Grey */
  margin-top: 10px;
  text-align: center;
}
</style>
