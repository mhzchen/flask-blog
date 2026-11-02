// 前端纵深防御：sanitizeHtml 净化逻辑单测
import { describe, it, expect } from "vitest"
import { sanitizeHtml } from "../src/utils/sanitize"

describe("sanitizeHtml", () => {
  it("空输入返回空串", () => {
    expect(sanitizeHtml("")).toBe("")
    expect(sanitizeHtml(null)).toBe("")
    expect(sanitizeHtml(undefined)).toBe("")
  })
  it("剥离 script / iframe / style 危险标签", () => {
    const out = sanitizeHtml("<p>你好</p><script>alert(1)</script><iframe src=x></iframe><style>body{}</style>")
    expect(out).not.toContain("script")
    expect(out).not.toContain("iframe")
    expect(out).not.toContain("style")
    expect(out).toContain("<p>你好</p>")
  })
  it("剥离 on* 事件属性", () => {
    const out = sanitizeHtml('<a href="/x" onclick="alert(1)">链接</a>')
    expect(out).not.toContain("onclick")
    expect(out).toContain("href=\"/x\"")
  })
  it("剥离 javascript: 伪协议链接", () => {
    const out = sanitizeHtml('<a href="javascript:alert(1)">x</a>')
    expect(out).not.toContain("javascript:")
  })
  it("保留正常内容与合法属性", () => {
    const out = sanitizeHtml("<h2>标题</h2><p><strong>加粗</strong></p>")
    expect(out).toContain("<h2>标题</h2>")
    expect(out).toContain("<strong>加粗</strong>")
  })
})
