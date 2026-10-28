<template>
  <router-link :to="`/post/${post.id}`" class="card-link">
    <div class="article-card">
      <span class="card-category">{{ post.category }}</span>
      <h3>{{ post.title }}</h3>
      <p>{{ post.summary }}</p>
      <span class="card-date">{{ post.created_at }}</span>
    </div>
  </router-link>
</template>

<script setup>
defineProps({ post: { type: Object, required: true } })
</script>