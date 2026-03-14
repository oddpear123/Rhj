import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api.js'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token'))
  const subscription = ref(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.is_admin === true)
  const isSubscribed = computed(() => subscription.value?.is_active === true)
  const hasFullAccess = computed(() => isAdmin.value || isSubscribed.value)

  async function register(email, password) {
    const { data } = await api.post('/auth/register', { email, password })
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    await fetchUser()
  }

  async function login(email, password) {
    const { data } = await api.post('/auth/login', { email, password })
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    await fetchUser()
  }

  function logout() {
    token.value = null
    user.value = null
    subscription.value = null
    localStorage.removeItem('token')
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const { data } = await api.get('/auth/me')
      user.value = data
      await fetchSubscription()
    } catch {
      logout()
    }
  }

  async function fetchSubscription() {
    if (!token.value) return
    try {
      const { data } = await api.get('/subscription/status')
      subscription.value = data
    } catch {
      subscription.value = null
    }
  }

  async function createCheckout(plan = '1month') {
    const { data } = await api.post('/subscription/create-checkout', { plan })
    window.location.href = data.checkout_url
  }

  async function openPortal() {
    const { data } = await api.post('/subscription/portal')
    window.location.href = data.portal_url
  }

  // Initialize on store creation
  if (token.value) {
    fetchUser()
  }

  return {
    user, token, subscription, loading,
    isLoggedIn, isAdmin, isSubscribed, hasFullAccess,
    register, login, logout, fetchUser, fetchSubscription,
    createCheckout, openPortal,
  }
})
