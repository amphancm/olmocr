import { createRouter, createWebHistory } from 'vue-router';
import OcrPage from '../components/OcrPage.vue';
// ProcessPage will be created and imported in a later step

const routes = [
  {
    path: '/',
    name: 'Home',
    component: OcrPage,
  },
  {
    path: '/process',
    name: 'Process',
    // component: ProcessPage, // This will be uncommented/added when ProcessPage.vue is created
    component: () => import('../components/ProcessPage.vue'), // Lazy load; component to be created
    props: route => ({ ocrText: route.query.ocrText })
    // Consider using route.params if passing large data, or Pinia for state management
    // For now, query param is fine for text.
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL), // Added import.meta.env.BASE_URL for Vite
  routes,
});

export default router;
