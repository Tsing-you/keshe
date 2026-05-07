// import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
// 导入路由配置
import router from './router'

const app = createApp(App)
// 挂载路由
app.use(router)
app.mount('#app')
