<template>
  <div class="auth-page">
    <div class="card auth-card">
      <h2>Log In</h2>
      <form @submit.prevent="handleLogin">
        <div class="field">
          <label>Email</label>
          <input v-model="email" type="email" placeholder="you@example.com" required />
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="password" type="password" placeholder="Your password" required />
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" class="btn-primary" :disabled="submitting">
          {{ submitting ? 'Logging in...' : 'Log In' }}
        </button>
      </form>
      <p class="alt-link">Don't have an account? <router-link to="/register">Sign up</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function handleLogin() {
  error.value = ''
  submitting.value = true
  try {
    await auth.login(email.value, password.value)
    router.push('/gallery')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Login failed'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-page{display:flex;justify-content:center;padding-top:4rem}
.auth-card{width:100%;max-width:400px}
.auth-card h2{margin-bottom:1.5rem;font-size:1.5rem}
.field{margin-bottom:1rem}
.field label{display:block;font-size:.85rem;color:#888;margin-bottom:.4rem}
.auth-card .btn-primary{width:100%;margin-top:.5rem}
.alt-link{text-align:center;margin-top:1.5rem;font-size:.85rem;color:#666}
</style>
