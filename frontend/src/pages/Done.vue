<template>
  <div class="wall">
    <h1 class="serif">已完成</h1>
    <p v-if="err" class="err">{{ err }}</p>
    <article v-for="w in rows" :key="w.id" class="card">
      <h3>{{ w.title }}</h3><p>{{ w.claimer }}</p>
      <span class="tag">撤销窗剩余 {{ w.undo_remaining_seconds }}s</span>
      <button v-if="w.can_undo" class="ghost" @click="undo(w.id)">撤销</button>
    </article>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
const err = ref('')
async function load() { rows.value = await api('/done') }
async function undo(id) {
  err.value=''; try { await api('/wishes/'+id+'/undo',{method:'POST',body:'{}'}); await load() } catch(e){ err.value=e.message }
}
onMounted(load)
</script>
