<template>
  <div class="wall">
    <h1 class="serif">我的认领</h1>
    <input v-model="name" @change="load" placeholder="认领人名" />
    <p v-if="err" class="err">{{ err }}</p>
    <article v-for="w in rows || []" :key="w.id" class="card">
      <h3>{{ w.title }}</h3>
      <span class="tag">
        {{ w.status }}
        <template v-if="w.status==='claimed' && w.remaining_seconds!=null">
          · 剩余 {{ w.remaining_seconds }}s · 到期 {{ fmt(w.expires_at) }}
        </template>
        <template v-if="w.status==='fulfilled' && w.undo_remaining_seconds!=null">
          · 撤销窗剩余 {{ w.undo_remaining_seconds }}s · 截止 {{ fmt(w.undo_deadline) }}
        </template>
      </span>
    </article>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { usePoll } from '../usePoll'
import { fmtClock as fmt } from '../time'
const name = ref('访客')
const { rows, err, load } = usePoll(() => '/mine?claimer=' + encodeURIComponent(name.value))
</script>
