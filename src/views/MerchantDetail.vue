<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { showToast } from '../utils/toast'
import { formatTime } from '../utils/time'
const route = useRoute()
const router = useRouter()
const merchant = ref(null)
const dishes = ref([])
const reviews = ref([])
const cart = ref({})
const selectedAddressObj = ref(null)
const addresses = ref([])
const isLoading = ref(true)
const isOrdering = ref(false)

onMounted(() => {
    fetchAddresses()
    fetchMenu()
})

const fetchAddresses = async () => {
    try {
        const res = await api.post('/user/addresses')
        if (res.data.ok) {
            addresses.value = res.data.addresses
            const defAddr = addresses.value.find(a => a.is_default)
            if (defAddr) {
                selectedAddressObj.value = defAddr
            } else if (addresses.value.length > 0) {
                selectedAddressObj.value = addresses.value[0]
            }
        }
    } catch(e) {}
}

const fetchMenu = async () => {
    try {
        const res = await api.post('/menu', { merchant_id: route.params.id })
        if (res.data.ok) {
            merchant.value = res.data.merchant
            dishes.value = res.data.dishes
            reviews.value = res.data.reviews
        }
    } catch(e) {
        showToast('无法加载菜单', 'error')
        router.back()
    } finally {
        isLoading.value = false
    }
}

const resolveImageSrc = (path) => {
  if (!path) return ''
  if (/^(https?:|data:|blob:|\/api\/)/.test(path)) return path
  if (path.startsWith('/pic/')) return `/api${path}`
  if (path.startsWith('pic/')) return `/api/${path}`
  return ''
}

const addToCart = (dishId) => {
    if (!isMerchantAvailable.value) {
        showToast('商家当前休息中，暂不可点单', 'error')
        return
    }
    cart.value[dishId] = (cart.value[dishId] || 0) + 1
}

const removeFromCart = (dishId) => {
    if (cart.value[dishId]) {
        cart.value[dishId]--
        if (cart.value[dishId] === 0) delete cart.value[dishId]
    }
}

const cartTotal = computed(() => {
    return dishes.value.reduce((sum, d) => {
        return sum + (parseFloat(d.price) * (cart.value[d.id] || 0))
    }, 0).toFixed(2)
})

const cartItems = computed(() => {
    return dishes.value
        .filter(d => cart.value[d.id] > 0)
        .map(d => ({
            dish_id: d.id,
            name: d.name,
            price: d.price,
            quantity: cart.value[d.id]
        }))
})

const isMerchantAvailable = computed(() => Number(merchant.value?.is_available ?? 1) === 1)

const checkout = async () => {
    if (!isMerchantAvailable.value) return showToast('商家当前休息中，暂不可下单', 'error')
    if (cartItems.value.length === 0) return showToast('请先选择菜品', 'error')
    if (!selectedAddressObj.value) return showToast('请选择并填写配送地址', 'error')
    isOrdering.value = true
    try {
        const addrStr = `【${selectedAddressObj.value.label}】${selectedAddressObj.value.address} (${selectedAddressObj.value.receiver_name || '未填'} ${selectedAddressObj.value.receiver_phone || ''})`.trim()
        const payload = {
            merchant_id: route.params.id,
            address: addrStr,
            items: cartItems.value.map(i => ({ dish_id: i.dish_id, quantity: i.quantity }))
        }
        const res = await api.post('/order', payload)
        if (res.data.ok) {
            showToast(res.data.message, 'success')
            router.push('/customer')
        } else {
            showToast(res.data.error || '下单失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    } finally {
        isOrdering.value = false
    }
}
</script>

<template>
  <div class="container animate-fade-in">
    <div v-if="isLoading" class="loading-state">
      <span class="loader-dark"></span>
      <p>正在加载商家信息...</p>
    </div>

    <div v-else-if="merchant">
      <button class="btn-text mb-4" @click="router.back()">
        <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none" style="vertical-align: middle; margin-right: 4px"><path d="M19 12H5M12 19l-7-7 7-7"></path></svg>
        返回列表
      </button>
      
            <div class="merchant-header-banner">
                <div style="display:flex; align-items:center; gap:12px">
                    <img v-if="resolveImageSrc(merchant.logo_path)" :src="resolveImageSrc(merchant.logo_path)" :alt="merchant.name" style="width:64px;height:64px;border-radius:12px;object-fit:cover;border:1px solid rgba(0,0,0,0.06)" />
                    <h2 class="page-title mb-0">{{ merchant.name }} <span :class="['m-status', isMerchantAvailable ? 'open' : 'closed']">{{ isMerchantAvailable ? '营业中' : '休息中' }}</span></h2>
                </div>
            </div>

      <div v-if="!isMerchantAvailable" class="close-tip">商家当前休息中，可先浏览菜单，暂不支持下单。</div>

      <div class="layout-grid">
          <div class="menu-section">
              <h3 class="section-title">点餐</h3>
              <div v-if="dishes.length === 0" class="empty-state">暂无可用菜品</div>
                            <div class="card dish-card" v-for="dish in dishes" :key="dish.id">
                                    <div style="display:flex; gap:12px; align-items:center">
                                        <div v-if="resolveImageSrc(dish.image_path)" style="width:96px; height:72px; overflow:hidden; border-radius:8px; flex-shrink:0">
                                            <img :src="resolveImageSrc(dish.image_path)" :alt="dish.name" style="width:100%; height:100%; object-fit:cover" />
                                        </div>
                                        <div class="dish-info" style="flex:1">
                                            <h4>{{ dish.name }}</h4>
                                            <p>{{ dish.description || '这道菜没有留下描述' }}</p>
                                            <div class="price">￥{{ dish.price }}</div>
                                        </div>
                                    </div>
                  <div class="dish-actions">
                      <Transition name="fade">
                          <div class="action-group" v-if="cart[dish.id]">
                              <button class="btn-circle btn-outline" @click="removeFromCart(dish.id)">-</button>
                              <span class="qty">{{ cart[dish.id] }}</span>
                          </div>
                      </Transition>
                      <button class="btn-circle" :disabled="!isMerchantAvailable" @click="addToCart(dish.id)">+</button>
                  </div>
              </div>

              <h3 class="section-title mt-4">用户评价 ({{reviews.length}})</h3>
              <div v-if="!reviews.length" class="empty-state">暂无评价</div>
              <div class="review-card" v-for="(r, idx) in reviews" :key="idx">
                  <div class="r-header">
                      <div class="reviewer"><div class="tiny-avatar">{{ r.customer.charAt(0).toUpperCase() }}</div> <strong>{{ r.customer }}</strong></div>
                      <span class="rating-stars">
                          <span v-for="star in 5" :key="star" :class="{ active: star <= r.rating }">★</span>
                      </span>
                  </div>
                  <p class="r-comment">{{ r.comment || '该用户没有留下文字评价。' }}</p>
                  <div class="r-time text-sm" style="color: #9ca3af; margin-top: 10px;" v-if="r.created_at">{{ formatTime(r.created_at) }}</div>
              </div>
          </div>

          <div class="cart-section">
              <div class="cart-box">
                  <h3 class="section-title">购物车</h3>
                  <div v-if="cartItems.length === 0" class="empty-cart">
                      <div style="font-size: 2.5rem; margin-bottom: 0.5rem">🛒</div>
                      购物车空空如也
                  </div>
                  <div class="cart-list" v-else>
                      <TransitionGroup name="list">
                          <div class="cart-item" v-for="item in cartItems" :key="item.dish_id">
                              <div class="c-name">{{ item.name }}</div>
                              <div class="c-qty">x{{ item.quantity }}</div>
                              <div class="c-price">￥{{ (item.price * item.quantity).toFixed(2) }}</div>
                          </div>
                      </TransitionGroup>
                  </div>
                  <div class="checkout-footer" v-if="cartItems.length > 0">
                      <div class="cart-total">
                          <span class="text-gray">总结算</span>
                          <strong>￥{{ cartTotal }}</strong>
                      </div>
                      <div class="checkout-form">
                          <label class="text-sm font-medium mb-2" style="display:block">选择收货地址：</label>
                          <select v-model="selectedAddressObj" v-if="addresses.length > 0" class="w-100 mb-2">
                              <option v-for="addr in addresses" :key="addr.id" :value="addr">
                                  {{ addr.label }} - {{ addr.receiver_name }} - {{ addr.address }}
                              </option>
                          </select>
                          <div v-else class="text-sm text-gray mb-2">暂无地址，请先在个人中心添加</div>
                          <button class="w-100 mt-2 btn-primary" @click="checkout" :disabled="isOrdering || !selectedAddressObj || !isMerchantAvailable">
                              <span v-if="!isOrdering">{{ isMerchantAvailable ? '去结算' : '商家休息中' }}</span>
                              <span v-else class="loader-light"></span>
                          </button>
                      </div>
                  </div>
              </div>
          </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.4s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.loading-state { text-align: center; padding: 4rem; color: #666; }
.loader-dark { display: inline-block; width: 30px; height: 30px; border: 3px solid rgba(0,0,0,0.1); border-radius: 50%; border-top-color: #111; animation: spin 0.8s ease-in-out infinite; margin-bottom: 1rem; }
.loader-light { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: #fff; animation: spin 0.8s ease-in-out infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.merchant-header-banner { background: #111; color: #fff; padding: 2rem; border-radius: 16px; margin-bottom: 2rem; }
.merchant-header-banner .page-title { color: #fff; }
.m-status { margin-left: 0.45rem; font-size: 0.74rem; font-weight: 600; padding: 0.15rem 0.45rem; border-radius: 999px; vertical-align: middle; }
.m-status.open { background: #dcfce7; color: #166534; }
.m-status.closed { background: #fee2e2; color: #991b1b; }
.close-tip { margin-bottom: 1rem; border: 1px solid #fecaca; background: #fef2f2; color: #991b1b; font-size: 0.9rem; border-radius: 10px; padding: 0.7rem 0.9rem; }

.section-title { font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem; }
.layout-grid { display: grid; grid-template-columns: 1fr 340px; gap: 2rem; align-items: start; }
@media (max-width: 768px) { .layout-grid { grid-template-columns: 1fr; } }
.mb-4 { margin-bottom: 1.5rem; }
.mb-0 { margin-bottom: 0; }
.mt-4 { margin-top: 2rem; }
.mt-2 { margin-top: 0.8rem; }
.w-100 { width: 100%; }

.dish-card { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; padding: 1.5rem; transition: transform 0.2s, box-shadow 0.2s; }
.dish-card:hover { transform: translateX(4px); box-shadow: 0 4px 15px rgba(0,0,0,0.04); }
.dish-info h4 { margin-bottom: 0.3rem; font-size: 1.1rem; }
.dish-info p { font-size: 0.85rem; color: #9ca3af; margin-bottom: 0.8rem; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.price { font-weight: 700; color: #111; font-size: 1.1rem; }
.dish-actions { display: flex; align-items: center; gap: 0.5rem; }
.action-group { display: flex; align-items: center; gap: 0.5rem; }
.qty { width: 24px; text-align: center; font-weight: 600; }
.btn-circle { width: 32px; height: 32px; padding: 0; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: normal; }

.cart-box { background: #fff; border-radius: 16px; border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 10px 30px rgba(0,0,0,0.03); position: sticky; top: 6rem; overflow: hidden; }
.cart-box > h3 { padding: 1.5rem 1.5rem 0; margin-bottom: 0; }
.empty-cart { padding: 3rem 1.5rem; text-align: center; color: #9ca3af; font-size: 0.9rem; }
.cart-list { padding: 1rem 1.5rem; max-height: calc(100vh - 350px); overflow-y: auto; }
.cart-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; font-size: 0.95rem; }
.c-name { flex: 1; font-weight: 500; }
.c-qty { width: 40px; text-align: center; color: #6b7280; font-size: 0.85rem; }
.c-price { width: 70px; text-align: right; font-weight: 600; }
.checkout-footer { background: #fafafa; padding: 1.5rem; border-top: 1px solid rgba(0,0,0,0.05); }
.cart-total { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.cart-total strong { font-size: 1.5rem; letter-spacing: -0.5px; }

.review-card { background: #fff; padding: 1.5rem; border-radius: 12px; border: 1px solid rgba(0,0,0,0.05); margin-bottom: 1rem; }
.r-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; }
.reviewer { display: flex; align-items: center; gap: 0.6rem; font-size: 0.9rem; }
.tiny-avatar { width: 24px; height: 24px; border-radius: 50%; background: #e5e7eb; color: #4b5563; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 600; }
.rating-stars { color: #f59e0b; font-size: 0.9rem; }
.rating-stars span { color: #e5e7eb; }
.rating-stars span.active { color: #f59e0b; }
.r-comment { color: #4b5563; font-size: 0.95rem; line-height: 1.5; }

/* List transitions */
.list-enter-active, .list-leave-active { transition: all 0.3s ease; }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateX(30px); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
