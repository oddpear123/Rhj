<template>
  <div class="admin-upload-container">
    <div v-if="!isAdmin" class="access-denied">
      <h2>403 Forbidden</h2>
      <p>Your hands don't belong here. Admin access required.</p>
    </div>

    <div v-else class="upload-vault">
      <h2>Vault Uploader</h2>
      <p class="subtitle">Drop photos here to add to the gallery.</p>

      <div
        class="drop-zone"
        :class="{ 'is-dragging': isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <span v-if="!selectedFile">Drag & Drop a photo here, or click to browse</span>
        <span v-else class="file-selected">{{ selectedFile.name }} ({{ formatSize(selectedFile.size) }})</span>

        <input
          type="file"
          ref="fileInput"
          class="hidden-input"
          accept="image/*"
          @change="handleFileSelect"
        >
      </div>

      <div class="title-field" v-if="selectedFile">
        <label>Title</label>
        <input v-model="title" type="text" placeholder="Photo title" />
      </div>

      <div class="upload-controls" v-if="selectedFile">
        <button
          class="upload-btn"
          :disabled="isUploading"
          @click="uploadToBackend"
        >
          {{ isUploading ? 'Uploading...' : 'Send to Vault' }}
        </button>
        <button
          class="cancel-btn"
          :disabled="isUploading"
          @click="clearSelection"
        >
          Cancel
        </button>
      </div>

      <div class="progress-container" v-if="isUploading || uploadComplete">
        <div class="progress-bar" :style="{ width: uploadProgress + '%' }"></div>
        <span class="progress-text" v-if="!uploadComplete">{{ uploadProgress }}%</span>
        <span class="progress-text success" v-else>Upload Complete. Media Secured.</span>
      </div>
      
      <div class="error-message" v-if="uploadError">
        {{ uploadError }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth.js'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.isAdmin)

const fileInput = ref(null)
const isDragging = ref(false)
const selectedFile = ref(null)
const title = ref('')
const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadComplete = ref(false)
const uploadError = ref(null)

const triggerFileInput = () => {
  if (!isUploading.value) fileInput.value.click()
}

const handleFileSelect = (event) => {
  validateAndSetFile(event.target.files[0])
}

const handleDrop = (event) => {
  isDragging.value = false
  validateAndSetFile(event.dataTransfer.files[0])
}

const validateAndSetFile = (file) => {
  if (!file) return
  if (!file.type.startsWith('image/')) {
    uploadError.value = 'Invalid file type. Only images are allowed.'
    selectedFile.value = null
    return
  }
  uploadError.value = null
  uploadComplete.value = false
  uploadProgress.value = 0
  selectedFile.value = file
  if (!title.value) title.value = file.name.replace(/\.[^.]+$/, '')
}

const clearSelection = () => {
  selectedFile.value = null
  title.value = ''
  uploadError.value = null
  if (fileInput.value) fileInput.value.value = ''
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const uploadToBackend = () => {
  if (!selectedFile.value) return

  isUploading.value = true
  uploadError.value = null

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('title', title.value || 'Untitled')

  const xhr = new XMLHttpRequest()

  xhr.upload.addEventListener('progress', (event) => {
    if (event.lengthComputable) {
      uploadProgress.value = Math.round((event.loaded * 100) / event.total)
    }
  })

  xhr.addEventListener('load', () => {
    isUploading.value = false
    if (xhr.status >= 200 && xhr.status < 300) {
      uploadComplete.value = true
      setTimeout(() => clearSelection(), 3000)
    } else {
      uploadError.value = `Upload failed: ${xhr.statusText || 'Server error'}`
    }
  })

  xhr.addEventListener('error', () => {
    isUploading.value = false
    uploadError.value = 'Network error occurred during upload.'
  })

  // VITE_API_URL is "/api" in prod, "http://localhost:8000" in dev
  // Backend route is POST /photos/admin/upload
  xhr.open('POST', `${import.meta.env.VITE_API_URL}/photos/admin/upload`)
  xhr.setRequestHeader('Authorization', `Bearer ${authStore.token}`)
  xhr.send(formData)
}
</script>

<style scoped>
.admin-upload-container {
  max-width: 800px;
  margin: 2rem auto;
  color: #e0e0e0;
  font-family: 'Inter', sans-serif;
}

.access-denied {
  text-align: center;
  padding: 4rem;
  background: #1a1014;
  border: 1px solid #4a1525;
  border-radius: 8px;
  color: #ff3366;
}

.upload-vault {
  background: #111;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  border: 1px solid #333;
}

.subtitle {
  color: #888;
  margin-bottom: 2rem;
}

.drop-zone {
  border: 2px dashed #444;
  border-radius: 8px;
  padding: 4rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #181818;
}

.drop-zone.is-dragging, .drop-zone:hover {
  border-color: #ff3366;
  background: #1f1418;
}

.hidden-input {
  display: none;
}

.file-selected {
  color: #ff3366;
  font-weight: 600;
}

.title-field {
  margin-top: 1.5rem;
}
.title-field label {
  display: block;
  font-size: .85rem;
  color: #888;
  margin-bottom: .4rem;
}

.upload-controls {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

button {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  transition: opacity 0.2s;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-btn {
  background: #ff3366;
  color: white;
  flex: 1;
}

.cancel-btn {
  background: #333;
  color: #fff;
}

.progress-container {
  margin-top: 1.5rem;
  height: 24px;
  background: #222;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #cc2952, #ff3366);
  transition: width 0.1s linear;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.8rem;
  font-weight: bold;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
}

.progress-text.success {
  color: #fff;
}

.error-message {
  margin-top: 1rem;
  color: #ff4444;
  text-align: center;
  padding: 0.5rem;
  background: rgba(255, 68, 68, 0.1);
  border-radius: 4px;
}
</style>