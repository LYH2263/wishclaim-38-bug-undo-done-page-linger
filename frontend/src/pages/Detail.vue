<template>
  <div class="wall">
    <h1 class="serif">{{ w.title }}</h1>
    <p>{{ w.note }}</p>
    <p class="tag">状态 {{ w.status }} · 认领人 {{ w.claimer || '—' }}</p>
    <p v-if="w.status==='claimed' && w.remaining_seconds!=null" class="tag">认领倒计时 {{ w.remaining_seconds }}s</p>
    <p v-if="w.status==='fulfilled'" class="tag">
      撤销窗剩余 {{ w.undo_remaining_seconds }}s<span v-if="w.proof"> · 举证 {{ w.proof }}</span>
    </p>
    <p v-if="err" class="err">{{ err }}</p>
    <input v-model="claimer" placeholder="你的名字" />
    <input v-model="proof" placeholder="举证（核销时记录，可选）" />
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button @click="claim">认领锁定</button>
      <button class="ghost" @click="release">释放</button>
      <button class="ghost" @click="fulfill">核销完成</button>
      <button v-if="w.can_undo" class="ghost" @click="undo">撤销核销</button>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const props = defineProps({ id: String })
const w = ref({})
const claimer = ref('访客')
const proof = ref('')
const err = ref('')
async function load() { w.value = await api('/wishes/' + props.id) }
async function claim() {
  err.value=''; try { await api('/wishes/'+props.id+'/claim',{method:'POST',body:JSON.stringify({claimer:claimer.value})}); await load() } catch(e){ err.value=e.message }
}
async function release() {
  err.value=''; try { await api('/wishes/'+props.id+'/release',{method:'POST',body:'{}'}); await load() } catch(e){ err.value=e.message }
}
async function fulfill() {
  err.value=''; try { await api('/wishes/'+props.id+'/fulfill',{method:'POST',body:JSON.stringify({proof:proof.value})}); await load() } catch(e){ err.value=e.message }
}
async function undo() {
  err.value=''; try { await api('/wishes/'+props.id+'/undo',{method:'POST',body:'{}'}); await load() } catch(e){ err.value=e.message }
}
onMounted(load)
</script>
