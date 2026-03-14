<template>
  <div class="landing" :class="{ entered: phase >= 1 }">

    <!-- ─── PHASE 0: Full-screen splash ─── -->
    <Transition name="fade">
      <div v-if="phase === 0" class="splash" @click="enter">
        <div class="splash-inner">
          <div class="splash-avatar"></div>
          <h1 class="splash-title">Red Hot Jugs</h1>
          <p class="splash-hint">Tap to enter</p>
        </div>
      </div>
    </Transition>

    <!-- ─── PHASE 1: Teaser showcase ─── -->
    <Transition name="rise">
      <div v-if="phase >= 1" class="showcase">

        <!-- Hero banner -->
        <section class="hero-section">
          <div class="hero-avatar"></div>
          <h1 class="hero-title">Red Hot Jugs</h1>
          <p class="hero-sub">Premium. Exclusive. Yours.</p>
        </section>

        <!-- Preview gallery (blurred) -->
        <section class="preview-section">
          <h2 class="section-heading">Preview</h2>
          <div class="preview-grid" v-if="photos.length">
            <div
              v-for="photo in photos"
              :key="photo.id"
              class="preview-card"
              @click="handlePhotoClick(photo)"
            >
              <img :src="photo.preview_url" :alt="photo.title" />
              <div v-if="photo.is_locked" class="locked-badge">Locked</div>
            </div>
          </div>
          <div v-else-if="loadingPhotos" class="loading-text">Loading previews...</div>
        </section>

        <!-- Social links -->
        <section class="social-section">
          <h2 class="section-heading">Follow</h2>
          <div class="social-row">
            <a
              v-for="link in socialLinks"
              :key="link.url"
              :href="link.url"
              target="_blank"
              rel="noopener noreferrer"
              class="social-pill"
            >
              {{ link.label }}
            </a>
          </div>
        </section>

        <!-- CTA — adapts to auth state -->
        <section class="cta-section">
          <template v-if="auth.hasFullAccess">
            <router-link to="/gallery" class="cta-btn">Enter Gallery</router-link>
          </template>
          <template v-else-if="auth.isLoggedIn">
            <p class="cta-sub">You're in. Unlock full-resolution access.</p>
            <router-link to="/pricing" class="cta-btn">See Plans</router-link>
          </template>
          <template v-else>
            <p class="cta-sub">Create an account to unlock everything.</p>
            <div class="cta-row">
              <router-link to="/register" class="cta-btn">Sign Up</router-link>
              <router-link to="/login" class="cta-btn cta-secondary">Log In</router-link>
            </div>
          </template>
        </section>

      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import api from '../api.js'

const auth = useAuthStore()
const router = useRouter()

// Skip splash for returning authenticated subscribers
const phase = ref(auth.hasFullAccess ? 1 : 0)

const photos = ref([])
const loadingPhotos = ref(false)

const socialLinks = [
  { url: 'https://www.instagram.com/redhotjugs', label: 'Instagram' },
  { url: 'https://twitter.com/redhotjugs', label: 'Twitter' },
  { url: 'https://onlyfans.com/redhotjugs', label: 'OnlyFans' },
  { url: 'https://throne.com/redhotjugs', label: 'Wishlist' },
  { url: 'https://cash.app/$Sassysavvv', label: 'Cashapp' },
]

function enter() {
  phase.value = 1
  loadPreview()
}

async function loadPreview() {
  if (photos.value.length) return
  loadingPhotos.value = true
  try {
    const endpoint = auth.isLoggedIn ? '/photos/gallery' : '/photos'
    const { data } = await api.get(endpoint)
    photos.value = data
  } catch {
    try {
      const { data } = await api.get('/photos')
      photos.value = data
    } catch { /* no photos available yet */ }
  } finally {
    loadingPhotos.value = false
  }
}

function handlePhotoClick(photo) {
  if (!photo.is_locked) {
    router.push(`/photo/${photo.id}`)
  } else if (!auth.isLoggedIn) {
    router.push('/register')
  } else {
    router.push('/pricing')
  }
}

onMounted(() => {
  // Pre-fetch previews if we skipped splash
  if (phase.value >= 1) loadPreview()
})
</script>

<style scoped>
/* ─── Splash (Phase 0) ─── */
.splash {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0a;
  cursor: pointer;
}

.splash-inner {
  text-align: center;
  animation: breathe 3s ease-in-out infinite;
}

.splash-avatar {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  margin: 0 auto 1.5rem;
  background-image: url('https://ugc.production.linktr.ee/d71ebae8-a001-483a-aa09-a6ae0d842111_6AngKleAEBh9WZKVzbKgAA52kKV2.jpeg?io=true&size=thumbnail-stack_v1_0');
  background-size: cover;
  background-position: center;
  border: 3px solid #e74c3c;
  box-shadow: 0 0 40px rgba(231, 76, 60, 0.4);
}

.splash-title {
  font-size: 2.5rem;
  font-weight: 800;
  letter-spacing: -1px;
  color: #fff;
  margin-bottom: 0.5rem;
}

.splash-hint {
  color: #555;
  font-size: 0.85rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  animation: pulse 2s ease-in-out infinite;
}

/* ─── Showcase (Phase 1) ─── */
.showcase {
  display: flex;
  flex-direction: column;
  gap: 3rem;
  padding-bottom: 4rem;
}

.hero-section {
  text-align: center;
  padding-top: 1rem;
}

.hero-avatar {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  margin: 0 auto 1rem;
  background-image: url('https://ugc.production.linktr.ee/d71ebae8-a001-483a-aa09-a6ae0d842111_6AngKleAEBh9WZKVzbKgAA52kKV2.jpeg?io=true&size=thumbnail-stack_v1_0');
  background-size: cover;
  background-position: center;
  border: 3px solid #e74c3c;
  box-shadow: 0 0 30px rgba(231, 76, 60, 0.3);
}

.hero-title {
  font-size: 2.5rem;
  font-weight: 800;
  letter-spacing: -1px;
  margin-bottom: 0.25rem;
}

.hero-sub {
  color: #666;
  font-size: 1.1rem;
  font-weight: 500;
}

/* ─── Preview grid ─── */
.section-heading {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 3px;
  color: #555;
  margin-bottom: 1.25rem;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 1rem;
}

.preview-card {
  position: relative;
  aspect-ratio: 3 / 4;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #222;
  cursor: pointer;
  transition: transform 0.25s, border-color 0.25s;
}

.preview-card:hover {
  transform: translateY(-4px) scale(1.02);
  border-color: #e74c3c;
}

.preview-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.locked-badge {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
  padding: 1.5rem 0.75rem 0.5rem;
  text-align: center;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: #888;
}

.loading-text {
  text-align: center;
  color: #444;
  padding: 2rem;
}

/* ─── Social links ─── */
.social-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  justify-content: center;
}

.social-section {
  text-align: center;
}

.social-pill {
  display: inline-block;
  padding: 0.5rem 1.25rem;
  border: 1px solid #333;
  border-radius: 50px;
  font-size: 0.85rem;
  font-weight: 500;
  color: #aaa;
  text-decoration: none;
  transition: all 0.2s;
}

.social-pill:hover {
  border-color: #e74c3c;
  color: #fff;
  background: rgba(231, 76, 60, 0.1);
}

/* ─── CTA ─── */
.cta-section {
  text-align: center;
  padding: 2rem 0;
}

.cta-sub {
  color: #666;
  margin-bottom: 1.25rem;
  font-size: 1rem;
}

.cta-row {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.cta-btn {
  display: inline-block;
  background: #e74c3c;
  color: #fff;
  text-decoration: none;
  padding: 0.85rem 2.5rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 700;
  transition: all 0.2s;
}

.cta-btn:hover {
  background: #ff6b5a;
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(231, 76, 60, 0.3);
}

.cta-secondary {
  background: transparent;
  border: 1px solid #333;
  color: #aaa;
}

.cta-secondary:hover {
  background: #1a1a1a;
  border-color: #555;
  color: #fff;
}

/* ─── Transitions ─── */
.fade-leave-active {
  transition: opacity 0.6s ease;
}
.fade-leave-to {
  opacity: 0;
}

.rise-enter-active {
  transition: opacity 0.8s ease 0.3s, transform 0.8s ease 0.3s;
}
.rise-enter-from {
  opacity: 0;
  transform: translateY(30px);
}

/* ─── Keyframes ─── */
@keyframes breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}

@keyframes pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.8; }
}
</style>
