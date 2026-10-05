<template>
  <div class="wall">
    <template v-if="w && w.id">
      <h1 class="serif">{{ w.title }}</h1>
      <p>{{ w.note }}</p>
      <p class="tag">状态 {{ w.status }} · 认领人 {{ w.claimer || '—' }}</p>
      <p v-if="w.status==='claimed' && w.remaining_seconds!=null" class="tag">
        认领倒计时 {{ w.remaining_seconds }}s · 到期 {{ fmt(w.expires_at) }}
      </p>
      <p v-if="w.status==='fulfilled'" class="tag">
        撤销窗剩余 {{ w.undo_remaining_seconds }}s · 截止 {{ fmt(w.undo_deadline) }}
      </p>
      <!-- 举证区: 只在 fulfilled 且有举证时出现; 撤销成功后 proof 清空, 此区必须为空 -->
      <p v-if="w.status==='fulfilled' && w.proof" class="tag">举证 {{ w.proof }}</p>
      <p v-if="w.status==='fulfilled' && !w.proof" class="tag">举证区（空）</p>
      <p v-if="err" class="err">{{ err }}</p>
      <input v-model="claimer" placeholder="你的名字" />
      <input v-model="proof" placeholder="举证（核销时记录，可选）" />
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button @click="claim">认领锁定</button>
        <button class="ghost" @click="release">释放</button>
        <button class="ghost" @click="fulfill">核销完成</button>
        <button v-if="w.can_undo" class="ghost" @click="undo">撤销核销</button>
      </div>
    </template>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { usePoll } from '../usePoll'
import { api } from '../api'
import { fmtClock as fmt } from '../time'
const props = defineProps({ id: String })
const { rows: w, err, load } = usePoll(() => '/wishes/' + props.id)
const claimer = ref('访客')
const proof = ref('')
async function act(path, body) {
  try { await api(path, { method: 'POST', body: JSON.stringify(body) }); await load() }
  catch (e) {
    // 任何 4xx: 不碰本地状态, 下一跳秒仍以服务端投影为准。
    err.value = e.message
  }
}
const claim = () => act('/wishes/' + props.id + '/claim', { claimer: claimer.value })
const release = () => act('/wishes/' + props.id + '/release', {})
const fulfill = () => act('/wishes/' + props.id + '/fulfill', { proof: proof.value })
const undo = () => act('/wishes/' + props.id + '/undo', {})
</script>
