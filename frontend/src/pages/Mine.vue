<template>
  <div class="wall">
    <h1 class="serif">我的认领</h1>
    <input v-model="name" @change="load" placeholder="认领人名" />
    <article v-for="w in rows" :key="w.id" class="card">
      <h3>{{ w.title }}</h3>
      <span class="tag">{{ w.status }}<template v-if="w.remaining_seconds!=null"> · 剩余 {{ w.remaining_seconds }}s</template></span>
    </article>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const name = ref('访客')
const rows = ref([])
async function load() { rows.value = await api('/mine?claimer=' + encodeURIComponent(name.value)) }
onMounted(load)
</script>
