<template>
  <div>
    <h2 class="section-title">{{ t('admin.title') }}</h2>

    <div class="admin-tabs" role="tablist">
      <button :class="{ active: tab === 'posts' }" @click="tab = 'posts'" role="tab" :aria-selected="tab === 'posts'">{{ t('admin.posts') }}</button>
      <button :class="{ active: tab === 'categories' }" @click="tab = 'categories'" role="tab" :aria-selected="tab === 'categories'">{{ t('admin.cats') }}</button>
    </div>

    <!-- ===== 文章管理 ===== -->
    <div v-if="tab === 'posts'">
      <button class="btn-add" @click="openNewPost">{{ t('admin.newPost') }}</button>

      <table class="admin-table">
        <thead>
          <tr><th>{{ t('admin.id') }}</th><th>{{ t('admin.title') }}</th><th>{{ t('admin.category') }}</th><th>{{ t('admin.published') }}</th><th>{{ t('admin.ops') }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="post in posts" :key="post.id">
            <td>{{ post.id }}</td>
            <td>{{ post.title }}</td>
            <td>{{ post.category }}</td>
            <td>{{ post.created_at }}</td>
            <td>
              <button class="btn-sm" @click="openEditPost(post)">{{ t('admin.editPost') }}</button>
              <button class="btn-sm danger" @click="deletePost(post)">{{ t('admin.delete') }}</button>
            </td>
          </tr>
          <tr v-if="!posts.length"><td colspan="5" class="empty-tip">{{ t('admin.none') }}</td></tr>
        </tbody>
      </table>

      <!-- 文章编辑弹窗 -->
      <div v-if="postModal.show" class="modal-mask">
        <div class="modal" role="dialog" aria-modal="true">
          <h3>{{ postModal.editId ? t('admin.editPost') : t('admin.newArticle') }}</h3>
          <div class="form-group">
            <label for="ap-title">{{ t('admin.title') }}</label>
            <input id="ap-title" v-model="postForm.title" class="form-input" required />
          </div>
          <div class="form-group">
            <label for="ap-cat">{{ t('admin.category') }}</label>
            <select id="ap-cat" v-model="postForm.category_id" class="form-input">
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label for="ap-tags">{{ t('admin.tags') }}</label>
            <input id="ap-tags" v-model="postForm.tags" class="form-input" placeholder="Flask, Web" />
          </div>
          <div class="form-group">
            <label for="ap-summary">{{ t('admin.summary') }}</label>
            <input id="ap-summary" v-model="postForm.summary" class="form-input" />
          </div>
          <div class="form-group">
            <label for="ap-content">{{ t('admin.content') }}</label>
            <textarea id="ap-content" v-model="postForm.content" class="form-input" rows="6"></textarea>
          </div>
          <p v-if="postModal.error" class="error-tip" role="alert">{{ postModal.error }}</p>
          <div class="modal-actions">
            <button class="btn-sm" @click="postModal.show = false">{{ t('admin.cancel') }}</button>
            <button class="btn-sm primary" @click="savePost" :disabled="postModal.saving">
              {{ postModal.saving ? t('admin.saving') : t('admin.save') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 分类管理 ===== -->
    <div v-if="tab === 'categories'">
      <button class="btn-add" @click="openNewCategory">{{ t('admin.newCat') }}</button>

      <table class="admin-table">
        <thead>
          <tr><th>{{ t('admin.id') }}</th><th>{{ t('admin.name') }}</th><th>slug</th><th>{{ t('admin.ops') }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="cat in categories" :key="cat.id">
            <td>{{ cat.id }}</td>
            <td>{{ cat.name }}</td>
            <td>{{ cat.slug }}</td>
            <td>
              <button class="btn-sm" @click="openEditCategory(cat)">{{ t('admin.editCat') }}</button>
              <button class="btn-sm danger" @click="deleteCategory(cat)">{{ t('admin.delete') }}</button>
            </td>
          </tr>
          <tr v-if="!categories.length"><td colspan="4" class="empty-tip">{{ t('admin.noCats') }}</td></tr>
        </tbody>
      </table>

      <div v-if="catModal.show" class="modal-mask">
        <div class="modal" role="dialog" aria-modal="true">
          <h3>{{ catModal.editId ? t('admin.editCat') : t('admin.newCateg') }}</h3>
          <div class="form-group">
            <label for="ac-name">{{ t('admin.name') }}</label>
            <input id="ac-name" v-model="catForm.name" class="form-input" required />
          </div>
          <div class="form-group">
            <label for="ac-slug">{{ t('admin.slug') }}</label>
            <input id="ac-slug" v-model="catForm.slug" class="form-input" />
          </div>
          <p v-if="catModal.error" class="error-tip" role="alert">{{ catModal.error }}</p>
          <div class="modal-actions">
            <button class="btn-sm" @click="catModal.show = false">{{ t('admin.cancel') }}</button>
            <button class="btn-sm primary" @click="saveCategory" :disabled="catModal.saving">
              {{ catModal.saving ? t('admin.saving') : t('admin.save') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'

const { t } = useI18n()
const tab = ref('posts')
const posts = ref([])
const categories = ref([])

// ---- 文章 ----
const postModal = ref({ show: false, editId: null, saving: false, error: '' })
const postForm = ref({ title: '', summary: '', content: '', category_id: null, tags: '' })

// ---- 分类 ----
const catModal = ref({ show: false, editId: null, saving: false, error: '' })
const catForm = ref({ name: '', slug: '' })

async function fetchPosts() {
  const { data } = await api.get('/admin/posts')
  posts.value = data.items
}

async function fetchCategories() {
  const { data } = await api.get('/categories')
  categories.value = data.items
}

function openNewPost() {
  postForm.value = { title: '', summary: '', content: '', category_id: categories.value[0]?.id || null, tags: '' }
  postModal.value = { show: true, editId: null, saving: false, error: '' }
}

function openEditPost(post) {
  postForm.value = { title: post.title, summary: post.summary, content: post.content, category_id: post.category_id, tags: (post.tags || []).join(', ') }
  postModal.value = { show: true, editId: post.id, saving: false, error: '' }
}

async function savePost() {
  postModal.value.saving = true
  postModal.value.error = ''
  try {
    const payload = { ...postForm.value, tags: postForm.value.tags.split(',').map(s => s.trim()).filter(Boolean) }
    if (postModal.value.editId) {
      await api.put(`/admin/posts/${postModal.value.editId}`, payload)
    } else {
      await api.post('/admin/posts', payload)
    }
    postModal.value.show = false
    await fetchPosts()
  } catch (e) {
    postModal.value.error = e.response?.data?.error || t('admin.saveFailed')
  } finally {
    postModal.value.saving = false
  }
}

async function deletePost(post) {
  if (!confirm(t('admin.confirmDeletePost', { title: post.title }))) return
  await api.delete(`/admin/posts/${post.id}`)
  await fetchPosts()
}

function openNewCategory() {
  catForm.value = { name: '', slug: '' }
  catModal.value = { show: true, editId: null, saving: false, error: '' }
}

function openEditCategory(cat) {
  catForm.value = { name: cat.name, slug: cat.slug }
  catModal.value = { show: true, editId: cat.id, saving: false, error: '' }
}

async function saveCategory() {
  catModal.value.saving = true
  catModal.value.error = ''
  try {
    if (catModal.value.editId) {
      await api.put(`/admin/categories/${catModal.value.editId}`, catForm.value)
    } else {
      await api.post('/admin/categories', catForm.value)
    }
    catModal.value.show = false
    await fetchCategories()
  } catch (e) {
    catModal.value.error = e.response?.data?.error || t('admin.saveFailed')
  } finally {
    catModal.value.saving = false
  }
}

async function deleteCategory(cat) {
  if (!confirm(t('admin.confirmDeleteCat', { name: cat.name }))) return
  await api.delete(`/admin/categories/${cat.id}`)
  await fetchCategories()
  await fetchPosts()
}

onMounted(async () => {
  await fetchCategories()
  await fetchPosts()
})
</script>

<style scoped>
.admin-tabs { margin-bottom: 20px; }
.admin-tabs button {
  padding: 8px 20px; margin-right: 8px; border: 1px solid var(--border-strong); border-radius: 6px;
  background: var(--card-bg); cursor: pointer; color: var(--fg);
}
.admin-tabs button.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.btn-add { padding: 8px 16px; background: var(--heading); color: #fff; border: none; border-radius: 6px; cursor: pointer; margin-bottom: 14px; }
.admin-table { width: 100%; border-collapse: collapse; background: var(--card-bg); border-radius: 8px; overflow: hidden; }
.admin-table th, .admin-table td { padding: 10px 14px; border-bottom: 1px solid var(--border); text-align: left; }
.admin-table th { background: var(--thead-bg); font-size: 14px; }
.btn-sm { padding: 4px 12px; margin-right: 6px; border: 1px solid var(--border-strong); border-radius: 4px; background: var(--card-bg); cursor: pointer; color: var(--fg); }
.btn-sm.primary { background: var(--heading); color: #fff; border-color: var(--heading); }
.btn-sm.danger { color: var(--accent); border-color: var(--accent); }
.modal-mask { position: fixed; inset: 0; background: var(--mask); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { width: 520px; max-width: 90vw; background: var(--card-bg); border-radius: 10px; padding: 24px; color: var(--fg); }
.modal h3 { margin-bottom: 16px; }
.modal textarea { resize: vertical; }
.modal-actions { margin-top: 16px; text-align: right; }
</style>
