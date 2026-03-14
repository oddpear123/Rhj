<template>
  <div class="admin-panel">
    <div v-if="!auth.isAdmin" class="access-denied">
      <h2>403 Forbidden</h2>
      <p>Admin access required.</p>
    </div>

    <template v-else>
      <div class="admin-header">
        <h1>Admin Panel</h1>
        <div class="header-actions">
          <router-link to="/admin/upload" class="btn-action">Upload Photos</router-link>
        </div>
      </div>

      <!-- Stats -->
      <div class="stats-row" v-if="stats">
        <div class="stat-card">
          <span class="stat-value">{{ stats.total_users }}</span>
          <span class="stat-label">Users</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.total_photos }}</span>
          <span class="stat-label">Photos</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.active_subscriptions }}</span>
          <span class="stat-label">Active Subs</span>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        <button
          :class="{ active: activeTab === 'photos' }"
          @click="activeTab = 'photos'"
        >Photos</button>
        <button
          :class="{ active: activeTab === 'users' }"
          @click="activeTab = 'users'"
        >Users</button>
      </div>

      <!-- Photos Tab -->
      <div v-if="activeTab === 'photos'" class="tab-content">
        <div v-if="photos.length" class="photo-grid">
          <div v-for="photo in photos" :key="photo.id" class="photo-item">
            <div class="photo-thumb">
              <img :src="photo.preview_url" :alt="photo.title" />
            </div>
            <div class="photo-details">
              <span class="photo-title">{{ photo.title }}</span>
              <button class="btn-delete" @click="confirmDelete(photo)">Delete</button>
            </div>
          </div>
        </div>
        <div v-else-if="loadingPhotos" class="loading">Loading photos...</div>
        <div v-else class="empty">No photos uploaded yet.</div>
      </div>

      <!-- Users Tab -->
      <div v-if="activeTab === 'users'" class="tab-content">
        <div v-if="users.length" class="users-table">
          <div class="table-header">
            <span class="col-email">Email</span>
            <span class="col-role">Role</span>
            <span class="col-sub">Subscription</span>
            <span class="col-date">Joined</span>
          </div>
          <div v-for="u in users" :key="u.id" class="table-row">
            <span class="col-email">{{ u.email }}</span>
            <span class="col-role">
              <span v-if="u.is_admin" class="badge admin">Admin</span>
              <span v-else class="badge user">User</span>
            </span>
            <span class="col-sub">
              <span v-if="u.has_active_subscription" class="badge active">Active</span>
              <span v-else class="badge inactive">None</span>
            </span>
            <span class="col-date">{{ formatDate(u.created_at) }}</span>
          </div>
        </div>
        <div v-else-if="loadingUsers" class="loading">Loading users...</div>
        <div v-else class="empty">No users found.</div>
      </div>

      <!-- Delete Confirmation Modal -->
      <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
        <div class="modal">
          <h3>Delete Photo</h3>
          <p>Delete "{{ deleteTarget.title }}"? This cannot be undone.</p>
          <div class="modal-actions">
            <button class="btn-delete" :disabled="deleting" @click="doDelete">
              {{ deleting ? 'Deleting...' : 'Delete' }}
            </button>
            <button class="btn-cancel" @click="deleteTarget = null">Cancel</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import api from '../api.js'

const auth = useAuthStore()

const activeTab = ref('photos')
const stats = ref(null)
const photos = ref([])
const users = ref([])
const loadingPhotos = ref(true)
const loadingUsers = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

onMounted(async () => {
  if (!auth.isAdmin) return

  // Load stats and photos in parallel
  try {
    const [statsRes, photosRes] = await Promise.all([
      api.get('/admin/stats'),
      api.get('/photos/gallery'),
    ])
    stats.value = statsRes.data
    photos.value = photosRes.data
  } catch (e) {
    console.error('Failed to load admin data:', e)
  } finally {
    loadingPhotos.value = false
  }

  // Load users
  loadingUsers.value = true
  try {
    const { data } = await api.get('/admin/users')
    users.value = data
  } catch (e) {
    console.error('Failed to load users:', e)
  } finally {
    loadingUsers.value = false
  }
})

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function confirmDelete(photo) {
  deleteTarget.value = photo
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.delete(`/photos/admin/${deleteTarget.value.id}`)
    photos.value = photos.value.filter(p => p.id !== deleteTarget.value.id)
    if (stats.value) stats.value.total_photos--
    deleteTarget.value = null
  } catch (e) {
    console.error('Delete failed:', e)
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.admin-panel {
  max-width: 1000px;
  margin: 0 auto;
}

.access-denied {
  text-align: center;
  padding: 4rem;
  background: #1a1014;
  border: 1px solid #4a1525;
  border-radius: 8px;
  color: #ff3366;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
}

.admin-header h1 {
  font-size: 1.8rem;
}

.btn-action {
  background: #e74c3c;
  color: #fff !important;
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  transition: background 0.2s;
}
.btn-action:hover {
  background: #ff6b5a;
}

/* Stats */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: #151515;
  border: 1px solid #222;
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #e74c3c;
}

.stat-label {
  font-size: 0.85rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #333;
  margin-bottom: 1.5rem;
}

.tabs button {
  background: none;
  border: none;
  color: #888;
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tabs button:hover {
  color: #ccc;
}

.tabs button.active {
  color: #e74c3c;
  border-bottom-color: #e74c3c;
}

/* Photos Grid */
.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem;
}

.photo-item {
  background: #151515;
  border: 1px solid #222;
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.2s;
}
.photo-item:hover {
  border-color: #444;
}

.photo-thumb {
  aspect-ratio: 4/3;
  overflow: hidden;
}

.photo-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-details {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.8rem;
}

.photo-title {
  font-size: 0.85rem;
  color: #ccc;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60%;
}

.btn-delete {
  background: #c0392b;
  color: #fff;
  border: none;
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-delete:hover {
  background: #e74c3c;
}
.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Users Table */
.users-table {
  border: 1px solid #222;
  border-radius: 10px;
  overflow: hidden;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  padding: 0.75rem 1rem;
  align-items: center;
  gap: 0.5rem;
}

.table-header {
  background: #1a1a1a;
  font-size: 0.8rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.table-row {
  border-top: 1px solid #1f1f1f;
  font-size: 0.9rem;
}

.table-row:hover {
  background: #151515;
}

.col-email {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge.admin { color: #e74c3c; background: rgba(231,76,60,0.15); }
.badge.user { color: #888; background: rgba(136,136,136,0.1); }
.badge.active { color: #2ecc71; background: rgba(46,204,113,0.15); }
.badge.inactive { color: #666; background: rgba(102,102,102,0.1); }

/* Loading / Empty */
.loading, .empty {
  text-align: center;
  padding: 3rem;
  color: #555;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal {
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 12px;
  padding: 2rem;
  max-width: 400px;
  width: 90%;
}

.modal h3 {
  margin-bottom: 0.75rem;
}

.modal p {
  color: #aaa;
  margin-bottom: 1.5rem;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
}

.btn-cancel {
  background: #333;
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}
.btn-cancel:hover {
  background: #444;
}
</style>
