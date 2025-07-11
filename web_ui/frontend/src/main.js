import { createApp } from 'vue'
import './style.css'
import App from './App.vue' // This is the root App component
import router from './router' // Import the router

const app = createApp(App); // Create the app instance with the root App component
app.use(router); // Tell Vue to use the router
app.mount('#app');
