<template>
  <div id="app-shell">
    <router-view></router-view>
  </div>
</template>

<script setup>
// This component is now just a shell for the router.
// Global styles that were in the old App.vue might need to be moved
// to style.css or remain here if they are truly global shell styles.
</script>

<style>
/* Global styles previously in App.vue that apply to the overall page structure */
html, body, #app-shell { /* Updated to #app-shell if #app was too generic */
  height: 100%;
  margin: 0;
  padding: 0;
}

#app-shell { /* Ensure this matches the root div's ID */
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  min-height: 100vh; /* Ensure it takes full viewport height */
  display: flex; /* Added to ensure router-view can expand if needed */
  flex-direction: column; /* Added for typical layout */
}

/* Styles that were specific to the content of the old App.vue
   (like .header-row, .upload-section, etc.) have been moved to OcrPage.vue
   and scoped. If any styles were truly global and not component-specific,
   they could remain here or be moved to a global style.css.
   The current style block in OcrPage.vue is scoped, which is good practice.
*/
</style>
