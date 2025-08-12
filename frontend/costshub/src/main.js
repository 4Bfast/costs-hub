import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

// CSS principal com fonte Inter
import './assets/main.css'

// PrimeVue v4 com tema dark
import PrimeVue from 'primevue/config'
import Lara from '@primevue/themes/lara'
import Tooltip from 'primevue/tooltip'
import 'primeicons/primeicons.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
    theme: {
        preset: Lara,
        options: {
            prefix: 'p',
            darkModeSelector: '.p-dark',
            cssLayer: false
        }
    }
})

// Registrar diretiva Tooltip
app.directive('tooltip', Tooltip)

app.mount('#app')
