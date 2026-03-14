<template>
  <div class="home">
    <div class="hero">
      <h1>Red Hot Jugs</h1>
      <p class="tagline">Premium photo content. Exclusive access.</p>
      <div class="hero-actions">
        <router-link to="/gallery" class="btn-primary">Browse Gallery</router-link>
        <router-link to="/register" class="btn-secondary" v-if="!auth.isLoggedIn">Get Started</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth.js'
const auth = useAuthStore()
</script>

<style scoped>
.home{display:flex;align-items:center;justify-content:center;min-height:70vh}
.hero{text-align:center}
.hero h1{font-size:3.5rem;font-weight:800;letter-spacing:-1px;margin-bottom:.5rem}
.tagline{font-size:1.2rem;color:#888;margin-bottom:2rem}
.hero-actions{display:flex;gap:1rem;justify-content:center}
</style>
