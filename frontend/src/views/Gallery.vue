<template>
  <div class="gallery-page">
    <h1>Gallery</h1>
    <div class="gallery-header" v-if="auth.isAdmin">
      <p class="gallery-sub">Admin view — all photos unlocked</p>
      <router-link to="/admin/upload" class="btn-primary-sm">Upload Photos</router-link>
    </div>
    <p class="gallery-sub" v-else-if="auth.hasFullAccess">Subscriber — full access</p>
    <p class="gallery-sub" v-else-if="auth.isLoggedIn">Subscribe to unlock full-resolution photos</p>
    <p class="gallery-sub" v-else>Log in and subscribe to unlock full-resolution photos</p>

    <div class="grid" v-if="photos.length">
      <div
        v-for="photo in photos"
        :key="photo.id"
        class="photo-card"
        :class="{ unlocked: !photo.is_locked }"
        @click="handleClick(photo)"
      >
        <div class="img-wrap">
          <img :src="photo.preview_url" :alt="photo.title" />
          <div v-if="photo.is_locked" class="lock-overlay">
            <span>Locked</span>
          </div>
        </div>
        <div class="photo-info">
          <span class="photo-title">{{ photo.title }}</span>
          <span v-if="!photo.is_locked" class="badge-unlocked">Unlocked</span>
        </div>
      </div>
    </div>

    <div v-else-if="loading" class="loading">Loading photos...</div>
    <div v-else class="empty-state">
      <p>No photos available yet.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import api from '../api.js'

const auth = useAuthStore()
const router = useRouter()
const photos = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const endpoint = auth.isLoggedIn ? '/photos/gallery' : '/photos'
    const { data } = await api.get(endpoint)
    photos.value = data
  } catch {
    try {
      const { data } = await api.get('/photos')
      photos.value = data
    } catch {}
  } finally {
    loading.value = false
  }
})

function handleClick(photo) {
  if (photo.is_locked) {
    if (!auth.isLoggedIn) {
      router.push('/login')
    } else {
      router.push('/pricing')
    }
  } else {
    router.push(`/photo/${photo.id}`)
  }
}
</script>

<style scoped>
.gallery-page h1{font-size:2rem;margin-bottom:.25rem}
.gallery-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:2rem}
.gallery-header .gallery-sub{margin-bottom:0}
.gallery-sub{color:#888;margin-bottom:2rem}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.5rem;margin-top:1.5rem}

.photo-card{background:#151515;border-radius:12px;overflow:hidden;border:1px solid #222;cursor:pointer;transition:all .2s}
.photo-card:hover{transform:translateY(-4px);border-color:#333}
.photo-card.unlocked{border-color:#2ecc71}

.img-wrap{position:relative;aspect-ratio:4/3;overflow:hidden}
.img-wrap img{width:100%;height:100%;object-fit:cover;transition:transform .3s}
.photo-card:hover .img-wrap img{transform:scale(1.05)}
.lock-overlay{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.5);font-size:1.2rem;font-weight:600;color:#aaa}

.photo-info{display:flex;align-items:center;justify-content:space-between;padding:.75rem 1rem}
.photo-title{font-size:.9rem;color:#ccc}
.badge-unlocked{font-size:.75rem;color:#2ecc71;background:rgba(46,204,113,.1);padding:.2rem .6rem;border-radius:20px}

.loading,.empty-state{text-align:center;padding:4rem;color:#555;font-size:1.1rem}
</style>
