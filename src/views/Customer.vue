<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import { showToast } from '../utils/toast'
import { formatTime } from '../utils/time'

const router = useRouter()
const merchants = ref([])
const activeOrders = ref([])
const historyOrders = ref([])
const activeTab = ref('merchants')
const merchantKeyword = ref('')
const isMerchantLoading = ref(false)
const isOrderLoading = ref(false)
// 排序相关
const sortKey = ref('default') // 'default' | 'orders' | 'rating'
const sortDir = ref('desc') // 'asc' | 'desc'
const reviewModal = ref({
    show: false,
    mode: 'create',
    orderId: null,
    merchant_rating: 5,
    merchant_comment: '',
    rider_rating: 5,
    rider_comment: '',
})
const contactModal = ref({ show: false, contacts: null })

const profile = ref({ username: '', phone: '', password: '' })
const isProfileLoading = ref(false)

const addresses = ref([])
const showAddressModal = ref(false)
const addressForm = ref({ id: null, label: '', receiver_name: '', receiver_phone: '', address: '', is_default: 0 })

onMounted(async () => {
    fetchMerchants()
    fetchMyOrders()
    fetchProfile()
    fetchAddresses()
})

const fetchAddresses = async () => {
    try {
        const res = await api.post('/user/addresses')
        if (res.data.ok) addresses.value = res.data.addresses
    } catch(e) {
        showToast(e.response?.data?.error || '加载地址失败', 'error')
    }
}

const saveAddress = async () => {
    if (!addressForm.value.label || !addressForm.value.address) {
        showToast('标签和详细地址不能为空', 'error')
        return
    }
    try {
        const res = await api.post('/user/address/save', addressForm.value)
        if (res.data.ok) {
            showToast('地址保存成功', 'success')
            showAddressModal.value = false
            fetchAddresses()
        } else {
            showToast(res.data.error || '保存失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    }
}

const deleteAddress = async (id) => {
    if (!confirm('确定删除该地址吗？')) return
    try {
        const res = await api.post('/user/address/delete', { id })
        if (res.data.ok) {
            showToast('已删除', 'success')
            fetchAddresses()
        } else {
            showToast(res.data.error || '删除失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    }
}

const editAddress = (addr) => {
    addressForm.value = { ...addr }
    showAddressModal.value = true
}

const openNewAddressModal = () => {
    addressForm.value = { id: null, label: '', receiver_name: '', receiver_phone: '', address: '', is_default: 0 }
    showAddressModal.value = true
}

const fetchProfile = async () => {
    isProfileLoading.value = true
    try {
        const res = await api.post('/user/profile')
        if (res.data.ok) {
            profile.value.username = res.data.user.username || ''
            profile.value.phone = res.data.user.phone || ''
        }
    } catch(e) {
        showToast(e.response?.data?.error || '加载个人信息失败', 'error')
    } finally {
        isProfileLoading.value = false
    }
}

const updateProfile = async () => {
    try {
        const res = await api.post('/user/profile/update', Object.fromEntries(Object.entries(profile.value).filter(([_, v]) => v !== '')))
        if(res.data.ok) {
            showToast('个人信息更新成功', 'success')
            profile.value.password = ''
            fetchProfile()
        } else {
            showToast(res.data.error || '更新失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    }
}

const fetchMerchants = async () => {
    isMerchantLoading.value = true
    try {
        const res = await api.post('/merchants')
        if (res.data.ok) merchants.value = res.data.merchants
    } catch(e) {
        showToast(e.response?.data?.error || '加载商家失败', 'error')
    } finally {
        isMerchantLoading.value = false
    }
}

const resolveImageSrc = (path) => {
  if (!path) return ''
  if (/^(https?:|data:|blob:|\/api\/)/.test(path)) return path
  if (path.startsWith('/pic/')) return `/api${path}`
  if (path.startsWith('pic/')) return `/api/${path}`
  return ''
}

const fetchMyOrders = async () => {
    isOrderLoading.value = true
    try {
        const res = await api.post('/orders/my')
        if (res.data.ok) {
            activeOrders.value = res.data.active || []
            historyOrders.value = res.data.history || []
        }
    } catch(e) {
        showToast(e.response?.data?.error || '加载订单失败', 'error')
    } finally {
        isOrderLoading.value = false
    }
}

const filteredMerchants = computed(() => {
    const key = merchantKeyword.value.trim().toLowerCase()
    // 先筛选
    let list = merchants.value.filter((m) => `${m.name} ${m.description || ''}`.toLowerCase().includes(key))

    // 为每个商家保证有 order_count 与 avg_rating 字段以便排序（不修改原对象）
    const normalized = list.map((m) => {
        const order_count = Number(m.order_count ?? m.orders?.length ?? 0)
        let avg = Number(m.avg_rating ?? 0)
        const is_available = Number(m.is_available ?? 1) ? 1 : 0
        if (!m.avg_rating && Array.isArray(m.reviews) && m.reviews.length) {
            const sum = m.reviews.reduce((s, r) => s + (Number(r.merchant_rating) || 0), 0)
            avg = sum / m.reviews.length
        }
        return { ...m, order_count, avg_rating: avg, is_available }
    })

    normalized.sort((a, b) => Number(b.is_available) - Number(a.is_available))

    // 排序
    if (sortKey.value === 'orders') {
        normalized.sort((a, b) => (a.order_count - b.order_count) * (sortDir.value === 'asc' ? 1 : -1))
    } else if (sortKey.value === 'rating') {
        normalized.sort((a, b) => (a.avg_rating - b.avg_rating) * (sortDir.value === 'asc' ? 1 : -1))
    }

    return normalized
})

const goToMerchant = (id) => {
    if (!id.is_available) {
        showToast('商家当前休息中，暂不可点单', 'error')
        return
    }
    router.push('/customer/merchant/' + id.id)
}

const completeOrder = async (orderId) => {
    try {
        const res = await api.post('/complete', { order_id: orderId })
        if (res.data.ok) {
            showToast('收货成功！', 'success')
            fetchMyOrders()
        } else {
            showToast(res.data.error || '操作失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    }
}

const openReview = (order, mode = 'create') => {
    const review = order.review || {}
    reviewModal.value = {
        show: true,
        mode,
        orderId: order.id,
        merchant_rating: Number(review.merchant_rating ?? 5),
        merchant_comment: review.merchant_comment || '',
        rider_rating: Number(review.rider_rating ?? 5),
        rider_comment: review.rider_comment || '',
    }
}

const deleteReview = async () => {
    if (!confirm('确定删除这条评价吗？删除后订单将恢复为已确认收货状态。')) return
    try {
        const res = await api.post('/review/delete', { order_id: reviewModal.value.orderId })
        if (res.data.ok) {
            showToast('评价已删除', 'success')
            reviewModal.value.show = false
            fetchMyOrders()
        } else {
            showToast(res.data.error || '删除失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    }
}

const submitReview = async () => {
    try {
        const res = await api.post('/review', { 
            order_id: reviewModal.value.orderId,
            merchant_rating: reviewModal.value.merchant_rating,
            merchant_comment: reviewModal.value.merchant_comment,
            rider_rating: reviewModal.value.rider_rating,
            rider_comment: reviewModal.value.rider_comment,
        })
        if(res.data.ok) {
            showToast('评价成功', 'success')
            reviewModal.value.show = false
            fetchMyOrders()
        } else {
            showToast(res.data.error || '评价失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    }
}

const openContact = async (orderId) => {
    try {
        const res = await api.post('/order/contact', { order_id: orderId })
        if (res.data.ok) {
            contactModal.value.contacts = res.data.contacts
            contactModal.value.show = true
        } else {
            showToast(res.data.error || '获取联系方式失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    }
}

</script>

<template>
  <div class="container animate-fade-in">
    <div class="tabs">
        <button :class="['tab-btn', { active: activeTab === 'merchants' }]" @click="activeTab = 'merchants'">浏览商家</button>
        <button :class="['tab-btn', { active: activeTab === 'orders' }]" @click="activeTab = 'orders'">我的订单</button>
        <button :class="['tab-btn', { active: activeTab === 'profile' }]" @click="activeTab = 'profile'">个人中心</button>
    </div>

    <!-- Profile Tab -->
    <div v-if="activeTab === 'profile'" class="tab-pane">
        <div class="flex-between mb-4">
            <h2 class="page-title mb-0">个人信息</h2>
            <button class="btn-outline" @click="fetchProfile">刷新信息</button>
        </div>
        <div class="loading-state" v-if="isProfileLoading">
            <span class="loader-dark"></span>
            <p>正在加载信息...</p>
        </div>
        <div class="card" style="max-width: 600px" v-else>
            <div class="form-group">
                <label>用户名</label>
                <input v-model="profile.username" type="text" placeholder="输入用户名" />
            </div>
            <div class="form-group">
                <label>联系电话</label>
                <input v-model="profile.phone" type="text" placeholder="输入手机号" />
            </div>
            <div class="form-group">
                <label>新密码 (留空则不修改)</label>
                <input v-model="profile.password" type="password" placeholder="输入新密码" />
            </div>
            <div style="text-align: right; margin-top: 1rem">
                <button class="btn-primary" @click="updateProfile">保存修改</button>
            </div>
        </div>
        
        <div class="flex-between mt-4 mb-4">
            <h2 class="page-title mb-0">收货地址管理</h2>
            <button class="btn-outline" @click="openNewAddressModal">+ 新增地址</button>
        </div>
        <div class="grid">
            <div class="card" v-for="addr in addresses" :key="addr.id">
                <div class="flex-between mb-2">
                    <strong>{{ addr.label }} <span v-if="addr.is_default" class="badge">默认</span></strong>
                    <div>
                        <button class="btn-text btn-sm" @click="editAddress(addr)">编辑</button>
                        <button class="btn-text btn-sm" style="color: #ef4444" @click="deleteAddress(addr.id)">删除</button>
                    </div>
                </div>
                <div class="text-sm text-gray mb-2">{{ addr.receiver_name }} {{ addr.receiver_phone }}</div>
                <div class="text-gray">{{ addr.address }}</div>
            </div>
            <div v-if="!addresses.length" class="empty-state" style="grid-column: 1/-1">暂无收货地址，请添加</div>
        </div>

        <div class="modal-overlay" v-if="showAddressModal" @click.self="showAddressModal = false">
            <div class="modal-card">
                <h3>{{ addressForm.id ? '编辑地址' : '新增地址' }}</h3>
                <div class="form-group mt-4">
                    <label>标签 (如：家、公司)</label>
                    <input v-model="addressForm.label" type="text" placeholder="必填" />
                </div>
                <div class="form-group">
                    <label>收货人姓名</label>
                    <input v-model="addressForm.receiver_name" type="text" placeholder="如：张三 (选填)" />
                </div>
                <div class="form-group">
                    <label>收货人电话</label>
                    <input v-model="addressForm.receiver_phone" type="text" placeholder="选填" />
                </div>
                <div class="form-group">
                    <label>详细地址</label>
                    <input v-model="addressForm.address" type="text" placeholder="必填的楼栋门牌号等" />
                </div>
                <div class="form-group" style="display: flex; gap: 8px; align-items: center">
                    <input type="checkbox" id="is_default" v-model="addressForm.is_default" :true-value="1" :false-value="0" />
                    <label for="is_default" style="margin: 0">设为默认地址</label>
                </div>
                <div class="modal-actions" style="margin-top: 1.5rem">
                    <button class="btn-text" @click="showAddressModal = false">取消</button>
                    <button class="btn-primary" @click="saveAddress">保存</button>
                </div>
            </div>
        </div>

    </div>

    <!-- Merchants Tab -->
    <div v-if="activeTab === 'merchants'" class="tab-pane">
        <div class="flex-between mb-4">
            <h2 class="page-title mb-0">推荐商家</h2>
            <button class="btn-outline" @click="fetchMerchants">刷新商家</button>
        </div>
        <div class="merchant-toolbar">
            <input v-model="merchantKeyword" type="text" placeholder="搜索商家名或菜系关键词" />
            <div style="display:flex; gap:8px; align-items:center">
                <select v-model="sortKey" style="padding:6px 8px; border-radius:6px; border:1px solid #e5e7eb">
                    <option value="default">默认排序</option>
                    <option value="orders">按订单数</option>
                    <option value="rating">按平均星级</option>
                </select>
                <button class="btn-outline btn-sm" @click.stop="sortDir = sortDir === 'asc' ? 'desc' : 'asc'">{{ sortDir === 'asc' ? '升序' : '降序' }}</button>
            </div>
            <div class="hint-chip">共 {{ filteredMerchants.length }} 家</div>
        </div>
        <div class="loading-state" v-if="isMerchantLoading">
            <span class="loader-dark"></span>
            <p>正在更新商家列表...</p>
        </div>
        <div class="grid" v-else>
            <div class="card merchant-card" :class="{ resting: !m.is_available }" v-for="m in filteredMerchants" :key="m.id" @click="goToMerchant(m)">
                    <div class="m-image-placeholder">
                        <img v-if="resolveImageSrc(m.logo_path)" :src="resolveImageSrc(m.logo_path)" :alt="m.name" class="m-logo" />
                        <div v-else style="font-size:2.2rem">🏬</div>
                    </div>
                <div class="m-content">
                    <h3>{{ m.name }} <span :class="['m-status', m.is_available ? 'open' : 'closed']">{{ m.is_available ? '营业中' : '休息中' }}</span></h3>
                    <p>{{ m.description || '暂无描述' }}</p>
                    <div class="merchant-meta">
                        <span>⭐ {{ Number(m.avg_rating || 0).toFixed(1) }}</span>
                        <span>订单 {{ m.order_count || 0 }}</span>
                    </div>
                </div>
            </div>
        </div>
        <div v-if="!isMerchantLoading && !filteredMerchants.length" class="empty-state">
            <div style="font-size: 3rem; margin-bottom: 1rem">🏝️</div>
            目前还没有任何商家哦
        </div>
    </div>

    <!-- Orders Tab -->
    <div v-if="activeTab === 'orders'" class="tab-pane">
        <div class="flex-between mb-4">
            <h2 class="page-title mb-0">订单中心</h2>
            <button class="btn-outline" @click="fetchMyOrders">刷新订单</button>
        </div>
        <div class="loading-state" v-if="isOrderLoading">
            <span class="loader-dark"></span>
            <p>正在同步订单状态...</p>
        </div>
        <template v-else>
        <h2 class="page-title">进行中的订单</h2>
        <div v-if="activeOrders.length === 0" class="empty-state mb-4">暂无进行中的订单</div>
        <div class="card order-card" v-for="order in activeOrders" :key="'active-'+order.id">
            <div class="order-header">
                <div class="merchant-name">{{ order.merchant }} <span class="text-sm text-gray" style="margin-left: 8px">{{ formatTime(order.created_at) }}</span></div>
                <span class="badge pending">等待完成</span>
            </div>
            <div class="order-items">
                <div v-for="item in order.items" :key="item.dish_name" class="order-item text-sm">
                    <span class="text-gray">{{ item.dish_name }} x{{ item.quantity }}</span>
                    <span>￥{{ item.subtotal }}</span>
                </div>
            </div>
            <div class="order-footer">
                <div class="total-price">总计: <span>￥{{ order.total_amount }}</span></div>
                <button class="btn-primary" @click="completeOrder(order.id)">确认收货</button>
                <button class="btn-outline btn-sm" style="margin-left:8px" @click="openContact(order.id)">查看联系方式</button>
            </div>
            <div class="hint-text">提示: 只有骑手标记送达后，确认收货才会生效</div>
        </div>

        <h2 class="page-title mt-4">历史订单</h2>
        <div v-if="historyOrders.length === 0" class="empty-state">暂无历史订单</div>
        <div class="card order-card" v-for="order in historyOrders" :key="'history-'+order.id">
            <div class="order-header">
                <div class="merchant-name">{{ order.merchant }} <span class="text-sm text-gray" style="margin-left:8px">#{{ order.id }} - {{ formatTime(order.created_at) }}</span></div>
                <span :class="['badge', order.status]">{{ order.status_text }}</span>
            </div>
            <div class="order-items">
                <div v-for="item in order.items" :key="item.dish_name" class="order-item text-sm">
                    <span class="text-gray">{{ item.dish_name }} x{{ item.quantity }}</span>
                </div>
            </div>
            <div class="order-footer">
                <div class="total-price">总计: <span>￥{{ order.total_amount }}</span></div>
                <button class="btn-outline btn-sm" v-if="order.status === 'completed'" @click="openReview(order, 'create')">评价订单</button>
                <button class="btn-outline btn-sm" v-else-if="order.status === 'reviewed' && order.review" @click="openReview(order, 'view')">查看评价</button>
                <button class="btn-outline btn-sm" style="margin-left:8px" @click="openContact(order.id)">查看联系方式</button>
            </div>
        </div>
        </template>
    </div>

    <!-- Review Modal -->
    <div class="modal-overlay" v-if="reviewModal.show" @click.self="reviewModal.show = false">
        <div class="modal-card">
            <h3>{{ reviewModal.mode === 'view' ? '查看评价' : '评价订单' }}</h3>
            <p class="text-gray text-sm mb-4" v-if="reviewModal.mode === 'view'">以下是你对该订单的评价，删除后可重新评价。</p>
            <p class="text-gray text-sm mb-4" v-else>请分别评价商品/商家与骑手</p>

            <template v-if="reviewModal.mode === 'view'">
                <div class="review-section">
                    <div class="review-title">商品与商家评价</div>
                    <div class="review-stars">
                        <span v-for="star in 5" :key="'merchant-view-'+star" class="star static" :class="{ active: star <= reviewModal.merchant_rating }">★</span>
                    </div>
                    <div class="review-comment-box">{{ reviewModal.merchant_comment || '未填写评价内容' }}</div>
                </div>
                <div class="review-section" style="margin-top: 1rem">
                    <div class="review-title">骑手评价</div>
                    <div class="review-stars">
                        <span v-for="star in 5" :key="'rider-view-'+star" class="star static" :class="{ active: star <= reviewModal.rider_rating }">★</span>
                    </div>
                    <div class="review-comment-box">{{ reviewModal.rider_comment || '未填写评价内容' }}</div>
                </div>
            </template>

            <template v-else>
                <div class="review-section">
                    <div class="review-title">商品与商家评价</div>
                    <div class="form-group">
                        <label>评分 (1-5)</label>
                        <div class="star-rating">
                            <span v-for="star in 5" :key="'merchant-'+star"
                                  class="star"
                                  :class="{ active: star <= reviewModal.merchant_rating }"
                                  @click="reviewModal.merchant_rating = star">★</span>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>评价内容</label>
                        <textarea v-model="reviewModal.merchant_comment" rows="3" placeholder="写点商品口味、包装、商家服务等..."></textarea>
                    </div>
                </div>
                <div class="review-section" style="margin-top: 1rem">
                    <div class="review-title">骑手评价</div>
                    <div class="form-group">
                        <label>评分 (1-5)</label>
                        <div class="star-rating">
                            <span v-for="star in 5" :key="'rider-'+star"
                                  class="star"
                                  :class="{ active: star <= reviewModal.rider_rating }"
                                  @click="reviewModal.rider_rating = star">★</span>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>评价内容</label>
                        <textarea v-model="reviewModal.rider_comment" rows="3" placeholder="写点骑手送达速度、态度等..."></textarea>
                    </div>
                </div>
            </template>
            <div class="modal-actions">
                <button class="btn-text" @click="reviewModal.show = false">取消</button>
                <button v-if="reviewModal.mode === 'view'" class="btn-text" style="color:#ef4444" @click="deleteReview">删除评价</button>
                <button v-else @click="submitReview">提交评价</button>
            </div>
        </div>
    </div>
    <div class="modal-overlay" v-if="contactModal.show" @click.self="contactModal.show = false">
        <div class="modal-card">
            <h3>联系方式</h3>
            <div style="margin-top: 1rem">
                <div v-if="contactModal.contacts">
                    <div style="margin-bottom: 0.8rem"><strong>商家：</strong>{{ contactModal.contacts.merchant.name }} - <span style="color:#111">{{ contactModal.contacts.merchant.phone || '未公开' }}</span></div>
                    <div style="margin-bottom: 0.8rem"><strong>骑手：</strong>{{ contactModal.contacts.rider.username }} - <span style="color:#111">{{ contactModal.contacts.rider.phone || '未公开' }}</span></div>
                    <div style="margin-bottom: 0.8rem"><strong>用户：</strong>{{ contactModal.contacts.customer.username }} - <span style="color:#111">{{ contactModal.contacts.customer.phone || '未公开' }}</span></div>
                </div>
            </div>
            <div class="modal-actions" style="margin-top: 1.5rem">
                <button class="btn-text" @click="contactModal.show = false">关闭</button>
            </div>
        </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.4s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.loading-state { text-align: center; padding: 2.6rem 1rem; color: #666; }
.loader-dark { display: inline-block; width: 30px; height: 30px; border: 3px solid rgba(0,0,0,0.1); border-radius: 50%; border-top-color: #111; animation: spin 0.8s ease-in-out infinite; margin-bottom: 1rem; }
@keyframes spin { to { transform: rotate(360deg); } }

.tabs { margin-bottom: 2rem; display: flex; gap: 2rem; border-bottom: 1px solid #ebebeb; }
.tab-btn { background: transparent; color: #999; border: none; font-size: 1.1rem; padding: 0 0 0.8rem 0; border-radius: 0; font-weight: 500; transition: color 0.2s; position: relative; }
.tab-btn:hover { color: #111; }
.tab-btn.active { color: #111; }
.tab-btn.active::after { content: ''; position: absolute; bottom: -1px; left: 0; width: 100%; height: 2px; background: #111; }

.flex-between { display: flex; justify-content: space-between; align-items: center; }
.merchant-toolbar { display: flex; gap: 0.7rem; margin-bottom: 1.2rem; }
.hint-chip { border: 1px solid #c8d5d2; border-radius: 999px; color: #3b655d; padding: 0.45rem 0.9rem; font-size: 0.85rem; white-space: nowrap; }
.mb-0 { margin-bottom: 0; }
.mb-4 { margin-bottom: 1.5rem; }
.mt-4 { margin-top: 2rem; }

.merchant-card { padding: 0; overflow: hidden; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.04); }
.merchant-card:hover { transform: translateY(-4px); box-shadow: 0 10px 25px rgba(0,0,0,0.08); }
.merchant-card.resting { opacity: 0.72; }
.merchant-card.resting:hover { transform: none; box-shadow: 0 4px 15px rgba(0,0,0,0.04); }
.m-image-placeholder { height: 120px; background: #f3f4f6; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; }
.m-content { padding: 1.5rem; }
.m-content h3 { margin-bottom: 0.5rem; font-size: 1.2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.m-status { margin-left: 0.4rem; font-size: 0.72rem; font-weight: 600; padding: 0.15rem 0.45rem; border-radius: 999px; vertical-align: middle; }
.m-status.open { background: #dcfce7; color: #166534; }
.m-status.closed { background: #fee2e2; color: #991b1b; }
.m-content p { color: #6b7280; font-size: 0.9rem; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.merchant-meta { display: flex; gap: 0.8rem; margin-top: 0.9rem; font-size: 0.85rem; color: #4b5563; }
.merchant-meta span { background: #f8fafc; border: 1px solid #eef0f2; padding: 0.35rem 0.6rem; border-radius: 999px; }

.order-card { padding: 1.5rem; transition: box-shadow 0.2s; }
.order-card:hover { box-shadow: 0 4px 15px rgba(0,0,0,0.04); }
.order-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(0,0,0,0.05); }
.merchant-name { font-weight: 600; font-size: 1.1rem; }
.order-items { margin-bottom: 1.5rem; }
.order-item { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
.order-footer { display: flex; justify-content: space-between; align-items: center; }
.total-price { font-weight: 500; font-size: 0.9rem; color: #666; }
.total-price span { font-size: 1.2rem; color: #111; font-weight: 700; margin-left: 0.5rem; }
.hint-text { font-size: 0.8rem; color: #9ca3af; margin-top: 1rem; border-top: 1px dashed #eee; padding-top: 0.8rem; }
.btn-sm { padding: 0.4rem 0.8rem; font-size: 0.85rem; }

/* Modal */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.4); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-card { background: #fff; width: 90%; max-width: 400px; padding: 2rem; border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); animation: popUp 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
@keyframes popUp { from { opacity: 0; transform: scale(0.95) translateY(10px); } to { opacity: 1; transform: scale(1) translateY(0); } }
.star-rating { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
.star { font-size: 1.8rem; color: #e5e7eb; cursor: pointer; transition: color 0.2s; }
.star.active { color: #f59e0b; }
.star:hover { transform: scale(1.1); }
.review-stars { display: flex; gap: 0.35rem; margin: 0.5rem 0 0.75rem; }
.star.static { cursor: default; }
.star.static:hover { transform: none; }
.review-comment-box { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 10px; padding: 0.85rem 1rem; color: #374151; min-height: 56px; white-space: pre-wrap; }
.modal-actions { display: flex; justify-content: flex-end; gap: 1rem; margin-top: 2rem; }
.form-group { margin-bottom: 1.5rem; }
.form-group label { display: block; font-size: 0.9rem; font-weight: 500; margin-bottom: 0.5rem; }
.review-section { padding: 1rem; border: 1px solid #eef0f2; border-radius: 12px; background: #fafafa; }
.review-title { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.75rem; color: #111; }
</style>
