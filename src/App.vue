<script setup>
import { computed, ref, onMounted, onUnmounted, nextTick } from 'vue'
import axios from 'axios'
import { useRouter, RouterView } from 'vue-router'
import api from './api'
import { toasts } from './utils/toast'
import { showToast } from './utils/toast'

const router = useRouter()
const showDropdown = ref(false)
const userState = ref(null)
const helpOpen = ref(false)
const helpQuestion = ref('')
const helpLoading = ref(false)
const helpChatRef = ref(null)
const helpMessages = ref([
  {
    role: 'assistant',
    content: '你好，我是系统帮助助手。你可以问我登录、下单、接单、商家管理、接口调用或开发启动相关的问题。',
  },
])

const readUser = () => {
  try {
    userState.value = JSON.parse(localStorage.getItem('user') || 'null')
  } catch (e) {
    userState.value = null
  }
}

const user = computed(() => userState.value)
const currentRoutePath = computed(() => router.currentRoute.value.fullPath)

const helpSuggestions = computed(() => {
  const common = ['如何注册或登录', '系统支持哪些角色', '如何查看我的订单']
  if (!user.value) {
    return [...common, '这个系统是做什么的', '如何开始使用这个项目']
  }
  if (user.value.role === 'customer') {
    return [...common, '普通用户如何下单', '如何添加收货地址', '如何评价订单']
  }
  if (user.value.role === 'rider') {
    return [...common, '骑手如何接单', '如何标记送达', '如何查看评价统计']
  }
  return [...common, '商家如何上架菜品', '如何切换营业状态', '如何查看经营分析']
})

const toggleDropdown = () => {
    showDropdown.value = !showDropdown.value
}

const closeDropdown = (e) => {
    if (!e.target.closest('.user-menu-wrapper')) {
        showDropdown.value = false
    }
}

const syncSession = () => {
  readUser()
}

const scrollHelpToBottom = async () => {
  await nextTick()
  if (helpChatRef.value) {
    helpChatRef.value.scrollTop = helpChatRef.value.scrollHeight
  }
}

const openHelp = async () => {
  helpOpen.value = true
  await scrollHelpToBottom()
}

const closeHelp = () => {
  helpOpen.value = false
}

const useSuggestion = (text) => {
  helpQuestion.value = text
}

const resetHelp = () => {
  helpQuestion.value = ''
  helpMessages.value = [
    {
      role: 'assistant',
      content: '你好，我是系统帮助助手。你可以问我登录、下单、接单、商家管理、接口调用或开发启动相关的问题。',
    },
  ]
}

const sendHelp = async () => {
  const question = helpQuestion.value.trim()
  if (!question) {
    showToast('请先输入问题', 'error')
    return
  }

  helpMessages.value.push({ role: 'user', content: question })
  helpQuestion.value = ''
  helpLoading.value = true
  await scrollHelpToBottom()

  try {
    const res = await axios.post('/api/help/chat', {
      question,
      route: currentRoutePath.value,
      role: user.value?.role || '',
      role_name: user.value?.role_name || '',
      username: user.value?.username || '',
      history: helpMessages.value.slice(0, -1).slice(-10),
    }, { timeout: 60000 })

    if (res.data.ok) {
      helpMessages.value.push({
        role: 'assistant',
        content: res.data.answer || '暂时没有返回答案，请稍后重试。',
      })
    } else {
      const message = res.data.error || '回答失败'
      helpMessages.value.push({ role: 'assistant', content: message })
      showToast(message, 'error')
    }
  } catch (err) {
    const message = err.response?.data?.error || err.message || '帮助服务暂不可用'
    helpMessages.value.push({ role: 'assistant', content: message })
    showToast(message, 'error')
  } finally {
    helpLoading.value = false
    await scrollHelpToBottom()
  }
}

onMounted(() => {
    readUser()
    document.addEventListener('click', closeDropdown)
    window.addEventListener('storage', syncSession)
    window.addEventListener('auth:changed', syncSession)
})
onUnmounted(() => {
    document.removeEventListener('click', closeDropdown)
    window.removeEventListener('storage', syncSession)
    window.removeEventListener('auth:changed', syncSession)
})

const logout = () => {
  localStorage.removeItem('user')
  localStorage.removeItem('credentials')
  localStorage.removeItem('token')
  window.dispatchEvent(new Event('auth:changed'))
  showDropdown.value = false
  router.push('/login')
}

const switchAccount = () => {
  localStorage.removeItem('user')
  localStorage.removeItem('credentials')
  localStorage.removeItem('token')
  window.dispatchEvent(new Event('auth:changed'))
  showDropdown.value = false
  router.push('/login')
}
</script>

<template>
  <div class="app-layout">
    <!-- Toast Notifications -->
    <div class="toast-container">
      <TransitionGroup name="toast-anim">
        <div v-for="t in toasts" :key="t.id" :class="['toast-msg', t.type]">
          {{ t.message }}
        </div>
      </TransitionGroup>
    </div>

    <!-- Header -->
    <header class="app-header" v-if="user">
      <div class="container header-content">
        <div class="logo">
          <span class="logo-icon">◉</span>
          <span class="logo-text">JLU FOODLAB</span>
        </div>
        
        <div class="user-menu-wrapper">
          <div class="user-trigger" @click="toggleDropdown">
            <div class="avatar">{{ user.username.charAt(0).toUpperCase() }}</div>
            <span class="username">{{ user.username }} <span class="role-tag">{{ user.role_name }}</span></span>
            <svg class="chevron" :class="{ open: showDropdown }" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><polyline points="6 9 12 15 18 9"></polyline></svg>
          </div>
          
          <Transition name="fade-slide">
            <div class="dropdown-menu" v-if="showDropdown">
              <div class="dropdown-header">
                <div><strong>{{ user.username }}</strong></div>
                <div class="text-sm text-gray">{{ user.phone }}</div>
              </div>
              <div class="dropdown-divider"></div>
              <button class="dropdown-item" @click="switchAccount">切换账号</button>
              <button class="dropdown-item text-red" @click="logout">退出登录</button>
            </div>
          </Transition>
        </div>
      </div>
    </header>

    <main class="app-main">
      <RouterView :key="$route.fullPath" />
    </main>

    <button class="help-fab" type="button" @click="openHelp">帮助</button>

    <Transition name="help-fade">
      <div v-if="helpOpen" class="help-overlay" @click.self="closeHelp">
        <div class="help-panel">
          <div class="help-header">
            <div>
              <div class="help-title">智能帮助</div>
              <div class="help-subtitle">基于当前页面、角色和项目知识的问答助手</div>
            </div>
            <button class="help-close" type="button" @click="closeHelp">×</button>
          </div>

          <div class="help-suggestions">
            <button
              v-for="item in helpSuggestions"
              :key="item"
              type="button"
              class="help-chip"
              @click="useSuggestion(item)"
            >
              {{ item }}
            </button>
          </div>

          <div ref="helpChatRef" class="help-chat">
            <div v-for="(msg, index) in helpMessages" :key="index" :class="['help-bubble', msg.role]">
              <span class="help-role">{{ msg.role === 'user' ? '你' : '助手' }}</span>
              <p>{{ msg.content }}</p>
            </div>
          </div>

          <form class="help-form" @submit.prevent="sendHelp">
            <textarea
              v-model="helpQuestion"
              rows="4"
              placeholder="例如：普通用户怎么下单？商家怎么切换营业状态？"
            ></textarea>
            <div class="help-actions">
              <button type="button" class="btn-outline" @click="resetHelp">清空对话</button>
              <button type="submit" :disabled="helpLoading">
                <span v-if="!helpLoading">发送</span>
                <span v-else>思考中...</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style>
:root {
  --bg: #f2f0e9;
  --surface: #fbfaf6;
  --surface-2: #fffefb;
  --ink: #1a1813;
  --muted: #6e655a;
  --line: #dfd7ca;
  --brand: #2e7a63;
  --brand-2: #d98a3d;
  --radius: 14px;
  --shadow-soft: 0 12px 30px rgba(40, 33, 20, 0.08);
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: "Trebuchet MS", "Noto Sans SC", "PingFang SC", sans-serif;
  background:
    radial-gradient(circle at 0% 0%, rgba(217, 138, 61, 0.15), transparent 45%),
    radial-gradient(circle at 100% 100%, rgba(46, 122, 99, 0.18), transparent 42%),
    var(--bg);
  color: var(--ink);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
.app-layout { min-height: 100vh; display: flex; flex-direction: column; }

/* Header Glassmorphism */
.app-header {
  background: rgba(251, 250, 246, 0.82);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-content {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.9rem 1.5rem; max-width: 1120px; margin: 0 auto; width: 100%;
}

/* Logo */
.logo { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.logo-icon {
  font-size: 0.9rem;
  color: var(--brand);
  border: 1px solid rgba(46, 122, 99, 0.35);
  padding: 0.25rem;
  border-radius: 999px;
}
.logo-text {
  font-family: Georgia, "Noto Serif SC", serif;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 1.4px;
}

/* User Menu */
.user-menu-wrapper { position: relative; }
.user-trigger { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; padding: 0.45rem 0.82rem; border-radius: 50px; transition: background 0.2s; }
.user-trigger:hover { background: rgba(46, 122, 99, 0.12); }
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(150deg, var(--brand), #3f665a);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.9rem;
}
.username { font-weight: 500; font-size: 0.9rem; display: flex; align-items: center; gap: 0.5rem; }
.role-tag { font-size: 0.7rem; padding: 0.1rem 0.4rem; background: #efe9dd; border-radius: 4px; color: #5f4e38; }
.chevron { transition: transform 0.3s; }
.chevron.open { transform: rotate(180deg); }

/* Dropdown */
.dropdown-menu {
  position: absolute; top: calc(100% + 0.5rem); right: 0;
  background: var(--surface-2); width: 220px; border-radius: 12px;
  box-shadow: var(--shadow-soft); border: 1px solid var(--line);
  overflow: hidden; z-index: 200;
}
.dropdown-header { padding: 1rem; background: #f3ede1; }
.dropdown-divider { height: 1px; background: var(--line); }
.dropdown-item {
  width: 100%; text-align: left; padding: 0.8rem 1rem;
  background: transparent; color: #433526; border-radius: 0; font-size: 0.9rem;
}
.dropdown-item:hover { background: #f4efe4; color: var(--ink); opacity: 1; }
.text-red { color: #dc2626 !important; }

/* Transitions */
.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.2s ease; }
.fade-slide-enter-from, .fade-slide-leave-to { opacity: 0; transform: translateY(-10px); }

/* Toasts */
.toast-container { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999; display: flex; flex-direction: column; gap: 10px; align-items: center; pointer-events: none; }
.toast-msg { background: #25362f; color: #fff; padding: 0.8rem 1.5rem; border-radius: 50px; font-size: 0.9rem; font-weight: 500; box-shadow: 0 4px 12px rgba(0,0,0,0.15); pointer-events: auto; }
.toast-msg.error { background: #8f2626; }
.toast-msg.info { background: #5b5f66; }
.toast-anim-enter-active, .toast-anim-leave-active { transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.toast-anim-enter-from { opacity: 0; transform: translateY(-20px) scale(0.9); }
.toast-anim-leave-to { opacity: 0; transform: translateY(-20px) scale(0.9); }

/* Common Utilities */
.container { max-width: 1080px; margin: 0 auto; padding: 2rem 1.5rem; }
.card { background: var(--surface-2); padding: 1.8rem; border-radius: var(--radius); border: 1px solid var(--line); box-shadow: 0 2px 10px rgba(0,0,0,0.02); }
ul { list-style: none; }
button { cursor: pointer; border: none; background: linear-gradient(135deg, #224b3f, #2e7a63); color: #fff; padding: 0.6rem 1.2rem; border-radius: 8px; font-size: 0.9rem; font-weight: 500; transition: all 0.2s; }
button:hover { opacity: 0.85; transform: translateY(-1px); }
button:active { transform: translateY(0); }
button:disabled { background: #e5e5e5; color: #999; cursor: not-allowed; transform: none; }
.btn-outline { background: transparent; color: #24483f; border: 1px solid #bfcfcb; }
.btn-outline:hover { background: #eef4f2; border-color: #578b7c; }
.btn-text { background: transparent; color: #6e655a; padding: 0; font-weight: normal; }
.btn-text:hover { background: transparent; color: var(--ink); transform: none; }
input, textarea, select { padding: 0.7rem 1rem; border: 1px solid var(--line); border-radius: 8px; width: 100%; font-size: 0.95rem; background: #f7f3ea; transition: all 0.2s; outline: none; }
input:focus, textarea:focus, select:focus { background: #fffefb; border-color: #6e8f84; box-shadow: 0 0 0 3px rgba(46, 122, 99, 0.12); }

.page-title { font-size: 1.8rem; font-weight: 700; margin-bottom: 2rem; letter-spacing: -0.5px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; }

.badge { display: inline-flex; align-items: center; justify-content: center; padding: 0.2rem 0.6rem; border-radius: 50px; font-size: 0.75rem; font-weight: 600; }
.badge.pending { background: #fef3c7; color: #92400e; }
.badge.accepted { background: #dbeafe; color: #1e40af; }
.badge.delivered { background: #d1fae5; color: #166534; }
.badge.completed { background: #f3f4f6; color: #374151; }
.badge.reviewed { background: #f4f4f5; color: #4b5563; }
.text-gray { color: var(--muted); }
.text-sm { font-size: 0.85rem; }
.empty-state { text-align: center; padding: 4rem 2rem; color: #8e8578; background: var(--surface-2); border-radius: 12px; border: 1px dashed var(--line); font-size: 0.95rem; }

.help-fab {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 1200;
  min-width: 72px;
  height: 72px;
  border-radius: 999px;
  padding: 0 1rem;
  box-shadow: 0 16px 32px rgba(28, 24, 18, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.4);
}

.help-fab:hover {
  transform: translateY(-2px);
}

.help-overlay {
  position: fixed;
  inset: 0;
  z-index: 1300;
  background: rgba(20, 18, 14, 0.42);
  backdrop-filter: blur(6px);
  display: flex;
  justify-content: flex-end;
  align-items: flex-end;
  padding: 24px;
}

.help-panel {
  width: min(100%, 460px);
  max-height: calc(100vh - 48px);
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: 22px;
  box-shadow: 0 24px 60px rgba(32, 24, 12, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.help-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.2rem 1.2rem 0.9rem;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, #fffefb 0%, #f6f1e5 100%);
}

.help-title {
  font-size: 1.05rem;
  font-weight: 700;
}

.help-subtitle {
  margin-top: 0.2rem;
  font-size: 0.82rem;
  color: var(--muted);
}

.help-close {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: #f0e8db;
  color: #53483c;
  padding: 0;
  font-size: 1.2rem;
  line-height: 1;
}

.help-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 1rem 1.2rem 0;
}

.help-chip {
  background: #f4efe4;
  color: #3f3326;
  border: 1px solid #e2d8c8;
  border-radius: 999px;
  padding: 0.45rem 0.75rem;
  font-size: 0.82rem;
}

.help-chat {
  flex: 1;
  overflow: auto;
  padding: 1rem 1.2rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.help-bubble {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.8rem 0.9rem;
  border-radius: 16px;
  border: 1px solid #e8dfd1;
  background: #fbfaf6;
}

.help-bubble.user {
  background: #e9f4ef;
  border-color: #c6ddd2;
}

.help-role {
  font-size: 0.72rem;
  font-weight: 700;
  color: #7b6d5a;
}

.help-bubble p {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.92rem;
  color: var(--ink);
}

.help-form {
  border-top: 1px solid var(--line);
  padding: 1rem 1.2rem 1.2rem;
  background: #fffdf8;
}

.help-form textarea {
  resize: vertical;
  min-height: 94px;
  max-height: 220px;
}

.help-actions {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.8rem;
}

.help-actions button {
  flex: 1;
}

.help-fade-enter-active, .help-fade-leave-active {
  transition: opacity 0.18s ease;
}

.help-fade-enter-from, .help-fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .container {
    padding: 1.2rem 1rem;
  }

  .logo-text {
    font-size: 0.95rem;
    letter-spacing: 1px;
  }

  .username {
    display: none;
  }

  .help-overlay {
    padding: 12px;
    align-items: stretch;
  }

  .help-panel {
    width: 100%;
    max-height: calc(100vh - 24px);
  }

  .help-fab {
    right: 14px;
    bottom: 14px;
    height: 64px;
  }
}
</style>
