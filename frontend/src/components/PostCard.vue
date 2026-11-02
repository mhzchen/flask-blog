<template>
  <router-link :to="`/post/${post.id}`" class="card-link">
    <div class="article-card">
      <span class="card-category">{{ post.category }}</span>
      <h3>{{ post.title }}</h3>
      <p>{{ post.summary }}</p>
      <div v-if="post.tags && post.tags.length" class="card-tags">
        <span v-for="t in post.tags" :key="t" class="card-tag">{{ t }}</span>
      </div>
      <span class="card-date">{{ post.created_at }}</span>
    </div>
  </router-link>
</template>

<script setup>
defineProps({ post: { type: Object, required: true } })
</script>

<style scoped>
.card-tags { margin: 6px 0; }
.card-tag {
  display: inline-block; background: #eef3ff; color: #3a6ea5;
  font-size: 12px; padding: 2px 8px; border-radius: 10px; margin-right: 6px;
}
</style>
