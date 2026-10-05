import { ref, onMounted, onUnmounted } from 'vue'
import { api } from './api'

// 所有页面的倒计时只吃服务端投影 (remaining_seconds / undo_remaining_seconds),
// 每秒重拉一次, 前端不自行重开满额, mine / 墙卡 / 详情天然同一个钉。
export function usePoll(source, interval = 1000) {
  const rows = ref(null)
  const err = ref('')
  let timer
  const pathOf = () => (typeof source === 'function' ? source() : source)
  async function load() {
    try {
      const data = await api(pathOf())
      rows.value = data
      err.value = ''
    } catch (e) {
      err.value = e.message
    }
  }
  onMounted(() => {
    load()
    timer = setInterval(load, interval)
  })
  onUnmounted(() => clearInterval(timer))
  return { rows, err, load }
}
