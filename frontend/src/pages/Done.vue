<template>
  <div class="wall">
    <h1 class="serif">已完成</h1>
    <p v-if="err" class="err">{{ err }}</p>
    <p v-if="rows && rows.length===0" class="tag">暂无已核销愿望</p>
    <article v-for="w in rows || []" :key="w.id" class="card">
      <h3>{{ w.title }}</h3><p>{{ w.claimer }}</p>
      <span class="tag">撤销窗剩余 {{ w.undo_remaining_seconds }}s · 截止 {{ fmt(w.undo_deadline) }}</span>
      <button v-if="w.can_undo" class="ghost" @click="onUndo(w.id)">撤销</button>
    </article>
  </div>
</template>
<script setup>
import { usePoll } from '../usePoll'
import { api } from '../api'
import { fmtClock as fmt } from '../time'
const { rows, err, load } = usePoll('/done')
async function onUndo(id) {
  try { await api('/wishes/' + id + '/undo', { method: 'POST', body: '{}' }); await load() }
  catch (e) {
    // 窗外失败: 不做任何本地改动, 下一跳秒服务端投影自然纠正, 行/倒计时/举证全停在失败前。
    err.value = e.message
  }
}
</script>
