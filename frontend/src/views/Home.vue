<template>
  <div class="landing" :style="themeVars">
    <!-- Scanline overlay -->
    <div class="scanlines" :style="{ opacity: crtOpacity }"></div>

    <!-- Hallucination overlay -->
    <Transition name="hallucination">
      <div v-if="hallucinationVisible" class="hallucination-overlay" @click="hallucinationVisible = false">
        <img :src="hallucinationSrc" class="hallucination-img" alt="Hallucination" />
      </div>
    </Transition>

    <!-- Banner (visible from state 1+) -->
    <div class="banner" v-show="currentState >= 1" :style="{ filter: imageFilter }"></div>

    <!-- Header with avatar + Surrender -->
    <div class="header" :style="headerStyle">
      <div class="profile-pic" :style="avatarStyle"></div>
      <h1 class="profile-title">Red Hot Jugs</h1>
      <p class="subtitle">{{ subtitleText }}</p>
      <br />
      <button v-if="currentState < maxStates" class="give-in-btn" @click="progressState">
        Surrender
      </button>
    </div>

    <!-- Preview section with photo carousel -->
    <section class="preview-section" v-if="currentState >= 1">
      <h2 class="section-heading">Preview</h2>
      <div class="carousel" v-if="carouselImages.length">
        <div class="carousel-track">
          <div
            v-for="(img, idx) in carouselImages"
            :key="idx"
            class="carousel-slide"
            :class="{ active: idx === activeSlide }"
          >
            <img :src="img" alt="Preview" :style="{ filter: imageFilter }" />
          </div>
          <div class="carousel-controls">
            <button class="carousel-btn" @click="prevSlide">&lsaquo;</button>
            <button class="carousel-btn" @click="nextSlide">&rsaquo;</button>
          </div>
        </div>
        <div class="carousel-dots">
          <button
            v-for="(_, idx) in carouselImages"
            :key="idx"
            class="carousel-dot"
            :class="{ active: idx === activeSlide }"
            @click="activeSlide = idx"
          ></button>
        </div>
      </div>
      <div v-else-if="loadingPhotos" class="loading-text">Loading previews...</div>
    </section>

    <!-- Follow section -->
    <section class="social-section" v-if="currentState >= 1">
      <h2 class="section-heading">Follow</h2>
      <div class="social-row">
        <a
          v-for="link in socialLinks"
          :key="link.url"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
          class="link-card"
        >
          <span class="link-text">{{ link.label }}</span>
        </a>
      </div>
    </section>

    <!-- Vault panel (state 3) -->
    <Transition name="vault">
      <div v-if="currentState >= 3" class="vault-panel">
        <h2 class="vault-heading">The Vault is Open</h2>

        <!-- CTA — adapts to auth state -->
        <template v-if="auth.hasFullAccess">
          <router-link to="/gallery" class="link-card cta-link">
            <span class="link-text">Enter Gallery</span>
          </router-link>
        </template>
        <template v-else-if="auth.isLoggedIn">
          <p class="cta-sub">Unlock full-resolution access.</p>
          <router-link to="/pricing" class="link-card cta-link">
            <span class="link-text">See Plans</span>
          </router-link>
        </template>
        <template v-else>
          <p class="cta-sub">Create an account to unlock everything.</p>
          <div class="cta-row">
            <router-link to="/register" class="link-card cta-link">
              <span class="link-text">Sign Up</span>
            </router-link>
            <router-link to="/login" class="link-card cta-link">
              <span class="link-text">Log In</span>
            </router-link>
          </div>
        </template>

        <div class="gallery-grid">
          <div v-for="img in galleryImages" :key="img" class="gallery-item">
            <img :src="img" alt="Gallery Image" :style="{ filter: imageFilter }" />
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import api from '../api.js'
import {
  initAudio,
  updateAudioIntensity,
  escalateHallucination,
  setHallucinationCallback,
  dispose,
} from '../services/toneService.js'

const auth = useAuthStore()

// ── State machine ──────────────────────────────
const currentState = ref(0)
const maxStates = 3

// ── Carousel ───────────────────────────────────
const activeSlide = ref(0)
const loadingPhotos = ref(false)
const apiPhotos = ref([])
let carouselInterval = null

const galleryImages = [
  '/linktree/Sassysavvv.svg',
  '/linktree/09CAFF8E-2D3D-4267-9A34-13ECE9D12593.png',
  '/linktree/926E8403-267A-4716-BE2E-667CCE454B03.jpeg',
  '/linktree/GTNg2UeaYAEKZc2.jpg',
  '/linktree/GVdM0DrXwAIEpC6.jpg',
  '/linktree/GYG5Ommb0AE95XD.jpg',
  '/linktree/GYxXMuhbQAQRmQu.jpg',
  '/linktree/IMG_7296.jpeg',
]

const carouselImages = computed(() => {
  // Use API preview photos if available, fall back to gallery images
  if (apiPhotos.value.length) {
    return apiPhotos.value.map((p) => p.preview_url || p.url)
  }
  return galleryImages
})

function nextSlide() {
  activeSlide.value = (activeSlide.value + 1) % carouselImages.value.length
}

function prevSlide() {
  activeSlide.value =
    (activeSlide.value - 1 + carouselImages.value.length) % carouselImages.value.length
}

function startCarousel() {
  stopCarousel()
  carouselInterval = setInterval(nextSlide, 4000)
}

function stopCarousel() {
  if (carouselInterval) {
    clearInterval(carouselInterval)
    carouselInterval = null
  }
}

// ── Hallucination ──────────────────────────────
const hallucinationVisible = ref(false)
const hallucinationSrc = ref('')

function triggerHallucination() {
  const images = carouselImages.value
  if (images.length === 0) return
  hallucinationSrc.value = images[Math.floor(Math.random() * images.length)]
  hallucinationVisible.value = true

  setTimeout(() => {
    hallucinationVisible.value = false
  }, 4000)

  escalateHallucination()
}

setHallucinationCallback(triggerHallucination)

// ── Social links ───────────────────────────────
const socialLinks = [
  { url: 'https://www.instagram.com/redhotjugs', label: 'Instagram' },
  { url: 'https://twitter.com/redhotjugs', label: 'Twitter' },
  { url: 'https://onlyfans.com/redhotjugs', label: 'Spicy' },
  { url: 'https://throne.com/redhotjugs', label: 'Throne | Wishlist' },
  { url: 'https://cash.app/$Sassysavvv', label: 'Cashapp' },
]

// ── Theme CSS variables derived from state ─────
const themeVars = computed(() => {
  const s = currentState.value
  if (s === 0)
    return {
      '--bg-color': '#ffe6ea',
      '--text-color': '#ff3366',
      '--card-bg': 'rgba(255, 255, 255, 0.85)',
      '--card-border': '#ffb3c6',
      '--shadow-color': 'rgba(255, 179, 198, 0.6)',
      '--btn-bg': '#ff3366',
      '--btn-text': '#fff',
      '--vignette': 'transparent',
    }
  if (s === 1)
    return {
      '--bg-color': '#ff99aa',
      '--text-color': '#ff3366',
      '--card-bg': 'rgba(255, 255, 255, 0.85)',
      '--card-border': '#ffb3c6',
      '--shadow-color': 'rgba(255, 179, 198, 0.6)',
      '--btn-bg': '#ff3366',
      '--btn-text': '#fff',
      '--vignette': 'inset 0 0 50px rgba(255, 0, 51, 0.1)',
    }
  if (s === 2)
    return {
      '--bg-color': '#4a0011',
      '--text-color': '#ff0033',
      '--card-bg': 'rgba(255, 255, 255, 0.85)',
      '--card-border': '#ff0033',
      '--shadow-color': 'rgba(255, 0, 51, 0.8)',
      '--btn-bg': '#ff0033',
      '--btn-text': '#000',
      '--vignette': 'inset 0 0 100px rgba(255, 0, 51, 0.4)',
    }
  // s === 3
  return {
    '--bg-color': '#050002',
    '--text-color': '#ff0033',
    '--card-bg': 'rgba(15, 0, 5, 0.9)',
    '--card-border': '#ff0033',
    '--shadow-color': 'rgba(255, 0, 51, 0.8)',
    '--btn-bg': '#ff0033',
    '--btn-text': '#000',
    '--vignette': 'inset 0 0 150px rgba(255, 0, 51, 0.6)',
  }
})

const crtOpacity = computed(() => {
  if (currentState.value === 2) return 0.5
  if (currentState.value >= 3) return 1
  return 0
})

const imageFilter = computed(() => {
  if (currentState.value >= 3)
    return 'grayscale(100%) contrast(180%) sepia(100%) hue-rotate(330deg) saturate(300%)'
  return 'none'
})

const subtitleText = computed(() => {
  const s = currentState.value
  if (s === 0) return 'You have to earn access.'
  if (s === 1) return 'A little further...'
  if (s === 2) return 'Almost there.'
  return 'Access Granted.'
})

const headerStyle = computed(() => {
  if (currentState.value === 2) return { animation: 'violent-shake 0.2s infinite' }
  return {}
})

const avatarStyle = computed(() => {
  const base = { filter: imageFilter.value }
  if (currentState.value >= 3) base.animation = 'breathe 1s infinite'
  return base
})

// ── Interaction ────────────────────────────────
async function progressState() {
  if (currentState.value >= maxStates) return
  await initAudio(() => currentState.value)
  currentState.value++
  updateAudioIntensity(currentState.value, maxStates)

  // Start carousel + load photos on first progression
  if (currentState.value === 1) {
    loadPreview()
    startCarousel()
  }
}

async function loadPreview() {
  if (apiPhotos.value.length) return
  loadingPhotos.value = true
  try {
    const endpoint = auth.isLoggedIn ? '/photos/gallery' : '/photos'
    const { data } = await api.get(endpoint)
    apiPhotos.value = data
  } catch {
    try {
      const { data } = await api.get('/photos')
      apiPhotos.value = data
    } catch {
      /* fall back to gallery images */
    }
  } finally {
    loadingPhotos.value = false
  }
}

// ── Cleanup ────────────────────────────────────
onUnmounted(() => {
  stopCarousel()
  dispose()
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

.landing {
  min-height: 100vh;
  background-color: var(--bg-color);
  color: var(--text-color);
  font-family: 'Inter', sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  overflow-x: hidden;
  position: relative;
  transition: background-color 1s ease, color 1s ease;
  box-shadow: var(--vignette);
}

/* ─── Scanline overlay ─── */
.scanlines {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255, 0, 51, 0.15) 3px,
    rgba(0, 0, 0, 0.2) 3px
  );
  pointer-events: none;
  z-index: 998;
  transition: opacity 1s;
}

/* ─── Banner ─── */
.banner {
  width: 100%;
  height: 200px;
  background-image: url('https://public.onlyfans.com/files/j/jd/jdc/jdcuvtfzw5ne5dolulri0zxwwwbwbwgnq31709177480/387693175/header.jpg');
  background-size: cover;
  background-position: center;
  border-bottom: 3px solid var(--card-border);
  box-shadow: 0 4px 15px var(--shadow-color);
  transition: all 1s ease;
  margin-bottom: 2rem;
}

/* ─── Header ─── */
.header {
  text-align: center;
  z-index: 10;
  margin-bottom: 2rem;
}

.profile-pic {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  margin: 2rem auto 1rem;
  background-image: url('https://ugc.production.linktr.ee/d71ebae8-a001-483a-aa09-a6ae0d842111_6AngKleAEBh9WZKVzbKgAA52kKV2.jpeg?io=true&size=thumbnail-stack_v1_0');
  background-size: cover;
  background-position: center;
  border: 4px solid var(--card-border);
  box-shadow: 0 0 30px var(--shadow-color);
  transition: all 0.5s ease;
}

.profile-title {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin: 0;
}

.subtitle {
  opacity: 0.7;
}

/* ─── Surrender button ─── */
.give-in-btn {
  background: var(--btn-bg);
  color: var(--btn-text);
  border: none;
  padding: 1.5rem 3rem;
  border-radius: 50px;
  font-size: 1.2rem;
  font-weight: 800;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 2px;
  box-shadow: 0 0 20px var(--shadow-color);
  transition: all 0.3s ease;
  animation: breathe 2s infinite;
}

.give-in-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 0 40px var(--shadow-color);
}

/* ─── Section headings ─── */
.section-heading {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 3px;
  text-align: center;
  margin-bottom: 1.25rem;
  opacity: 0.8;
}

/* ─── Carousel ─── */
.preview-section {
  width: 100%;
  max-width: 450px;
  padding: 0 2rem;
  z-index: 10;
}

.carousel {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: 12px;
  border: 2px solid var(--card-border);
  box-shadow: 0 4px 20px var(--shadow-color);
}

.carousel-track {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  background: #000;
}

.carousel-slide {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  transform: scale(0.92);
  transition: opacity 0.6s ease, transform 0.6s ease;
  pointer-events: none;
}

.carousel-slide.active {
  opacity: 1;
  transform: scale(1);
  pointer-events: auto;
}

.carousel-slide img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: filter 1s ease;
}

.carousel-controls {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  transform: translateY(-50%);
  display: flex;
  justify-content: space-between;
  padding: 0 0.5rem;
  pointer-events: none;
  z-index: 5;
}

.carousel-btn {
  pointer-events: auto;
  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s;
  backdrop-filter: blur(4px);
}

.carousel-btn:hover {
  background: var(--shadow-color);
}

.carousel-dots {
  display: flex;
  justify-content: center;
  gap: 6px;
  padding: 0.75rem 0;
  background: var(--card-bg);
}

.carousel-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1.5px solid var(--card-border);
  background: transparent;
  cursor: pointer;
  transition: background 0.3s, transform 0.3s;
  padding: 0;
}

.carousel-dot.active {
  background: var(--text-color);
  transform: scale(1.3);
}

.loading-text {
  text-align: center;
  padding: 2rem;
  opacity: 0.5;
}

/* ─── Social / Follow ─── */
.social-section {
  width: 100%;
  max-width: 450px;
  padding: 1rem 2rem;
  z-index: 10;
}

.social-row {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.link-card {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 60px;
  background: var(--card-bg);
  border: 2px solid var(--card-border);
  border-radius: 30px;
  text-decoration: none;
  color: var(--text-color);
  font-weight: 600;
  font-size: 1.1rem;
  overflow: hidden;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  backdrop-filter: blur(5px);
}

.link-card:hover {
  transform: translateY(-3px) scale(1.02);
  background: var(--shadow-color);
  box-shadow: 0 8px 25px var(--shadow-color);
}

.link-text {
  padding: 0 2rem;
  text-align: center;
}

/* ─── Vault panel (state 3) ─── */
.vault-panel {
  width: 100%;
  max-width: 800px;
  background: var(--card-bg);
  border: 2px solid var(--card-border);
  border-radius: 16px;
  padding: 2rem;
  box-shadow: 0 10px 40px var(--shadow-color);
  backdrop-filter: blur(12px);
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
  margin-top: 2rem;
}

.vault-heading {
  text-align: center;
  margin-bottom: 1rem;
}

.cta-link {
  text-decoration: none;
}

.cta-sub {
  text-align: center;
  opacity: 0.7;
  margin-bottom: 0.5rem;
}

.cta-row {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.cta-row .link-card {
  flex: 1;
}

/* ─── Gallery grid ─── */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 15px;
  margin-top: 1.5rem;
  width: 100%;
}

.gallery-item {
  aspect-ratio: 1 / 1;
  overflow: hidden;
  border-radius: 12px;
  border: 2px solid var(--card-border);
  box-shadow: 0 4px 10px var(--shadow-color);
  transition: transform 0.3s ease;
}

.gallery-item:hover {
  transform: scale(1.05);
}

.gallery-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: filter 1s ease;
}

/* ─── Hallucination overlay ─── */
.hallucination-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  cursor: pointer;
}

.hallucination-img {
  max-width: 90%;
  max-height: 90%;
  object-fit: contain;
  box-shadow: 0 0 50px rgba(255, 255, 255, 0.2);
  transform: scale(0.8);
  animation: hallucinateZoom 3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

/* ─── Vue transitions ─── */
.hallucination-enter-active {
  transition: opacity 1.5s ease;
}
.hallucination-leave-active {
  transition: opacity 1.5s ease;
}
.hallucination-enter-from,
.hallucination-leave-to {
  opacity: 0;
}

.vault-enter-active {
  animation: slideUp 0.5s forwards;
}

/* ─── Keyframes ─── */
@keyframes breathe {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes violent-shake {
  0% {
    transform: translate(1px, 1px) rotate(0deg);
  }
  25% {
    transform: translate(-2px, -2px) rotate(-1deg);
  }
  50% {
    transform: translate(3px, 0px) rotate(1deg);
  }
  75% {
    transform: translate(-1px, 2px) rotate(0deg);
  }
  100% {
    transform: translate(1px, -1px) rotate(0deg);
  }
}

@keyframes hallucinateZoom {
  to {
    transform: scale(1);
  }
}
</style>
