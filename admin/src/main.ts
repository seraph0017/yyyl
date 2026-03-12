// 一月一露 — Web管理后台入口
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import { useUserStore } from './stores/user'

// 样式
import 'element-plus/dist/index.css'
import './styles/index.scss'

const app = createApp(App)

// Pinia
const pinia = createPinia()
app.use(pinia)

// 初始化用户状态
const userStore = useUserStore()
userStore.initUser()

// Element Plus
app.use(ElementPlus, { locale: zhCn })

// 注册所有Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// Router
app.use(router)

app.mount('#app')
