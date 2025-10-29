import { ref } from "vue"

export const useSlugCheck = () => {
  const available = ref<boolean | null>(null)
  const isChecking = ref(false)

  const check = async (slug: string, withAuth = false) => {
    if (!slug) return

    const config = useRuntimeConfig()
    const token = useCookie("token")

    const headers: Record<string, string> = {}
    if (withAuth && token.value) {
      headers.Authorization = `Bearer ${token.value}`
    }

    const url = `${config.public.API_BASE_URL}/api/projects/check-slug/${slug}`

    isChecking.value = true
    try {
      const res = await $fetch<{ available: boolean }>(url, { headers })
      available.value = res.available
    } catch (e) {
      console.error("❌ Slug check failed:", e)
      available.value = null
    } finally {
      isChecking.value = false
    }
  }

  return {
    available,
    isChecking,
    check,
  }
}
