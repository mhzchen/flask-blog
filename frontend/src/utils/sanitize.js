// 前端纵深防御：渲染 HTML 前的二次净化。
// 后端（bleach）已做第一道净化，这里防止历史脏数据或其他入口。
export function sanitizeHtml(input) {
  if (!input) return ''
  if (typeof DOMParser === 'undefined') return input
  const doc = new DOMParser().parseFromString(input, 'text/html')
  doc.querySelectorAll('script, iframe, object, embed, link, style, form, input').forEach((el) => el.remove())
  doc.querySelectorAll('*').forEach((el) => {
    Array.from(el.attributes).forEach((attr) => {
      const name = attr.name.toLowerCase()
      const val = attr.value.trim().toLowerCase()
      if (name.startsWith('on') || val.startsWith('javascript:')) el.removeAttribute(attr.name)
    })
  })
  return doc.body.innerHTML
}