<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'
import { showToast } from '../utils/toast'
import { formatTime } from '../utils/time'

const availableOrders = ref([])
const activeOrders = ref([])
const historyOrders = ref([])
const activeTab = ref('available')
const isLoading = ref(true)
const isHistoryLoading = ref(false)

const profile = ref({ username: '', phone: '', password: '' })
const contactModal = ref({ show: false, contacts: null })
const riderStats = ref({ count: 0, avg: 0, recent: [] })

onMounted(() => {
    fetchAvailable()
    fetchMyOrders()
    fetchProfile()
    fetchRiderStats()
})

const fetchProfile = async () => {
    try {
        const res = await api.post('/user/profile')
        if (res.data.ok) {
            profile.value.username = res.data.user.username || ''
            profile.value.phone = res.data.user.phone || ''
        }
    } catch(e) {}
}

const fetchRiderStats = async () => {
    try {
        const res = await api.post('/rider/stats')
        if (res.data.ok) {
            riderStats.value.count = res.data.count || 0
            riderStats.value.avg = res.data.avg || 0
            riderStats.value.recent = res.data.recent || []
        }
    } catch(e) {
        // ignore for non-rider users
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

const fetchAvailable = async () => {
    isLoading.value = true
    try {
        const res = await api.post('/available')
        if (res.data.ok) availableOrders.value = res.data.orders
    } catch(e) {} finally {
        isLoading.value = false
    }
}

const fetchMyOrders = async () => {
    isHistoryLoading.value = true
    try {
        const res = await api.post('/orders/my')
        if (res.data.ok) {
            activeOrders.value = res.data.active || []
            historyOrders.value = res.data.history || []
        }
    } catch(e) {
        showToast(e.response?.data?.error || '获取骑手订单失败', 'error')
    } finally {
        isHistoryLoading.value = false
    }
}

const claimOrder = async (order) => {
    try {
        const res = await api.post('/claim', { order_id: order.id })
        if (res.data.ok) {
            showToast('接单成功', 'success')
            fetchAvailable()
            fetchMyOrders()
        } else {
            showToast(res.data.error || '接单失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    }
}

const deliverOrder = async (orderId) => {
    try {
        const res = await api.post('/deliver', { order_id: orderId })
        if (res.data.ok) {
            showToast('标记送达成功！', 'success')
            fetchMyOrders()
        } else {
            showToast(res.data.error || '操作失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    }
}

const clearDelivered = (orderId) => {
    activeOrders.value = activeOrders.value.filter(o => o.id !== orderId)
    showToast('记录已归档', 'info')
}

const refresh = () => {
    fetchAvailable()
    fetchMyOrders()
}
</script>

<template>
  <div class="container animate-fade-in">
    <div class="tabs">
        <button :class="['tab-btn', { active: activeTab === 'available' }]" @click="activeTab = 'available'">新订单大厅 
            <span class="count-badge" v-if="availableOrders.length">{{ availableOrders.length }}</span>
        </button>
        <button :class="['tab-btn', { active: activeTab === 'active' }]" @click="activeTab = 'active'">我的配送</button>
        <button :class="['tab-btn', { active: activeTab === 'history' }]" @click="activeTab = 'history'">历史履历</button>
        <button :class="['tab-btn', { active: activeTab === 'profile' }]" @click="activeTab = 'profile'">个人中心</button>
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

    <!-- Profile Tab -->
    <div v-if="activeTab === 'profile'" class="tab-pane">
        <div class="flex-between mb-4">
            <h2 class="page-title mb-0">个人信息</h2>
            <button class="btn-outline" @click="fetchProfile">刷新</button>
        </div>
        <div class="card" style="max-width: 600px">
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
                <div style="margin-top: 1.2rem; padding-top: 1rem; border-top: 1px dashed #eee">
                    <h4 style="margin:0 0 8px 0">综合评价</h4>
                    <div class="text-sm text-gray">平均评分: <strong>{{ riderStats.avg.toFixed ? riderStats.avg.toFixed(1) : (riderStats.avg || 0).toFixed(1) }}</strong> （共 {{ riderStats.count }} 条）</div>
                    <div v-if="riderStats.recent && riderStats.recent.length" style="margin-top:8px">
                        <div v-for="r in riderStats.recent" :key="r.id" style="padding:6px 0;border-bottom:1px solid #f3f4f6">
                            <div style="font-size:0.95rem"><strong>{{ r.customer }}</strong> 给出 {{ r.rating }} 分</div>
                            <div class="text-gray" style="font-size:0.9rem">{{ r.comment }}</div>
                        </div>
                    </div>
                </div>
        </div>
    </div>

    <!-- Available Tab -->
    <div v-if="activeTab === 'available'" class="tab-pane">
        <div class="flex-between mb-4">
            <h2 class="page-title mb-0">实时订单接取</h2>
            <button class="btn-outline refresh-btn" @click="refresh">
                <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
                刷新列表
            </button>
        </div>
        
        <div v-if="isLoading" class="loading-state">
            <span class="loader-dark"></span>
            <p>正在扫描周围订单...</p>
        </div>
        <div v-else-if="availableOrders.length === 0" class="empty-state">
            <div style="font-size: 3rem; margin-bottom: 1rem">🛵</div>
            暂时没有可接取的订单
        </div>
        <div class="grid" v-else>
            <div class="card job-card" v-for="order in availableOrders" :key="order.id">
                <div class="job-header">
                    <div>
                        <span class="order-id">#{{ order.id }}</span>
                        <div class="text-sm text-gray" style="margin-top: 4px;">下单时间: {{ formatTime(order.created_at) }}</div>
                    </div>
                    <span class="price-tag">￥{{ order.total_amount }}</span>
                </div>
                <div class="job-body">
                    <div class="route">
                        <div class="point start">
                            <i>发</i>
                            <span>{{ order.merchant }}</span>
                        </div>
                        <div class="point end">
                            <i>收</i>
                            <span>{{ order.delivery_address }}</span>
                        </div>
                    </div>
                </div>
                <div class="job-footer">
                    <button class="w-100 btn-primary" @click="claimOrder(order)">立即接单</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Active Tab -->
    <div v-if="activeTab === 'active'" class="tab-pane">
        <h2 class="page-title">进行中的配送任务</h2>
        <div v-if="isHistoryLoading" class="loading-state">
            <span class="loader-dark"></span>
            <p>正在同步配送状态...</p>
        </div>
        <template v-else>
        <div v-if="activeOrders.length === 0" class="empty-state">目前没有正在配送的订单</div>
        <div class="grid">
            <div class="card job-card" v-for="order in activeOrders" :key="'active-'+order.id">
                <div class="job-header">
                    <div>
                        <span class="order-id">#{{ order.id }}</span>
                        <div class="text-sm text-gray" style="margin-top: 4px;">下单时间: {{ formatTime(order.created_at) }}</div>
                    </div>
                    <span :class="['badge', order.status]">{{ order.status_text }}</span>
                </div>
                <div class="job-body">
                    <div class="route">
                        <div class="point start">
                            <i>发</i>
                            <span>{{ order.merchant }}</span>
                        </div>
                        <div class="point end">
                            <i>收</i>
                            <span>{{ order.delivery_address }}</span>
                        </div>
                    </div>
                </div>
                <div class="job-footer">
                    <button class="w-100" v-if="order.status === 'accepted'" @click="deliverOrder(order.id)">已送达用户</button>
                    <button class="w-100 btn-outline" v-else-if="order.status === 'delivered'" @click="clearDelivered(order.id)">归档此单</button>
                    <button class="w-100 btn-outline" style="margin-top:8px" @click="openContact(order.id)">查看联系方式</button>
                </div>
            </div>
        </div>
        </template>
    </div>

    <!-- History Tab -->
    <div v-if="activeTab === 'history'" class="tab-pane">
        <h2 class="page-title">历史完成记录</h2>
        <div v-if="isHistoryLoading" class="loading-state">
            <span class="loader-dark"></span>
            <p>正在加载历史订单...</p>
        </div>
        <template v-else>
        <div v-if="historyOrders.length === 0" class="empty-state">暂无历史订单</div>
        <div class="card p-0" v-else>
          <table class="data-table">
            <thead>
              <tr>
                <th>编号</th>
                <th>下单时间</th>
                <th>商家</th>
                <th>送货地址</th>
                <th class="text-right">状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in historyOrders" :key="'history-'+order.id">
                <td class="text-gray">#{{ order.id }}</td>
                <td class="text-gray">{{ formatTime(order.created_at) }}</td>
                <td class="font-medium">{{ order.merchant }}</td>
                <td>{{ order.delivery_address }}</td>
                <td class="text-right"><span :class="['badge', order.status]">{{ order.status_text }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
                </template>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.4s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.loading-state { text-align: center; padding: 4rem; color: #666; }
.loader-dark { display: inline-block; width: 30px; height: 30px; border: 3px solid rgba(0,0,0,0.1); border-radius: 50%; border-top-color: #111; animation: spin 0.8s ease-in-out infinite; margin-bottom: 1rem; }
@keyframes spin { to { transform: rotate(360deg); } }

.tabs { margin-bottom: 2rem; display: flex; gap: 2rem; border-bottom: 1px solid #ebebeb; }
.tab-btn { background: transparent; color: #999; border: none; font-size: 1.1rem; padding: 0 0 0.8rem 0; border-radius: 0; font-weight: 500; transition: color 0.2s; position: relative; }
.tab-btn:hover { color: #111; }
.tab-btn.active { color: #111; }
.tab-btn.active::after { content: ''; position: absolute; bottom: -1px; left: 0; width: 100%; height: 2px; background: #111; }
.count-badge { background: #e53935; color: #fff; font-size: 0.7rem; padding: 0.1rem 0.4rem; border-radius: 10px; position: relative; top: -2px; margin-left: 4px; }

.flex-between { display: flex; justify-content: space-between; align-items: center; }
.mb-0 { margin-bottom: 0; }
.mb-4 { margin-bottom: 1.5rem; }
.w-100 { width: 100%; }
.refresh-btn { display: flex; align-items: center; gap: 6px; padding: 0.4rem 0.8rem; font-size: 0.85rem; }

.job-card { padding: 1.5rem; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, box-shadow 0.2s; border: 1px solid rgba(0,0,0,0.06); }
.job-card:hover { transform: translateY(-4px); box-shadow: 0 10px 25px rgba(0,0,0,0.06); }
.job-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.order-id { font-weight: 600; color: #6b7280; }
.price-tag { font-size: 1.4rem; font-weight: 700; color: #111; }

.job-body { margin-bottom: 1.5rem; flex: 1; }
.route { display: flex; flex-direction: column; gap: 1rem; position: relative; }
.route::before { content: ''; position: absolute; left: 11px; top: 24px; bottom: 24px; width: 2px; background: #e5e5e5; border-radius: 2px; }
.point { display: flex; align-items: flex-start; gap: 1rem; position: relative; z-index: 1; }
.point i { display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; font-size: 0.7rem; font-style: normal; font-weight: 600; flex-shrink: 0; }
.point.start i { background: #111; color: #fff; }
.point.end i { background: #f3f4f6; color: #111; border: 1px solid #e5e5e5; }
.point span { font-size: 0.95rem; font-weight: 500; color: #374151; padding-top: 2px; }

.p-0 { padding: 0; overflow: hidden; }
.data-table { width: 100%; border-collapse: collapse; text-align: left; }
.data-table th { padding: 1rem 1.5rem; font-size: 0.85rem; font-weight: 600; color: #6b7280; border-bottom: 1px solid rgba(0,0,0,0.05); background: #fafafa; }
.data-table td { padding: 1.2rem 1.5rem; font-size: 0.95rem; border-bottom: 1px solid rgba(0,0,0,0.02); }
.text-right { text-align: right; }
.text-gray { color: #6b7280; }
.font-medium { font-weight: 500; }
</style>
