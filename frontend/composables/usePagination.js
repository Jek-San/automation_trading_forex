// composables/usePagination.js
import { ref, computed, watch } from "vue"

export function usePagination(items, itemsPerPage = 10) {
  const currentPage = ref(1)

  const totalPages = computed(() => {
    const len = items.value?.length || 0
    return len === 0 ? 1 : Math.ceil(len / itemsPerPage)
  })

  const paginatedData = computed(() => {
    if (!items.value?.length) return []
    const start = (currentPage.value - 1) * itemsPerPage
    return items.value.slice(start, start + itemsPerPage)
  })

  function nextPage() {
    if (currentPage.value < totalPages.value) currentPage.value++
  }

  function prevPage() {
    if (currentPage.value > 1) currentPage.value--
  }

  function goToPage(page) {
    if (page >= 1 && page <= totalPages.value) currentPage.value = page
  }

  // Reset to page 1 when items change
  watch(items, () => {
    currentPage.value = 1
  })

  return {
    currentPage,
    totalPages,
    paginatedData,
    nextPage,
    prevPage,
    goToPage,
  }
}