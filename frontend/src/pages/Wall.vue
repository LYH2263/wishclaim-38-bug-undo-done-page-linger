<template>
  <div class="wall">
    <h1 class="serif">愿望墙</h1>
    <p class="tag">无顶栏 · 瀑布流 · 点卡片认领</p>
    <div class="masonry">
      <article v-for="w in rows || []" :key="w.id" class="card" @click="$router.push('/wishes/'+w.id)">
        <h3>{{ w.title || '（无标题）' }}</h3>
        <p>{{ w.note }}</p>
        <span class="tag">
          {{ w.status }} · {{ w.data_quality }}
          <template v-if="w.status==='claimed' && w.remaining_seconds!=null">
            · 剩余 {{ w.remaining_seconds }}s · 到期 {{ fmt(w.expires_at) }}
          </template>
        </span>
      </article>
    </div>
  </div>
</template>
<script setup>
import { usePoll } from '../usePoll'
import { fmtClock as fmt } from '../time'
const { rows } = usePoll('/wishes')
</script>
