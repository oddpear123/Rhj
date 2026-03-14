<template>
  <div class="auth-page">
    <div class="card auth-card">
      <h2>Create Account</h2>
      <form @submit.prevent="handleRegister">
        <div class="field">
          <label>Email</label>
          <input v-model="email" type="email" placeholder="you@example.com" required />
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="password" type="password" placeholder="Min 8 characters" required minlength="8" />
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" class="btn-primary" :disabled="submitting">
          {{ submitting ? 'Creating account...' : 'Sign Up' }}
        </button>
      </form>
      <p class="alt-link">Already have an account? <router-link to="/login">Log in</router-link></p>
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

async function handleRegister() {
  error.value = ''
  submitting.value = true
  try {
    await auth.register(email.value, password.value)
    router.push('/gallery')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Registration failed'
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
