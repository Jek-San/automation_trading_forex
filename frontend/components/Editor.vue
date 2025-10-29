<template>
  <div class="space-y-2">
    <!-- Toolbar -->
    <div
      class="flex flex-wrap gap-2 border border-gray-700 p-2 rounded bg-[#1e1e1e]"
    >
      <button
        v-for="action in actions"
        :key="action.label"
        @click="action.command"
        :class="[
          'text-sm px-2 py-1 rounded',
          action.isActive()
            ? 'bg-cyan-600 text-white'
            : 'bg-gray-700 hover:bg-gray-600 text-gray-300',
        ]"
      >
        {{ action.label }}
      </button>
    </div>

    <!-- Editor -->
    <EditorContent
      :editor="editor"
      class="min-h-[200px] bg-[#0d1117] border border-gray-700 p-3 rounded text-white ProseMirror"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from "vue"
import { Editor, EditorContent } from "@tiptap/vue-3"

// Core + Extensions
import StarterKit from "@tiptap/starter-kit"
import Underline from "@tiptap/extension-underline"
import Link from "@tiptap/extension-link"
import BulletList from "@tiptap/extension-bullet-list"
import OrderedList from "@tiptap/extension-ordered-list"
import ListItem from "@tiptap/extension-list-item"
import Heading from "@tiptap/extension-heading"
import CodeBlock from "@tiptap/extension-code-block"

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void
}>()

const editor = ref<Editor>()

onMounted(() => {
  editor.value = new Editor({
    content: props.modelValue,
    extensions: [
      StarterKit.configure({
        heading: false,
        bulletList: false,
        orderedList: false,
        codeBlock: false,
      }),
      Heading.configure({ levels: [1, 2, 3] }),
      BulletList,
      OrderedList,
      ListItem,
      CodeBlock.configure({ HTMLAttributes: { class: "code-block" } }),
      Underline,
      Link.configure({ openOnClick: false }),
    ],
    editorProps: {
      attributes: {
        class: "focus:outline-none",
      },
    },
    onUpdate({ editor }) {
      emit("update:modelValue", editor.getHTML())
    },
  })
})

onBeforeUnmount(() => {
  editor.value?.destroy()
})

watch(
  () => props.modelValue,
  (val) => {
    if (editor.value && val !== editor.value.getHTML()) {
      editor.value.commands.setContent(val)
    }
  }
)

const actions = [
  {
    label: "Bold",
    command: () => editor.value?.chain().focus().toggleBold().run(),
    isActive: () => editor.value?.isActive("bold"),
  },
  {
    label: "Italic",
    command: () => editor.value?.chain().focus().toggleItalic().run(),
    isActive: () => editor.value?.isActive("italic"),
  },
  {
    label: "Underline",
    command: () => editor.value?.chain().focus().toggleUnderline().run(),
    isActive: () => editor.value?.isActive("underline"),
  },
  {
    label: "Strike",
    command: () => editor.value?.chain().focus().toggleStrike().run(),
    isActive: () => editor.value?.isActive("strike"),
  },
  {
    label: "H1",
    command: () =>
      editor.value?.chain().focus().toggleHeading({ level: 1 }).run(),
    isActive: () => editor.value?.isActive("heading", { level: 1 }),
  },
  {
    label: "H2",
    command: () =>
      editor.value?.chain().focus().toggleHeading({ level: 2 }).run(),
    isActive: () => editor.value?.isActive("heading", { level: 2 }),
  },
  {
    label: "Bullet List",
    command: () => editor.value?.chain().focus().toggleBulletList().run(),
    isActive: () => editor.value?.isActive("bulletList"),
  },
  {
    label: "Numbered List",
    command: () => editor.value?.chain().focus().toggleOrderedList().run(),
    isActive: () => editor.value?.isActive("orderedList"),
  },
  {
    label: "Code Block",
    command: () => editor.value?.chain().focus().toggleCodeBlock().run(),
    isActive: () => editor.value?.isActive("codeBlock"),
  },
]
</script>

<style>
/* Optional: for flicker stability and styling */
.ProseMirror {
  min-height: 200px;
  white-space: pre-wrap;
}
.code-block {
  background: #1e1e1e;
  padding: 0.5rem;
  font-family: monospace;
  border-radius: 4px;
}
</style>
