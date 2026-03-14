<template>
  <div class="photo-detail" v-if="photo">
    <router-link to="/gallery" class="back-link">Back to Gallery</router-link>
    <h1>{{ photo.title }}</h1>
    <div class="photo-wrap">
      <img :src="photo.full_url" :alt="photo.title" />
    </div>
    <p class="meta">Uploaded {{ new Date(photo.uploaded_at).toLocaleDateString() }}</p>
  </div>
  <div v-else-if="loading" class="loading">Loading...</div>
  <div v-else class="error-state card">
    <p>{{ error || 'Photo not found' }}</p>
    <router-link to="/gallery" class="btn-secondary" style="margin-top:1rem">Back to Gallery</router-link>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api.js'

const route = useRoute()
const photo = ref(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get(`/photos/${route.params.id}/full`)
    photo.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load photo'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.photo-detail{max-width:900px;margin:0 auto}
.back-link{display:inline-block;margin-bottom:1rem;color:#888;font-size:.9rem}
.back-link:hover{color:#fff}
.photo-detail h1{font-size:1.8rem;margin-bottom:1rem}
.photo-wrap{border-radius:12px;overflow:hidden;border:1px solid #222}
.photo-wrap img{width:100%;display:block}
.meta{color:#666;font-size:.85rem;margin-top:1rem}
.loading,.error-state{text-align:center;padding:4rem;color:#555}
</style>
