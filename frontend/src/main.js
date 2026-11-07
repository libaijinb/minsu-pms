import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'  // 必须：EP 组件样式，漏掉会导致按钮/表单/下拉全部裸奔
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import './styles/theme.css'  // 设计系统：C 端品牌色覆盖 Element Plus 默认蓝（须在 EP CSS 之后）

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

for (const [name, comp] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, comp)  // 注册全部图标
}

app.mount('#app')
