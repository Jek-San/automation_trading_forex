<!-- components/DeleteModal.vue -->
<template>
  <div
    v-if="show"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
  >
    <div class="bg-[#161b22] rounded-xl shadow-lg w-full max-w-md p-6">
      <h2 class="text-xl font-bold text-white mb-4">Confirm Deletion</h2>
      <p class="text-gray-300 mb-6">
        Are you sure you want to delete
        <strong class="text-red-400">{{ itemName }}</strong
        >? This action cannot be undone.
      </p>
      <div class="flex justify-end gap-3">
        <button
          class="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded"
          @click="$emit('cancel')"
        >
          Cancel
        </button>
        <button
          class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
          @click="$emit('confirm')"
        >
          Delete
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  show: Boolean,
  itemName: String,
})
defineEmits(["confirm", "cancel"])
</script>
