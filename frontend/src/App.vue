<template>
  <div id="app">
    <div class="fractal-bg"></div>
    <nav class="navbar">
      <router-link to="/" class="logo">Red Hot Jugs</router-link>
      <div class="nav-links">
        <router-link to="/gallery">Gallery</router-link>
        <router-link to="/pricing">Pricing</router-link>
        <template v-if="auth.isLoggedIn">
          <router-link to="/dashboard">Dashboard</router-link>
          <router-link v-if="auth.isAdmin" to="/admin" class="admin-link">Admin</router-link>
          <button @click="auth.logout()" class="btn-link">Logout</button>
        </template>
        <template v-else>
          <router-link to="/login">Login</router-link>
          <router-link to="/register" class="btn-primary-sm">Sign Up</router-link>
        </template>
      </div>
    </nav>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useAuthStore } from './stores/auth.js'
const auth = useAuthStore()
</script>

<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,sans-serif;background:#0a0a0a;color:#f0f0f0;min-height:100vh}
a{color:#e74c3c;text-decoration:none;transition:color .2s}
a:hover{color:#ff6b5a}

.navbar{display:flex;align-items:center;justify-content:space-between;padding:1rem 2rem;background:#111;border-bottom:1px solid #222;position:sticky;top:0;z-index:100}
.logo{font-size:1.3rem;font-weight:800;color:#e74c3c !important;letter-spacing:-0.5px}
.nav-links{display:flex;align-items:center;gap:1.5rem}
.nav-links a{color:#aaa;font-size:.9rem;font-weight:500}
.nav-links a:hover,.nav-links a.router-link-active{color:#fff}

.btn-link{background:none;border:none;color:#aaa;cursor:pointer;font-size:.9rem;font-weight:500}
.btn-link:hover{color:#fff}
.admin-link{color:#e74c3c !important;font-weight:600}
.btn-primary-sm{background:#e74c3c;color:#fff !important;padding:.4rem 1rem;border-radius:6px;font-weight:600;font-size:.85rem}
.btn-primary-sm:hover{background:#ff6b5a}

main{max-width:1200px;margin:0 auto;padding:2rem}

.btn-primary{display:inline-block;background:#e74c3c;color:#fff;border:none;padding:.75rem 2rem;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;transition:all .2s}
.btn-primary:hover{background:#ff6b5a;transform:translateY(-1px)}
.btn-secondary{display:inline-block;background:#222;color:#fff;border:1px solid #333;padding:.75rem 2rem;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;transition:all .2s}
.btn-secondary:hover{background:#333}

.card{background:#151515;border:1px solid #222;border-radius:12px;padding:2rem}

input[type="email"],input[type="password"],input[type="text"]{width:100%;padding:.75rem 1rem;background:#1a1a1a;border:1px solid #333;border-radius:8px;color:#fff;font-size:.95rem;font-family:inherit}
input:focus{outline:none;border-color:#e74c3c}

.error-msg{color:#e74c3c;font-size:.85rem;margin-top:.5rem}

/* Hypnotic fractal background */
.fractal-bg{position:fixed;inset:0;z-index:-1;overflow:hidden;background:#0a0a0a}

.fractal-bg::before,.fractal-bg::after{
  content:'';position:absolute;inset:-50%;width:200%;height:200%;
}

.fractal-bg::before{
  background:
    repeating-conic-gradient(from 0deg at 50% 50%, #e74c3c08 0deg, transparent 30deg, #ff6b5a06 60deg, transparent 90deg),
    repeating-conic-gradient(from 45deg at 40% 60%, #e74c3c05 0deg, transparent 20deg, #c0392b08 40deg, transparent 60deg),
    repeating-conic-gradient(from 90deg at 60% 40%, #ff6b5a04 0deg, transparent 15deg, #e74c3c06 30deg, transparent 45deg);
  animation:fractalSpin 60s linear infinite;
}

.fractal-bg::after{
  background:
    repeating-conic-gradient(from 180deg at 50% 50%, #e74c3c06 0deg, transparent 25deg, #ff6b5a04 50deg, transparent 75deg),
    repeating-conic-gradient(from 120deg at 35% 65%, #c0392b05 0deg, transparent 18deg, #e74c3c07 36deg, transparent 54deg),
    radial-gradient(ellipse at 30% 70%, #e74c3c0a 0%, transparent 50%),
    radial-gradient(ellipse at 70% 30%, #ff6b5a08 0%, transparent 50%);
  animation:fractalSpinReverse 45s linear infinite;
}

@keyframes fractalSpin{
  0%{transform:rotate(0deg) scale(1)}
  50%{transform:rotate(180deg) scale(1.15)}
  100%{transform:rotate(360deg) scale(1)}
}

@keyframes fractalSpinReverse{
  0%{transform:rotate(360deg) scale(1.1)}
  50%{transform:rotate(180deg) scale(0.95)}
  100%{transform:rotate(0deg) scale(1.1)}
}

#app{position:relative;z-index:1}
</style>
