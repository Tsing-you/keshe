import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Customer from '../views/Customer.vue'
import MerchantDetail from '../views/MerchantDetail.vue'
import Rider from '../views/Rider.vue'
import Merchant from '../views/Merchant.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: Login },
  { path: '/customer', name: 'Customer', component: Customer, meta: { role: 'customer' } },
  { path: '/customer/merchant/:id', name: 'MerchantDetail', component: MerchantDetail, meta: { role: 'customer' } },
  { path: '/rider', name: 'Rider', component: Rider, meta: { role: 'rider' } },
  { path: '/merchant', name: 'Merchant', component: Merchant, meta: { role: 'merchant' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  if (to.name !== 'Login' && !user) {
    next({ name: 'Login' })
  } else if (to.name === 'Login' && user) {
    if(user.role === 'customer') next({ name: 'Customer' })
    else if (user.role === 'rider') next({ name: 'Rider' })
    else if (user.role === 'merchant') next({ name: 'Merchant' })
    else next()
  } else if (to.meta.role && user && to.meta.role !== user.role) {
    // Role mismatch, redirect to right layout
    if(user.role === 'customer') next({ name: 'Customer' })
    else if (user.role === 'rider') next({ name: 'Rider' })
    else if (user.role === 'merchant') next({ name: 'Merchant' })
    else next({ name: 'Login' })
  } else {
    next()
  }
})

export default router
