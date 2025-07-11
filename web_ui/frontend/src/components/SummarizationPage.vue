<template>
  <div class="summarization-page">
    <h1>Summary and Prediction</h1>

    <div class="section">
      <h2>Summarization</h2>
      <textarea v-model="summaryText" readonly placeholder="Summary will appear here..."></textarea>
    </div>

    <div class="section">
      <h2>Prediction</h2>
      <textarea v-model="predictionText" readonly placeholder="Prediction output will appear here..."></textarea>
    </div>

    <button @click="goBack">Back to OCR</button>
  </div>
</template>

<script setup>
import { ref, defineEmits } from 'vue';

const emit = defineEmits(['go-back']);

const summaryText    = ref('Placeholder summary text. This will be replaced with actual summarized content.');
const predictionText = ref('Placeholder prediction text. This will be replaced with the model\'s prediction.');

const goBack = () => {
  emit('go-back');
};
</script>

<style scoped>
.summarization-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
  gap: 20px;
  box-sizing: border-box;
}

h1 {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 20px;
}

.section {
  width: 100%;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.section h2 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

textarea {
  width: 100%;
  min-height: 150px;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  font-family: monospace;
  font-size: 0.9em;
  resize: vertical;
  background-color: #fff;
}

button {
  padding: 10px 20px;
  font-size: 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s;
  margin-top: 20px;
}

button:hover {
  background-color: #0056b3;
}

/* Responsive Design */
@media (max-width: 768px) {
  .summarization-page {
    padding: 15px;
  }

  .section {
    padding: 15px;
  }

  textarea {
    min-height: 120px;
    font-size: 0.85em;
  }

  button {
    font-size: 15px;
    padding: 8px 16px;
  }
}

@media (max-width: 480px) {
  h1 {
    font-size: 1.5em;
  }
  .section h2 {
    font-size: 1.1em;
  }
  textarea {
    min-height: 100px;
  }
}
</style>
