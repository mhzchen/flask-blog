<template>
  <div>
    <h2 class="section-title">后台管理</h2>

    <div class="admin-tabs">
      <button :class="{ active: tab === 'posts' }" @click="tab = 'posts'">文章管理</button>
      <button :class="{ active: tab === 'categories' }" @click="tab = 'categories'">分类管理</button>
    </div>

    <!-- ===== 文章管理 ===== -->
    <div v-if="tab === 'posts'">
      <button class="btn-add" @click="openNewPost">＋ 新建文章</button>

      <table class="admin-table">
        <thead>
          <tr><th>ID</th><th>标题</th><th>分类</th><th>发布时间</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="post in posts" :key="post.id">
            <td>{{ post.id }}</td>
            <td>{{ post.title }}</td>
            <td>{{ post.category }}</td>
            <td>{{ post.created_at }}</td>
            <td>
              <button class="btn-sm" @click="openEditPost(post)">编辑</button>
              <button class="btn-sm danger" @click="deletePost(post)">删除</button>
            </td>
          </tr>
          <tr v-if="!posts.length"><td colspan="5" class="empty-tip">暂无文章</td></tr>
        </tbody>
      </table>

      <!-- 文章编辑弹窗 -->
      <div v-if="postModal.show" class="modal-mask">
        <div class="modal">
          <h3>{{ postModal.editId ? '编辑文章' : '新建文章' }}</h3>
          <div class="form-group">
            <label>标题</label>
            <input v-model="postForm.title" class="form-input" required />
          </div>
          <div class="form-group">
            <label>分类</label>
            <select v-model="postForm.category_id" class="form-input">
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>摘要</label>
            <input v-model="postForm.summary" class="form-input" />
          </div>
          <div class="form-group">
            <label>正文（支持 HTML）</label>
            <textarea v-model="postForm.content" class="form-input" rows="6"></textarea>
          </div>
          <p v-if="postModal.error" class="error-tip">{{ postModal.error }}</p>
          <div class="modal-actions">
            <button class="btn-sm" @click="postModal.show = false">取消</button>
            <button class="btn-sm primary" @click="savePost" :disabled="postModal.saving">
              {{ postModal.saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 分类管理 ===== -->
    <div v-if="tab === 'categories'">
      <button class="btn-add" @click="openNewCategory">＋ 新建分类</button>

      <table class="admin-table">
        <thead>
          <tr><th>ID</th><th>名称</th><th>slug</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="cat in categories" :key="cat.id">
            <td>{{ cat.id }}</td>
            <td>{{ cat.name }}</td>
            <td>{{ cat.slug }}</td>
            <td>
              <button class="btn-sm" @click="openEditCategory(cat)">编辑</button>
              <button class="btn-sm danger" @click="deleteCategory(cat)">删除</button>
            </td>
          </tr>
          <tr v-if="!categories.length"><td colspan="4" class="empty-tip">暂无分类</td></tr>
        </tbody>
      </table>

      <div v-if="catModal.show" class="modal-mask">
        <div class="modal">
          <h3>{{ catModal.editId ? '编辑分类' : '新建分类' }}</h3>
          <div class="form-group">
            <label>名称</label>
            <input v-model="catForm.name" class="form-input" required />
          </div>
          <div class="form-group">
            <label>slug（可选，留空自动生成）</label>
            <input v-model="catForm.slug" class="form-input" />
          </div>
          <p v-if="catModal.error" class="error-tip">{{ catModal.error }}</p>
          <div class="modal-actions">
            <button class="btn-sm" @click="catModal.show = false">取消</button>
            <button class="btn-sm primary" @click="saveCategory" :disabled="catModal.saving">
              {{ catModal.saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const tab = ref('posts')
const posts = ref([])
const categories = ref([])

// ---- 文章 ----
const postModal = ref({ show: false, editId: null, saving: false, error: '' })
const postForm = ref({ title: '', summary: '', content: '', category_id: null })

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
  postForm.value = { title: '', summary: '', content: '', category_id: categories.value[0]?.id || null }
  postModal.value = { show: true, editId: null, saving: false, error: '' }
}

function openEditPost(post) {
  postForm.value = { title: post.title, summary: post.summary, content: post.content, category_id: post.category_id }
  postModal.value = { show: true, editId: post.id, saving: false, error: '' }
}

async function savePost() {
  postModal.value.saving = true
  postModal.value.error = ''
  try {
    if (postModal.value.editId) {
      await api.put(`/admin/posts/${postModal.value.editId}`, postForm.value)
    } else {
      await api.post('/admin/posts', postForm.value)
    }
    postModal.value.show = false
    await fetchPosts()
  } catch (e) {
    postModal.value.error = e.response?.data?.error || '保存失败'
  } finally {
    postModal.value.saving = false
  }
}

async function deletePost(post) {
  if (!confirm(`确定删除文章「${post.title}」？`)) return
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
    catModal.value.error = e.response?.data?.error || '保存失败'
  } finally {
    catModal.value.saving = false
  }
}

async function deleteCategory(cat) {
  if (!confirm(`确定删除分类「${cat.name}」？`)) return
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
  padding: 8px 20px; margin-right: 8px; border: 1px solid #ddd; border-radius: 6px;
  background: #fff; cursor: pointer;
}
.admin-tabs button.active { background: #e74c3c; color: #fff; border-color: #e74c3c; }
.btn-add { padding: 8px 16px; background: #2c3e50; color: #fff; border: none; border-radius: 6px; cursor: pointer; margin-bottom: 14px; }
.admin-table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; }
.admin-table th, .admin-table td { padding: 10px 14px; border-bottom: 1px solid #eee; text-align: left; }
.admin-table th { background: #f8f9fa; font-size: 14px; }
.btn-sm { padding: 4px 12px; margin-right: 6px; border: 1px solid #ddd; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-sm.primary { background: #2c3e50; color: #fff; border-color: #2c3e50; }
.btn-sm.danger { color: #e74c3c; border-color: #e74c3c; }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { width: 520px; max-width: 90vw; background: #fff; border-radius: 10px; padding: 24px; }
.modal h3 { margin-bottom: 16px; }
.modal textarea { resize: vertical; }
.modal-actions { margin-top: 16px; text-align: right; }
</style>