<!-- components/PaginationControls.vue -->
<template>
  <div class="flex justify-between items-center mt-4 text-slate-300 text-sm">
    <div>Page {{ currentPage }} of {{ totalPages }}</div>

    <div class="flex gap-2">
      <button
        @click="$emit('prev')"
        :disabled="currentPage === 1"
        class="px-3 py-1 rounded-lg bg-slate-700/40 hover:bg-slate-700/70 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Prev
      </button>
      <button
        @click="$emit('next')"
        :disabled="currentPage === totalPages"
        class="px-3 py-1 rounded-lg bg-slate-700/40 hover:bg-slate-700/70 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Next
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  currentPage: Number,
  totalPages: Number,
})
</script>
