<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'
import { showToast } from '../utils/toast'
import { formatTime } from '../utils/time'
const activeTab = ref('dashboard')
const orders = ref([])
const dishes = ref([])
const reviews = ref([])
const isLoading = ref(true)
const isSavingDish = ref(false)
const isUploadingLogo = ref(false)
const isUploadingDishImage = ref(false)
const isTogglingBusiness = ref(false)
const orderFilter = ref('')
const analyticsPeriod = ref('daily')
const analyticsMetric = ref('revenue')
const dishMetric = ref('quantity')
const contactModal = ref({ show: false, contacts: null })

const dishForm = ref({
  id: null,
  name: '',
  price: '',
  description: '',
  image_path: '',
  is_available: 1
})

const profile = ref({
  name: '',
  description: '',
  logo_path: '',
  is_available: 1,
  password: '',
})

const fetchProfile = async () => {
    try {
        const res = await api.post('/merchant/profile')
        if (res.data.ok) {
            profile.value.name = res.data.merchant.name || ''
            profile.value.description = res.data.merchant.description || ''
            profile.value.logo_path = res.data.merchant.logo_path || ''
          profile.value.is_available = Number(res.data.merchant.is_available ?? 1) ? 1 : 0
        }
    } catch(e) {
        showToast(e.response?.data?.error || '加载商家信息失败', 'error')
    }
}

const resolveImageSrc = (path) => {
  if (!path) return ''
  if (/^(https?:|data:|blob:|\/api\/)/.test(path)) return path
  if (path.startsWith('/pic/')) return `/api${path}`
  if (path.startsWith('pic/')) return `/api/${path}`
  return ''
}

const uploadImageFile = async (file, kind) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('kind', kind)
  const res = await api.post('/upload/image', formData)
  if (!res.data.ok) {
    throw new Error(res.data.error || '图片上传失败')
  }
  return res.data.path
}

const handleLogoUpload = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  isUploadingLogo.value = true
  try {
    profile.value.logo_path = await uploadImageFile(file, 'merchant')
    showToast('商家图片上传成功', 'success')
  } catch (err) {
    showToast(err.response?.data?.error || err.message || '图片上传失败', 'error')
  } finally {
    isUploadingLogo.value = false
  }
}

const handleDishImageUpload = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  isUploadingDishImage.value = true
  try {
    dishForm.value.image_path = await uploadImageFile(file, 'dish')
    showToast('菜品图片上传成功', 'success')
  } catch (err) {
    showToast(err.response?.data?.error || err.message || '图片上传失败', 'error')
  } finally {
    isUploadingDishImage.value = false
  }
}

const updateProfile = async () => {
    try {
        const res = await api.post('/merchant/profile/update', profile.value)
        if(res.data.ok) {
            showToast('商家信息更新成功', 'success')
            fetchProfile()
        } else {
            showToast(res.data.error || '更新失败', 'error')
        }
    } catch(err) {
        showToast(err.response?.data?.error || '请求失败', 'error')
    }
    if (profile.value.password) {
        try {
            await api.post('/user/profile/update', { password: profile.value.password })
            profile.value.password = ''
        } catch(e) {}
    }
}

const fetchOrders = async () => {
  try {
    const res = await api.post('/merchant/orders')
    if (res.data.ok) {
      orders.value = res.data.orders
    } else {
      showToast(res.data.error || '获取订单失败', 'error')
    }
  } catch (err) {
    showToast(err.response?.data?.error || '获取订单失败', 'error')
  }
}

const fetchDishes = async () => {
  try {
    const res = await api.post('/merchant/dishes')
    if (res.data.ok) {
      dishes.value = res.data.dishes
    } else {
      showToast(res.data.error || '获取菜品失败', 'error')
    }
  } catch (err) {
    showToast(err.response?.data?.error || '获取菜品失败', 'error')
  }
}

const fetchReviews = async () => {
  try {
    const res = await api.post('/merchant/reviews')
    if (res.data.ok) {
      reviews.value = res.data.reviews
    } else {
      showToast(res.data.error || '获取评价失败', 'error')
    }
  } catch (err) {
    showToast(err.response?.data?.error || '获取评价失败', 'error')
  }
}

const loadAll = async () => {
  isLoading.value = true
  await Promise.all([fetchProfile(), fetchOrders(), fetchDishes(), fetchReviews()])
  isLoading.value = false
}

onMounted(() => {
  loadAll()
})

const openContact = async (orderId) => {
  try {
    const res = await api.post('/order/contact', { order_id: orderId })
    if (res.data.ok) {
      contactModal.value.contacts = res.data.contacts
      contactModal.value.show = true
    } else {
      showToast(res.data.error || '获取联系方式失败', 'error')
    }
  } catch (err) {
    showToast(err.response?.data?.error || '请求失败', 'error')
  }
}

const totalRevenue = computed(() => {
  const sum = orders.value.reduce((acc, order) => {
    if (['completed', 'reviewed'].includes(order.status)) {
      return acc + parseFloat(order.total_amount)
    }
    return acc
  }, 0)
  return sum.toFixed(2)
})

const completedCount = computed(() => {
  return orders.value.filter(o => ['completed', 'reviewed'].includes(o.status)).length
})

const activeCount = computed(() => {
  return orders.value.filter(o => ['pending', 'accepted', 'delivered'].includes(o.status)).length
})

const avgRating = computed(() => {
  if (!reviews.value.length) return '0.0'
  const sum = reviews.value.reduce((acc, r) => acc + Number(r.rating || 0), 0)
  return (sum / reviews.value.length).toFixed(1)
})

const periodOptions = [
  { value: 'daily', label: '近7天' },
  { value: 'weekly', label: '近8周' },
  { value: 'monthly', label: '近6个月' }
]

const metricOptions = [
  { value: 'revenue', label: '营业额(元)' },
  { value: 'orders', label: '订单量(单)' },
  { value: 'avgTicket', label: '客单价(元)' }
]

const completedStatuses = new Set(['completed', 'reviewed'])

const pad2 = (value) => String(value).padStart(2, '0')

const dateKey = (date) => `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`

const monthKey = (date) => `${date.getFullYear()}-${pad2(date.getMonth() + 1)}`

const weekStartDate = (date) => {
  const day = date.getDay() || 7
  const start = new Date(date)
  start.setHours(0, 0, 0, 0)
  start.setDate(start.getDate() - day + 1)
  return start
}

const weekKey = (date) => dateKey(weekStartDate(date))

const parseOrderDate = (order) => {
  if (!order.created_at) return null
  const date = new Date(order.created_at)
  return Number.isNaN(date.getTime()) ? null : date
}

const selectedPeriodMeta = computed(() => {
  if (analyticsPeriod.value === 'weekly') {
    return { keyFn: weekKey, size: 8 }
  }
  if (analyticsPeriod.value === 'monthly') {
    return { keyFn: monthKey, size: 6 }
  }
  return { keyFn: dateKey, size: 7 }
})

const buildRecentKeys = (period, size) => {
  const keys = []
  const base = new Date()
  base.setHours(0, 0, 0, 0)
  if (period === 'daily') {
    for (let i = size - 1; i >= 0; i -= 1) {
      const d = new Date(base)
      d.setDate(base.getDate() - i)
      keys.push(dateKey(d))
    }
    return keys
  }
  if (period === 'weekly') {
    const thisWeek = weekStartDate(base)
    for (let i = size - 1; i >= 0; i -= 1) {
      const d = new Date(thisWeek)
      d.setDate(thisWeek.getDate() - i * 7)
      keys.push(dateKey(d))
    }
    return keys
  }
  const monthBase = new Date(base.getFullYear(), base.getMonth(), 1)
  for (let i = size - 1; i >= 0; i -= 1) {
    const d = new Date(monthBase)
    d.setMonth(monthBase.getMonth() - i)
    keys.push(monthKey(d))
  }
  return keys
}

const formatPeriodLabel = (key, period) => {
  if (period === 'daily') {
    const [year, month, day] = key.split('-')
    return `${month}/${day}`
  }
  if (period === 'weekly') {
    const [year, month, day] = key.split('-')
    return `${month}/${day}周`
  }
  const [year, month] = key.split('-')
  return `${year}.${month}`
}

const analyticsRows = computed(() => {
  const period = analyticsPeriod.value
  const { keyFn, size } = selectedPeriodMeta.value
  const keys = buildRecentKeys(period, size)
  const bucket = new Map(keys.map((key) => [key, { orders: 0, revenue: 0 }]))

  for (const order of orders.value) {
    if (!completedStatuses.has(order.status)) continue
    const date = parseOrderDate(order)
    if (!date) continue
    const key = keyFn(date)
    const target = bucket.get(key)
    if (!target) continue
    target.orders += 1
    target.revenue += Number(order.total_amount || 0)
  }

  return keys.map((key) => {
    const item = bucket.get(key)
    const avgTicket = item.orders ? item.revenue / item.orders : 0
    return {
      key,
      label: formatPeriodLabel(key, period),
      orders: item.orders,
      revenue: Number(item.revenue.toFixed(2)),
      avgTicket: Number(avgTicket.toFixed(2))
    }
  })
})

const selectedMetricLabel = computed(() => {
  const metric = metricOptions.find((item) => item.value === analyticsMetric.value)
  return metric ? metric.label : '指标'
})

const analyticsMaxValue = computed(() => {
  const values = analyticsRows.value.map((row) => Number(row[analyticsMetric.value] || 0))
  const max = Math.max(...values, 0)
  return max > 0 ? max : 1
})

const analyticsPoints = computed(() => {
  const list = analyticsRows.value
  if (!list.length) return ''
  const width = 640
  const height = 240
  const step = list.length > 1 ? width / (list.length - 1) : width
  return list
    .map((row, index) => {
      const x = index * step
      const value = Number(row[analyticsMetric.value] || 0)
      const ratio = value / analyticsMaxValue.value
      const y = Number((height - ratio * 190 - 20).toFixed(2))
      return `${x},${y}`
    })
    .join(' ')
})

const analyticsDots = computed(() => {
  const list = analyticsRows.value
  if (!list.length) return []
  const width = 640
  const height = 240
  const step = list.length > 1 ? width / (list.length - 1) : width
  return list.map((row, index) => {
    const x = Number((index * step).toFixed(2))
    const value = Number(row[analyticsMetric.value] || 0)
    const ratio = value / analyticsMaxValue.value
    const y = Number((height - ratio * 190 - 20).toFixed(2))
    return { x, y, value }
  })
})

const rangeRevenue = computed(() => analyticsRows.value.reduce((acc, row) => acc + row.revenue, 0).toFixed(2))
const rangeOrders = computed(() => analyticsRows.value.reduce((acc, row) => acc + row.orders, 0))
const rangeAvgTicket = computed(() => {
  const count = rangeOrders.value
  if (!count) return '0.00'
  return (Number(rangeRevenue.value) / count).toFixed(2)
})

const analyticsPeak = computed(() => {
  if (!analyticsRows.value.length) return null
  return analyticsRows.value.reduce((best, row) => {
    if (!best) return row
    return Number(row[analyticsMetric.value] || 0) > Number(best[analyticsMetric.value] || 0) ? row : best
  }, null)
})

const printReport = () => {
  window.print()
}

const businessStatusText = computed(() => (profile.value.is_available ? '营业中' : '休息中'))

const toggleBusinessStatus = async () => {
  if (isTogglingBusiness.value) return
  isTogglingBusiness.value = true
  const nextStatus = profile.value.is_available ? 0 : 1
  try {
    const res = await api.post('/merchant/profile/update', { is_available: nextStatus })
    if (res.data.ok) {
      profile.value.is_available = nextStatus
      showToast(nextStatus ? '已切换为营业中' : '已切换为休息中', 'success')
    } else {
      showToast(res.data.error || '切换状态失败', 'error')
    }
  } catch (err) {
    showToast(err.response?.data?.error || '切换状态失败', 'error')
  } finally {
    isTogglingBusiness.value = false
  }
}

const dishSalesRows = computed(() => {
  const bucket = new Map()
  for (const order of orders.value) {
    if (!completedStatuses.has(order.status)) continue
    const safeItems = Array.isArray(order.items) ? order.items : []
    for (const item of safeItems) {
      const name = item.dish_name || '未命名商品'
      const quantity = Number(item.quantity || 0)
      const revenue = Number(item.subtotal || 0)
      if (!bucket.has(name)) {
        bucket.set(name, { name, quantity: 0, revenue: 0, orders: 0 })
      }
      const target = bucket.get(name)
      target.quantity += quantity
      target.revenue += revenue
      target.orders += 1
    }
  }
  return [...bucket.values()]
    .map((row) => ({
      ...row,
      revenue: Number(row.revenue.toFixed(2))
    }))
    .sort((a, b) => b.quantity - a.quantity)
})

const dishSalesTotalQuantity = computed(() => dishSalesRows.value.reduce((sum, row) => sum + row.quantity, 0))
const dishSalesTotalRevenue = computed(() => dishSalesRows.value.reduce((sum, row) => sum + row.revenue, 0).toFixed(2))

const topDishRows = computed(() => {
  const metric = dishMetric.value
  return [...dishSalesRows.value]
    .sort((a, b) => Number(b[metric] || 0) - Number(a[metric] || 0))
    .slice(0, 8)
})

const topDishMaxMetricValue = computed(() => {
  const metric = dishMetric.value
  const max = Math.max(...topDishRows.value.map((row) => Number(row[metric] || 0)), 0)
  return max > 0 ? max : 1
})

const donutRows = computed(() => {
  const source = [...dishSalesRows.value]
    .sort((a, b) => b.revenue - a.revenue)
    .slice(0, 5)
  const total = source.reduce((sum, row) => sum + row.revenue, 0)
  if (!total) return []
  return source.map((row) => ({
    ...row,
    percent: Number(((row.revenue / total) * 100).toFixed(1))
  }))
})

const donutGradient = computed(() => {
  if (!donutRows.value.length) return 'conic-gradient(#e5e7eb 0 360deg)'
  const colors = ['#0f172a', '#334155', '#64748b', '#94a3b8', '#cbd5e1']
  let start = 0
  const segments = donutRows.value.map((row, index) => {
    const degree = (row.percent / 100) * 360
    const end = start + degree
    const segment = `${colors[index % colors.length]} ${start.toFixed(2)}deg ${end.toFixed(2)}deg`
    start = end
    return segment
  })
  return `conic-gradient(${segments.join(', ')})`
})

const dishMetricLabel = computed(() => (dishMetric.value === 'quantity' ? '销量' : '销售额'))

const filteredOrders = computed(() => {
  if (!orderFilter.value) return orders.value
  return orders.value.filter(o => o.status === orderFilter.value)
})

const startEdit = (dish) => {
  dishForm.value = {
    id: dish.id,
    name: dish.name,
    price: dish.price,
    description: dish.description || '',
    image_path: dish.image_path || '',
    is_available: dish.is_available ? 1 : 0
  }
}

const resetForm = () => {
  dishForm.value = { id: null, name: '', price: '', description: '', image_path: '', is_available: 1 }
}
// Import / Export helpers for dishes CSV
const isImporting = ref(false)
const importProgress = ref({ done: 0, total: 0 })
const importFileRef = ref(null)

const exportDishes = () => {
  if (!dishes.value || !dishes.value.length) {
    showToast('没有可导出的菜品', 'error')
    return
  }
  const headers = ['id', 'name', 'price', 'description', 'image_path', 'is_available']
  const rows = dishes.value.map(d => headers.map(h => (d[h] !== undefined && d[h] !== null) ? String(d[h]).replace(/"/g, '""') : ''))
  const csv = [headers.join(',')].concat(rows.map(r => r.map(c => `"${c}"`).join(','))).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `dishes_export_${new Date().toISOString().slice(0,10)}.csv`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  showToast('已生成导出文件', 'success')
}

const parseCSV = (text) => {
  const lines = text.split(/\r?\n/).filter(Boolean)
  if (!lines.length) return []
  const header = lines[0].split(',').map(h => h.replace(/^"|"$/g, '').trim())
  const data = []
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]
    const cells = []
    let cur = ''
    let inQuotes = false
    for (let j = 0; j < line.length; j++) {
      const ch = line[j]
      if (ch === '"') {
        if (inQuotes && line[j+1] === '"') { cur += '"'; j++ } else { inQuotes = !inQuotes }
      } else if (ch === ',' && !inQuotes) {
        cells.push(cur); cur = ''
      } else {
        cur += ch
      }
    }
    cells.push(cur)
    const obj = {}
    for (let k = 0; k < header.length; k++) {
      obj[header[k]] = (cells[k] || '').trim().replace(/^"|"$/g, '')
    }
    data.push(obj)
  }
  return data
}

const handleImportFile = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  isImporting.value = true
  try {
    const text = await file.text()
    const rows = parseCSV(text)
    // Refresh current dishes to know which ids already belong to this merchant
    await fetchDishes()
    const existingIds = new Set(dishes.value.map(d => Number(d.id)))
    importProgress.value = { done: 0, total: rows.length }
    for (let i = 0; i < rows.length; i++) {
      const r = rows[i]
      const payload = {
        name: (r.name || '').trim(),
        price: (r.price || '').trim() || '0.00',
        description: (r.description || '').trim() || '',
        image_path: (r.image_path || '').trim() || '',
        is_available: (r.is_available && Number(r.is_available) ? 1 : 0)
      }
      try {
        const idNum = r.id ? Number(r.id) : null
        if (idNum && existingIds.has(idNum)) {
          await api.post('/merchant/dish/update', { dish_id: idNum, ...payload })
        } else {
          await api.post('/merchant/dish/create', payload)
        }
        importProgress.value.done++
      } catch (err) {
        console.debug('import row error', err)
      }
    }
    await fetchDishes()
    showToast(`导入完成：成功 ${importProgress.value.done}/${importProgress.value.total}`, 'success')
  } catch (err) {
    showToast('导入失败，请检查文件格式', 'error')
  } finally {
    isImporting.value = false
    importProgress.value = { done: 0, total: 0 }
  }
}

const submitDish = async () => {
  if (!dishForm.value.name || dishForm.value.price === '') {
    showToast('请填写菜品名称和价格', 'error')
    return
  }
  isSavingDish.value = true
  try {
    const payload = {
      dish_id: dishForm.value.id,
      name: dishForm.value.name,
      price: dishForm.value.price,
      description: dishForm.value.description,
      image_path: dishForm.value.image_path,
      is_available: dishForm.value.is_available
    }
    const endpoint = dishForm.value.id ? '/merchant/dish/update' : '/merchant/dish/create'
    const res = await api.post(endpoint, payload)
    if (res.data.ok) {
      showToast(res.data.message || '保存成功', 'success')
      resetForm()
      fetchDishes()
    } else {
      showToast(res.data.error || '保存失败', 'error')
    }
  } catch (err) {
    showToast(err.response?.data?.error || '保存失败', 'error')
  } finally {
    isSavingDish.value = false
  }
}

const toggleAvailability = async (dish) => {
  try {
    const res = await api.post('/merchant/dish/update', {
      dish_id: dish.id,
      is_available: dish.is_available ? 0 : 1
    })
    if (res.data.ok) {
      showToast(dish.is_available ? '已下架' : '已上架', 'success')
      fetchDishes()
    } else {
      showToast(res.data.error || '操作失败', 'error')
    }
  } catch (err) {
    showToast(err.response?.data?.error || '操作失败', 'error')
  }
}

const deleteDish = async (dish) => {
  if (!confirm(`确认删除「${dish.name}」吗？`)) return
  try {
    const res = await api.post('/merchant/dish/delete', { dish_id: dish.id })
    if (res.data.ok) {
      showToast('已删除菜品', 'success')
      fetchDishes()
    } else {
      showToast(res.data.error || '删除失败', 'error')
    }
  } catch (err) {
    showToast(err.response?.data?.error || '删除失败', 'error')
  }
}
</script>

<template>
  <div class="container animate-fade-in">
    <div class="flex-between mb-4">
      <h2 class="page-title mb-0">商家运营中心</h2>
    </div>

    <div class="tabs">
      <button :class="['tab-btn', { active: activeTab === 'dashboard' }]" @click="activeTab = 'dashboard'">概览</button>
      <button :class="['tab-btn', { active: activeTab === 'orders' }]" @click="activeTab = 'orders'">订单管理</button>
      <button :class="['tab-btn', { active: activeTab === 'dishes' }]" @click="activeTab = 'dishes'">菜品管理</button>
      <button :class="['tab-btn', { active: activeTab === 'reviews' }]" @click="activeTab = 'reviews'">用户评价</button>
      <button :class="['tab-btn', { active: activeTab === 'profile' }]" @click="activeTab = 'profile'">商家信息</button>
    </div>

    <div v-if="isLoading" class="loading-state">
      <span class="loader-dark"></span>
      <p>正在加载商家数据...</p>
    </div>

    <div v-else>
      <div v-if="activeTab === 'profile'" class="card" style="max-width: 600px;">
        <h3 class="mb-4">修改商家及账号信息</h3>
        <div class="business-status-wrap">
          <div>
            <div class="status-title">营业状态</div>
            <div class="status-desc">当前：<span :class="['status-pill', profile.is_available ? 'open' : 'closed']">{{ businessStatusText }}</span></div>
          </div>
          <button class="btn-outline" :disabled="isTogglingBusiness" @click="toggleBusinessStatus">
            {{ isTogglingBusiness ? '切换中...' : (profile.is_available ? '切换为休息' : '切换为营业') }}
          </button>
        </div>
        <div class="form-group">
            <label>商家名称</label>
            <input v-model="profile.name" type="text" placeholder="输入商家名称" />
        </div>
        <div class="form-group">
            <label>商家简介</label>
            <textarea v-model="profile.description" rows="3" placeholder="输入商家描述"></textarea>
        </div>
        <div class="form-group">
          <label>商家 Logo 图片</label>
          <input type="file" accept="image/*" @change="handleLogoUpload" />
          <div v-if="isUploadingLogo" class="upload-tip">正在上传图片...</div>
          <div v-if="resolveImageSrc(profile.logo_path)" class="image-preview">
            <img :src="resolveImageSrc(profile.logo_path)" alt="商家 Logo" />
          </div>
        </div>
        <div class="form-group">
          <label>商家 Logo 地址</label>
            <input v-model="profile.logo_path" type="text" placeholder="图片 URL" />
        </div>
        <div class="form-group">
            <label>修改登录密码 (留空则不修改)</label>
            <input v-model="profile.password" type="password" placeholder="输入新密码" />
        </div>
        <div style="text-align: right; margin-top: 1rem">
            <button class="btn-primary" @click="updateProfile">保存修改</button>
        </div>
      </div>

      <div v-if="activeTab === 'dashboard'">
        <div class="card analytics-panel">
          <div class="analytics-header">
            <div>
              <h3 class="section-title mb-0">经营趋势分析</h3>
              <p class="analytics-subtitle">按不同周期查看订单表现，支持直接打印经营报表。</p>
            </div>
            <div class="analytics-actions print-hide">
              <select v-model="analyticsPeriod">
                <option v-for="item in periodOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
              <select v-model="analyticsMetric">
                <option v-for="item in metricOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
              <button class="btn-outline" @click="printReport">打印报表</button>
            </div>
          </div>

          <div class="analytics-kpi">
            <div class="kpi-card">
              <div class="kpi-label">当前区间营业额</div>
              <div class="kpi-value">￥{{ rangeRevenue }}</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">当前区间订单量</div>
              <div class="kpi-value">{{ rangeOrders }} 单</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">当前区间客单价</div>
              <div class="kpi-value">￥{{ rangeAvgTicket }}</div>
            </div>
            <div class="kpi-card" v-if="analyticsPeak">
              <div class="kpi-label">峰值周期 ({{ selectedMetricLabel }})</div>
              <div class="kpi-value">{{ analyticsPeak.label }}</div>
            </div>
          </div>

          <div class="line-chart-wrap" v-if="analyticsRows.length">
            <svg viewBox="0 0 640 240" preserveAspectRatio="none" class="line-chart">
              <defs>
                <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#111827" stop-opacity="0.25" />
                  <stop offset="100%" stop-color="#111827" stop-opacity="0" />
                </linearGradient>
              </defs>
              <polyline :points="`0,220 ${analyticsPoints} 640,220`" fill="url(#trendGradient)" stroke="none" />
              <polyline :points="analyticsPoints" fill="none" stroke="#111827" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
              <circle v-for="(dot, idx) in analyticsDots" :key="idx" :cx="dot.x" :cy="dot.y" r="4.5" fill="#111827" />
            </svg>
            <div class="chart-x-axis">
              <span v-for="row in analyticsRows" :key="row.key">{{ row.label }}</span>
            </div>
          </div>

          <div class="analytics-table-wrap">
            <table class="analytics-table">
              <thead>
                <tr>
                  <th>周期</th>
                  <th>营业额</th>
                  <th>订单量</th>
                  <th>客单价</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in analyticsRows" :key="row.key">
                  <td>{{ row.label }}</td>
                  <td>￥{{ row.revenue.toFixed(2) }}</td>
                  <td>{{ row.orders }}</td>
                  <td>￥{{ row.avgTicket.toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card product-panel">
          <div class="analytics-header">
            <div>
              <h3 class="section-title mb-0">商品销售画像</h3>
              <p class="analytics-subtitle">关注不同商品的销量与收入结构，快速识别主力爆品。</p>
            </div>
            <div class="analytics-actions print-hide">
              <select v-model="dishMetric">
                <option value="quantity">按销量排序</option>
                <option value="revenue">按销售额排序</option>
              </select>
            </div>
          </div>

          <div v-if="!dishSalesRows.length" class="empty-state" style="margin-top: 0.6rem;">暂无可统计的商品销售数据</div>

          <div v-else class="product-chart-grid">
            <div class="bar-panel">
              <h4 class="mini-title">商品{{ dishMetricLabel }}排行榜 (Top 8)</h4>
              <div class="bar-list">
                <div class="bar-row" v-for="row in topDishRows" :key="`${row.name}-${dishMetric}`">
                  <div class="bar-meta">
                    <span class="bar-name">{{ row.name }}</span>
                    <span class="bar-value" v-if="dishMetric === 'quantity'">{{ row.quantity }} 份</span>
                    <span class="bar-value" v-else>￥{{ row.revenue.toFixed(2) }}</span>
                  </div>
                  <div class="bar-track">
                    <div class="bar-fill" :style="{ width: `${Math.max((Number(row[dishMetric] || 0) / topDishMaxMetricValue) * 100, 4)}%` }"></div>
                  </div>
                </div>
              </div>
            </div>

            <div class="donut-panel">
              <h4 class="mini-title">销售额占比 (Top 5)</h4>
              <div class="donut-wrap">
                <div class="donut" :style="{ background: donutGradient }">
                  <div class="donut-center">
                    <div class="donut-k">总销售额</div>
                    <div class="donut-v">￥{{ dishSalesTotalRevenue }}</div>
                  </div>
                </div>
                <div class="donut-legend">
                  <div class="legend-item" v-for="(row, idx) in donutRows" :key="row.name">
                    <span class="legend-dot" :class="`dot-${idx}`"></span>
                    <span class="legend-name">{{ row.name }}</span>
                    <span class="legend-val">{{ row.percent }}%</span>
                  </div>
                </div>
              </div>
              <div class="product-summary">
                <span>累计售出 {{ dishSalesTotalQuantity }} 份</span>
                <span>商品种类 {{ dishSalesRows.length }} 个</span>
              </div>
            </div>
          </div>
        </div>

        <div class="insight-grid">
          <div class="stats-card highlight">
            <h3>累计总营业额</h3>
            <div class="amount">￥{{ totalRevenue }}</div>
            <p>已完成和已评价订单统计。</p>
          </div>

          <div class="stats-card">
            <h3>进行中订单</h3>
            <div class="amount" style="color: #111;">{{ activeCount }}<span class="unit">单</span></div>
            <p>待接单、配送中的订单数。</p>
          </div>

          <div class="stats-card">
            <h3>已履约订单</h3>
            <div class="amount" style="color: #111;">{{ completedCount }}<span class="unit">单</span></div>
            <p>已完成或已评价的订单数。</p>
          </div>

          <div class="stats-card">
            <h3>平均评分</h3>
            <div class="amount" style="color: #111;">{{ avgRating }}<span class="unit">分</span></div>
            <p>基于用户评价的综合评分。</p>
          </div>
        </div>

        <h3 class="section-title mt-4">最新订单</h3>
        <div class="card p-0">
          <div v-if="!orders.length" class="empty-state">暂无订单</div>
          <div v-else class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>订单编号</th>
                  <th>下单时间</th>
                  <th>用户</th>
                  <th>状态</th>
                  <th>配送地址</th>
                  <th class="text-right">金额</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="order in orders.slice(0, 6)" :key="order.id">
                  <td class="text-gray">#{{ order.id }}</td>
                  <td class="text-gray">{{ formatTime(order.created_at) }}</td>
                  <td class="font-medium">{{ order.customer }}</td>
                  <td><span :class="['badge', order.status]">{{ order.status_text }}</span></td>
                  <td class="text-gray">{{ order.delivery_address }}</td>
                  <td class="text-right font-semibold">￥{{ order.total_amount }}</td>
                </tr>
              </tbody>
            </table>
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

      <div v-if="activeTab === 'orders'">
        <div class="flex-between mb-4">
          <h3 class="section-title mb-0">订单列表</h3>
          <div class="filter-group">
            <select v-model="orderFilter">
              <option value="">全部状态</option>
              <option value="pending">等待骑手接单</option>
              <option value="accepted">配送中</option>
              <option value="delivered">已送达</option>
              <option value="completed">已确认收货</option>
              <option value="reviewed">已完成评价</option>
            </select>
          </div>
        </div>

        <div class="card p-0">
          <div v-if="!filteredOrders.length" class="empty-state">暂无符合条件的订单</div>
          <div v-else class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>订单编号</th>
                  <th>下单时间</th>
                  <th>用户</th>
                  <th>状态</th>
                  <th>商品清单</th>
                  <th>骑手</th>
                  <th class="text-right">金额</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="order in filteredOrders" :key="order.id">
                  <td class="text-gray">#{{ order.id }}</td>
                  <td class="text-gray">{{ formatTime(order.created_at) }}</td>
                  <td class="font-medium">{{ order.customer }}</td>
                  <td><span :class="['badge', order.status]">{{ order.status_text }}</span></td>
                  <td>
                    <div v-for="item in order.items" :key="item.dish_name" class="dish-tag">
                      {{ item.dish_name }} x{{ item.quantity }}
                    </div>
                  </td>
                  <td class="text-gray">{{ order.rider || '待接单' }}</td>
                  <td class="text-right font-semibold">￥{{ order.total_amount }}</td>
                  <td class="text-right">
                    <button class="btn-text btn-sm" @click="openContact(order.id)">查看联系方式</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'dishes'">
        <div class="card form-card">
          <h3 class="section-title">{{ dishForm.id ? '编辑菜品' : '新增菜品' }}</h3>
          <div class="import-export-row">
            <div style="display:flex; gap:0.6rem; align-items:center">
              <button class="btn-outline" @click="exportDishes">导出菜品</button>
              <button class="btn-outline" @click="() => importFileRef && importFileRef.click()">导入菜品</button>
              <input ref="importFileRef" type="file" accept=".csv,text/csv" style="display:none" @change="handleImportFile" />
            </div>
            <div style="font-size:0.9rem; color:#6b7280">导入文件格式：CSV，表头 id,name,price,description,image_path,is_available（可选 id 则更新）</div>
          </div>
          <form class="form-grid" @submit.prevent="submitDish">
            <div class="form-group">
              <label>菜品名称</label>
              <input v-model="dishForm.name" type="text" placeholder="例如：香辣鸡腿饭" />
            </div>
            <div class="form-group">
              <label>价格</label>
              <input v-model="dishForm.price" type="number" step="0.01" min="0" placeholder="0.00" />
            </div>
            <div class="form-group full">
              <label>描述</label>
              <textarea v-model="dishForm.description" rows="3" placeholder="菜品特色或口味"></textarea>
            </div>
            <div class="form-group full">
              <label>菜品图片</label>
              <input type="file" accept="image/*" @change="handleDishImageUpload" />
              <div v-if="isUploadingDishImage" class="upload-tip">正在上传图片...</div>
              <div v-if="resolveImageSrc(dishForm.image_path)" class="image-preview image-preview--dish">
                <img :src="resolveImageSrc(dishForm.image_path)" :alt="dishForm.name || '菜品图片'" />
              </div>
            </div>
            <div class="form-group full">
              <label>菜品图片地址</label>
              <input v-model="dishForm.image_path" type="text" placeholder="图片 URL" />
            </div>
            <div class="form-actions full">
              <button type="submit" :disabled="isSavingDish">
                <span v-if="!isSavingDish">保存菜品</span>
                <span v-else class="loader-light"></span>
              </button>
              <button type="button" class="btn-outline" @click="resetForm">重置</button>
            </div>
          </form>
        </div>

        <h3 class="section-title mt-4">菜品列表</h3>
        <div class="card p-0">
          <div v-if="!dishes.length" class="empty-state">暂无菜品，请先新增</div>
          <div v-else class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>图片</th>
                  <th>菜品名称</th>
                  <th>价格</th>
                  <th>状态</th>
                  <th class="text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="dish in dishes" :key="dish.id">
                  <td>
                    <div class="thumb-wrap">
                      <img v-if="resolveImageSrc(dish.image_path)" :src="resolveImageSrc(dish.image_path)" :alt="dish.name" class="dish-thumb" />
                      <div v-else class="dish-thumb dish-thumb--empty">无图</div>
                    </div>
                  </td>
                  <td class="font-medium">{{ dish.name }}</td>
                  <td>￥{{ dish.price }}</td>
                  <td>
                    <span :class="['badge', dish.is_available ? 'available' : 'unavailable']">
                      {{ dish.is_available ? '上架中' : '已下架' }}
                    </span>
                  </td>
                  <td class="text-right">
                    <button class="btn-text" @click="startEdit(dish)">编辑</button>
                    <button class="btn-text" @click="toggleAvailability(dish)">
                      {{ dish.is_available ? '下架' : '上架' }}
                    </button>
                    <button class="btn-text text-red" @click="deleteDish(dish)">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'reviews'">
        <h3 class="section-title">用户评价</h3>
        <div v-if="!reviews.length" class="empty-state">暂无评价</div>
        <div v-else class="review-grid">
          <div class="review-card" v-for="review in reviews" :key="review.id">
            <div class="r-header">
              <div class="reviewer">
                <div class="tiny-avatar">{{ review.customer.charAt(0).toUpperCase() }}</div>
                <strong>{{ review.customer }}</strong>
              </div>
              <span class="rating-stars">
                <span v-for="star in 5" :key="star" :class="{ active: star <= review.rating }">★</span>
              </span>
            </div>
            <p class="r-comment">{{ review.comment || '该用户没有留下文字评价。' }}</p>
            <div class="r-time text-sm" style="color: #9ca3af; margin-top: 10px;" v-if="review.created_at">{{ formatTime(review.created_at) }}</div>
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

.tabs { margin-bottom: 2rem; display: flex; gap: 2rem; border-bottom: 1px solid #ebebeb; }
.tab-btn { background: transparent; color: #999; border: none; font-size: 1.05rem; padding: 0 0 0.8rem 0; border-radius: 0; font-weight: 500; transition: color 0.2s; position: relative; }
.tab-btn:hover { color: #111; }
.tab-btn.active { color: #111; }
.tab-btn.active::after { content: ''; position: absolute; bottom: -1px; left: 0; width: 100%; height: 2px; background: #111; }

.flex-between { display: flex; justify-content: space-between; align-items: center; }
.filter-group select { width: 180px; }
.mb-0 { margin-bottom: 0; }
.mb-4 { margin-bottom: 2rem; }
.mt-4 { margin-top: 3rem; margin-bottom: 1rem; }
.section-title { font-size: 1.2rem; font-weight: 600; }
.text-right { text-align: right; }
.text-gray { color: #6b7280; }
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }

.business-status-wrap { display: flex; justify-content: space-between; align-items: center; gap: 0.8rem; margin-bottom: 1rem; padding: 0.9rem 1rem; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; background: #fafafa; }
.status-title { font-size: 0.86rem; color: #6b7280; margin-bottom: 0.2rem; }
.status-desc { font-size: 0.9rem; color: #111827; }
.status-pill { display: inline-block; padding: 0.14rem 0.5rem; border-radius: 999px; font-size: 0.78rem; font-weight: 600; }
.status-pill.open { background: #dcfce7; color: #166534; }
.status-pill.closed { background: #fee2e2; color: #991b1b; }

.insight-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem; }
.stats-card { background: #fff; padding: 2rem; border-radius: 16px; border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 4px 15px rgba(0,0,0,0.02); }
.stats-card.highlight { background: #111; color: #fff; border: none; }
.stats-card h3 { margin-bottom: 0.5rem; font-size: 1rem; font-weight: 500; opacity: 0.8; }
.stats-card .amount { font-size: 2.6rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem; line-height: 1.1; letter-spacing: -1px; }
.stats-card.highlight .amount { color: #fff; }
.stats-card p { font-size: 0.85rem; opacity: 0.6; }
.unit { font-size: 1rem; font-weight: 500; margin-left: 0.5rem; color: #9ca3af; }

.analytics-panel { margin-bottom: 1.5rem; }
.analytics-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1rem; }
.analytics-subtitle { margin-top: 0.4rem; color: #6b7280; font-size: 0.9rem; }
.analytics-actions { display: flex; align-items: center; gap: 0.8rem; }
.analytics-actions select { width: 140px; }
.analytics-kpi { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 0.9rem; margin-bottom: 1.1rem; }
.kpi-card { border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; padding: 0.85rem 1rem; background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%); }
.kpi-label { color: #6b7280; font-size: 0.82rem; margin-bottom: 0.3rem; }
.kpi-value { color: #111827; font-size: 1.15rem; font-weight: 650; }
.line-chart-wrap { background: #f8fafc; border: 1px solid rgba(17,24,39,0.08); border-radius: 14px; padding: 1rem 1rem 0.8rem; }
.line-chart { width: 100%; height: 220px; display: block; }
.chart-x-axis { margin-top: 0.4rem; display: grid; gap: 0.25rem; grid-template-columns: repeat(auto-fit, minmax(40px, 1fr)); font-size: 0.78rem; color: #6b7280; text-align: center; }
.analytics-table-wrap { margin-top: 0.9rem; overflow-x: auto; }
.analytics-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
.analytics-table th, .analytics-table td { border-bottom: 1px solid rgba(0,0,0,0.06); padding: 0.55rem 0.45rem; text-align: left; }
.analytics-table th { color: #6b7280; font-weight: 600; }

.import-export-row { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin-bottom:0.9rem; }
.import-export-row input[type="file"] { display:none }

.product-panel { margin-bottom: 1.5rem; }
.product-chart-grid { display: grid; grid-template-columns: 1.25fr 1fr; gap: 1rem; }
.bar-panel, .donut-panel { border: 1px solid rgba(17,24,39,0.08); border-radius: 14px; padding: 1rem; background: #fff; }
.mini-title { margin-bottom: 0.8rem; color: #111827; font-size: 0.92rem; }
.bar-list { display: flex; flex-direction: column; gap: 0.65rem; }
.bar-row { display: flex; flex-direction: column; gap: 0.3rem; }
.bar-meta { display: flex; justify-content: space-between; align-items: baseline; gap: 0.8rem; }
.bar-name { color: #334155; font-size: 0.84rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 66%; }
.bar-value { color: #111827; font-size: 0.82rem; font-weight: 600; }
.bar-track { width: 100%; height: 8px; background: #e2e8f0; border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #1f2937 0%, #64748b 100%); }
.donut-wrap { display: grid; grid-template-columns: 170px 1fr; gap: 0.8rem; align-items: center; }
.donut { width: 170px; height: 170px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
.donut-center { width: 108px; height: 108px; border-radius: 50%; background: #fff; box-shadow: inset 0 0 0 1px rgba(0,0,0,0.06); display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 0.5rem; }
.donut-k { color: #64748b; font-size: 0.72rem; }
.donut-v { color: #0f172a; font-size: 0.9rem; font-weight: 700; margin-top: 0.2rem; }
.donut-legend { display: flex; flex-direction: column; gap: 0.4rem; }
.legend-item { display: grid; grid-template-columns: 14px 1fr auto; align-items: center; gap: 0.45rem; font-size: 0.8rem; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot-0 { background: #0f172a; }
.dot-1 { background: #334155; }
.dot-2 { background: #64748b; }
.dot-3 { background: #94a3b8; }
.dot-4 { background: #cbd5e1; }
.legend-name { color: #334155; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.legend-val { color: #0f172a; font-weight: 600; }
.product-summary { display: flex; justify-content: space-between; margin-top: 0.8rem; color: #64748b; font-size: 0.82rem; }

.form-card { margin-bottom: 2rem; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.2rem; }
.form-group { display: flex; flex-direction: column; gap: 0.5rem; }
.form-group.full, .form-actions.full { grid-column: 1 / -1; }
.form-actions { display: flex; gap: 1rem; align-items: center; }
.upload-tip { font-size: 0.85rem; color: #6b7280; }
.image-preview { margin-top: 0.25rem; width: 160px; height: 160px; border-radius: 16px; overflow: hidden; border: 1px solid rgba(0,0,0,0.08); background: #f9fafb; }
.image-preview--dish { width: 220px; height: 140px; }
.image-preview img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb-wrap { width: 64px; }
.dish-thumb { width: 56px; height: 56px; border-radius: 12px; object-fit: cover; display: block; background: #f3f4f6; border: 1px solid rgba(0,0,0,0.06); }
.dish-thumb--empty { display: flex; align-items: center; justify-content: center; color: #9ca3af; font-size: 0.75rem; }

.p-0 { padding: 0; overflow: hidden; }
.table-wrapper { width: 100%; overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; text-align: left; }
.data-table th { padding: 1rem 1.5rem; font-size: 0.85rem; font-weight: 600; color: #6b7280; border-bottom: 1px solid rgba(0,0,0,0.05); background: #fafafa; }
.data-table td { padding: 1.2rem 1.5rem; font-size: 0.95rem; border-bottom: 1px solid rgba(0,0,0,0.02); vertical-align: top; }
.data-table tbody tr:hover { background: rgba(0,0,0,0.01); }
.dish-tag { display: inline-block; background: #f3f4f6; color: #374151; font-size: 0.8rem; padding: 0.2rem 0.5rem; border-radius: 4px; margin-right: 0.4rem; margin-bottom: 0.4rem; }

.badge.available { background: #d1fae5; color: #166534; }
.badge.unavailable { background: #fee2e2; color: #991b1b; }

.review-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; }
.review-card { background: #fff; border-radius: 12px; border: 1px solid rgba(0,0,0,0.05); padding: 1.5rem; box-shadow: 0 4px 15px rgba(0,0,0,0.02); }
.r-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.reviewer { display: flex; align-items: center; gap: 0.5rem; }
.tiny-avatar { width: 28px; height: 28px; border-radius: 50%; background: #111; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; }
.rating-stars { color: #e5e7eb; font-size: 1rem; }
.rating-stars .active { color: #f59e0b; }
.r-comment { color: #4b5563; font-size: 0.9rem; line-height: 1.5; }
.r-time { margin-top: 0.8rem; color: #9ca3af; font-size: 0.8rem; }
.text-red { color: #dc2626; }

@media (max-width: 900px) {
  .analytics-header { flex-direction: column; }
  .analytics-actions { width: 100%; flex-wrap: wrap; }
  .analytics-actions select { flex: 1 1 140px; }
  .product-chart-grid { grid-template-columns: 1fr; }
  .donut-wrap { grid-template-columns: 1fr; justify-items: center; }
  .donut-legend { width: 100%; }
}

@media print {
  .tabs,
  .loading-state,
  .print-hide,
  .modal-overlay,
  .btn-text,
  .form-card,
  .filter-group,
  .page-title {
    display: none !important;
  }

  .container {
    max-width: 100%;
    padding: 0;
  }

  .card,
  .stats-card,
  .review-card {
    box-shadow: none !important;
    border: 1px solid #ddd !important;
    break-inside: avoid;
  }

  .line-chart-wrap {
    background: #fff;
  }
}
</style>
