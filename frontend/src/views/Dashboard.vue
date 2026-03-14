<template>
  <div class="dashboard">
    <h1>Dashboard</h1>

    <div class="card">
      <h3>Account</h3>
      <p class="detail">{{ auth.user?.email }}</p>
      <p v-if="auth.isAdmin" class="status admin" style="margin-top:.5rem">Admin</p>
    </div>

    <div class="card" style="margin-top:1.5rem">
      <h3>Access</h3>
      <template v-if="auth.isAdmin">
        <p class="status active">Full access (Admin)</p>
        <router-link to="/gallery" class="btn-secondary" style="margin-top:1rem">
          Go to Gallery
        </router-link>
      </template>
      <template v-else-if="auth.isSubscribed">
        <p class="status active">Active Subscription</p>
        <p class="detail" v-if="auth.subscription?.current_period_end">
          Renews {{ new Date(auth.subscription.current_period_end).toLocaleDateString() }}
        </p>
        <button @click="auth.openPortal()" class="btn-secondary" style="margin-top:1rem">
          Manage Subscription
        </button>
      </template>
      <template v-else-if="checkingPayment">
        <p class="status pending">Confirming your payment...</p>
      </template>
      <template v-else>
        <p class="status inactive">No active subscription</p>
        <router-link to="/pricing" class="btn-primary" style="margin-top:1rem">
          Subscribe
        </router-link>
      </template>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const route = useRoute()
const checkingPayment = ref(false)

onMounted(async () => {
  // After Stripe embedded checkout, user returns here with ?session_id=...
  // The webhook may not have processed yet, so poll for subscription activation.
  if (route.query.session_id) {
    checkingPayment.value = true
    for (let i = 0; i < 10; i++) {
      await auth.fetchSubscription()
      if (auth.isSubscribed) break
      await new Promise(r => setTimeout(r, 1500))
    }
    checkingPayment.value = false
  }
})
</script>

<style scoped>
.dashboard h1{font-size:2rem;margin-bottom:1.5rem}
.dashboard h3{font-size:1.1rem;margin-bottom:.75rem;color:#aaa}
.detail{color:#888;font-size:.95rem}
.status{font-weight:600;font-size:1.1rem}
.status.active{color:#2ecc71}
.status.inactive{color:#e74c3c}
.status.pending{color:#f39c12;animation:pulse 1.5s infinite}
@keyframes pulse{0%{opacity:.6}50%{opacity:1}100%{opacity:.6}}
.status.admin{color:#e74c3c;font-size:.85rem}
</style>
