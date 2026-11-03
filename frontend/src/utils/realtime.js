// WebSocket 实时推送客户端（socket.io-client）
// 后端评论/新文章发布时会广播 'comment:new' / 'post:new'；
// 本模块建立连接并把事件回调给调用方（App.vue 用它显示顶部实时通知条）。
import { io } from 'socket.io-client'

let socket = null

export function connectSocket(onEvent) {
  if (socket) return socket
  socket = io('/', {
    path: '/socket.io',
    transports: ['websocket', 'polling'],
    reconnectionAttempts: 3, // 后端未以 ASGI/ws 启动时避免无限重连（静默失败）
  })
  socket.on('comment:new', (data) => onEvent?.('comment', data))
  socket.on('post:new', (data) => onEvent?.('post', data))
  return socket
}

export function disconnectSocket() {
  if (socket) { socket.disconnect(); socket = null }
}