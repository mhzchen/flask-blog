// PostCard 组件测试：props 渲染
import { describe, it, expect } from "vitest"
import { mount } from "@vue/test-utils"
import PostCard from "../src/components/PostCard.vue"

function makePost(overrides = {}) {
  return { id: 1, title: "Flask 入门", summary: "简介", category: "Flask",
    created_at: "2026-10-29 10:00:00", tags: ["python", "web"], ...overrides }
}

const stubs = { "router-link": { template: "<a><slot/></a>" } }

describe("PostCard", () => {
  it("渲染标题摘要分类", () => {
    const w = mount(PostCard, { props: { post: makePost() }, global: { stubs } })
    expect(w.text()).toContain("Flask 入门")
    expect(w.text()).toContain("简介")
    expect(w.text()).toContain("Flask")
  })
  it("渲染标签列表", () => {
    const w = mount(PostCard, { props: { post: makePost() }, global: { stubs } })
    expect(w.text()).toContain("python")
    expect(w.text()).toContain("web")
  })
  it("无标签不渲染标签区", () => {
    const w = mount(PostCard, { props: { post: makePost({ tags: [] }) }, global: { stubs } })
    expect(w.find(".card-tags").exists()).toBe(false)
  })
})
