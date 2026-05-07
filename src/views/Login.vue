<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const account = ref('')
const password = ref('')
const error = ref('')
const isLoading = ref(false)
const remember = ref(true)
const isLoginMode = ref(true)
const router = useRouter()

const regForm = ref({
  username: '',
  password: '',
  phone: '',
  role: 'customer',
  address: '',
  merchant_name: ''
})

onMounted(() => {
  const saved = localStorage.getItem('credentials')
  if (!saved) return
  try {
    const creds = JSON.parse(saved)
    account.value = creds.account || ''
    password.value = creds.password || ''
  } catch (e) {
    localStorage.removeItem('credentials')
  }
})

const toggleMode = () => {
    isLoginMode.value = !isLoginMode.value
    error.value = ''
}

const register = async () => {
  error.value = ''
  isLoading.value = true
  try {
    const res = await api.post('/register', regForm.value)
    if (res.data.ok) {
      isLoginMode.value = true
      account.value = regForm.value.username
      password.value = regForm.value.password
      alert('注册成功，已自动填充账号密码，请点击进入系统！')
    } else {
      error.value = res.data.error || '注册失败'
    }
  } catch (err) {
    error.value = err.response?.data?.error || err.message
  } finally {
    isLoading.value = false
  }
}

const login = async () => {
  error.value = ''
  isLoading.value = true
  try {
    const res = await api.post('/login', { account: account.value, password: password.value })
    if (res.data.ok) {
      const user = res.data.user
      const token = res.data.token
      localStorage.setItem('user', JSON.stringify(user))
      localStorage.setItem('token', token)
      if (remember.value) {
        localStorage.setItem('credentials', JSON.stringify({ account: account.value, password: password.value }))
      } else {
        localStorage.removeItem('credentials')
      }
      window.dispatchEvent(new Event('auth:changed'))
      
      if (user.role === 'customer') router.push('/customer')
      else if (user.role === 'rider') router.push('/rider')
      else if (user.role === 'merchant') router.push('/merchant')
    } else {
      error.value = res.data.error || '登录失败'
    }
  } catch (err) {
    error.value = err.response?.data?.error || err.message
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-wrapper">
    <div class="brand-background">
      <div class="brand-content">
        <h1>Eat Quiet.<br/>Live Sharp.</h1>
        <p>不喧哗的效率，不平庸的体验。</p>
        <div class="brand-tags">
          <span>即时流转</span>
          <span>真实状态</span>
          <span>轻盈交互</span>
        </div>
      </div>
    </div>
    
    <div class="login-panel">
      <div class="login-card" :class="{ 'register-mode': !isLoginMode }">
        <div class="icon-logo"></div>
        <h2>{{ isLoginMode ? '欢迎回来' : '注册账号' }}</h2>
        <p class="subtitle">{{ isLoginMode ? '登录后自动进入对应工作台' : '一键开启体验' }}</p>
        
        <form @submit.prevent="isLoginMode ? login() : register()">
          <template v-if="isLoginMode">
            <div class="form-group">
              <label>账号</label>
              <input v-model="account" type="text" required placeholder="用户名或手机号" />
            </div>
            <div class="form-group">
              <label>密码</label>
              <input v-model="password" type="password" required placeholder="输入密码" />
            </div>

            <label class="remember-row">
              <input v-model="remember" type="checkbox" />
              <span>记住我（仅本机）</span>
            </label>
          </template>

          <template v-else>
            <div class="form-group">
                <label>用户名</label>
                <input v-model="regForm.username" type="text" required placeholder="起个名字" />
            </div>
            <div class="form-group">
                <label>手机号</label>
                <input v-model="regForm.phone" type="text" required placeholder="输入联系方式" />
            </div>
            <div class="form-group">
                <label>设置密码</label>
                <input v-model="regForm.password" type="password" required placeholder="设置密码" />
            </div>
            <div class="form-group">
                <label>用户角色</label>
                <select v-model="regForm.role" required>
                    <option value="customer">普通用户 (点餐)</option>
                    <option value="merchant">入驻商家 (开店)</option>
                    <option value="rider">配送骑手 (接单)</option>
                </select>
            </div>
            <div class="form-group" v-if="regForm.role === 'customer'">
                <label>收货地址 (选填)</label>
                <input v-model="regForm.address" type="text" placeholder="填写收货地址" />
            </div>
            <div class="form-group" v-if="regForm.role === 'merchant'">
                <label>商家/店铺名称 (必填)</label>
                <input v-model="regForm.merchant_name" type="text" :required="regForm.role === 'merchant'" placeholder="填写店铺名称" />
            </div>
          </template>
          
          <div v-if="error" class="error-box">{{ error }}</div>
          
          <button type="submit" class="submit-btn" :disabled="isLoading">
            <span v-if="!isLoading">{{ isLoginMode ? '进入系统' : '完成注册并登录' }}</span>
            <span v-else class="loader"></span>
          </button>
        </form>

        <div class="mode-toggle">
            <a href="#" @click.prevent="toggleMode" class="toggle-link">
              {{ isLoginMode ? '还没有账号？点此注册' : '已有账号？返回登录' }}
            </a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-wrapper {
  display: flex;
  min-height: 100vh;
  margin: -2rem -1.5rem;
  background: #f7f1e7;
}
.brand-background {
  flex: 1;
  background:
    radial-gradient(circle at 22% 22%, rgba(46, 122, 99, 0.45), transparent 50%),
    radial-gradient(circle at 84% 74%, rgba(217, 138, 61, 0.38), transparent 52%),
    #1f2322;
  display: flex;
  align-items: center;
  padding: 4rem;
  position: relative;
  overflow: hidden;
}
.brand-background::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px);
  background-size: 30px 30px;
  opacity: 0.3;
}
.brand-content {
  position: relative;
  z-index: 1;
  color: #f8f6f2;
}
.brand-content h1 {
  font-size: 4rem;
  font-family: Georgia, "Noto Serif SC", serif;
  font-weight: 700;
  line-height: 1.1;
  margin-bottom: 1rem;
  letter-spacing: 0.4px;
}
.brand-content p {
  color: #d9d4cb;
  font-size: 1.25rem;
}
.brand-tags {
  margin-top: 2rem;
  display: flex;
  gap: 0.8rem;
  flex-wrap: wrap;
}
.brand-tags span {
  border: 1px solid rgba(255, 255, 255, 0.35);
  color: #efe8dd;
  font-size: 0.85rem;
  border-radius: 999px;
  padding: 0.3rem 0.8rem;
}
.login-panel {
  flex: 0 0 500px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  background: #f7f1e7;
  box-shadow: -20px 0 40px rgba(0,0,0,0.05);
  z-index: 2;
}
.login-card {
  width: 100%;
  max-width: 360px;
  background: #fffdf8;
  border: 1px solid #dfd7ca;
  border-radius: 18px;
  padding: 2rem;
  box-shadow: 0 15px 30px rgba(43, 36, 25, 0.08);
}
.icon-logo {
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 1px;
  color: #2e7a63;
  margin-bottom: 1rem;
}
.login-card h2 {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  letter-spacing: -0.5px;
}
.subtitle {
  color: #6b7280;
  margin-bottom: 2rem;
}
.form-group {
  margin-bottom: 1.2rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #374151;
}
.form-group input, .form-group select {
  width: 100%;
  padding: 0.8rem 1rem;
  border: 1.5px solid #e5e0d8;
  border-radius: 10px;
  font-size: 1rem;
  background: #fff;
  transition: all 0.2s ease;
  box-sizing: border-box;
}
.form-group input:focus, .form-group select:focus {
  outline: none;
  border-color: #2e7a63;
  box-shadow: 0 0 0 4px rgba(46, 122, 99, 0.1);
}
.remember-row {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin-top: 0.2rem;
  font-size: 0.9rem;
  color: #635b4f;
}
.remember-row input {
  width: auto;
}
.submit-btn {
  width: 100%;
  margin-top: 1rem;
  padding: 0.8rem;
  font-size: 1rem;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 3rem;
}
.mode-toggle {
  margin-top: 1.5rem;
  text-align: center;
}
.toggle-link {
  color: #2e7a63;
  font-size: 0.95rem;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}
.toggle-link:hover {
  text-decoration: underline;
  color: #246350;
}
.register-mode {
  max-width: 400px;
}
.error-box {
  background: #fcefeb;
  color: #8b2b2b;
  padding: 0.8rem;
  border-radius: 8px;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
  border: 1px solid #edc8c0;
}
.loader {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 0.8s ease-in-out infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .brand-background { display: none; }
  .login-panel { flex: 1; box-shadow: none; }
  .login-wrapper { margin: -1.2rem -1rem; }
  .login-card { padding: 1.5rem; }
}
</style>
