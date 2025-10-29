// utils/meta.ts
import { useHead } from "#app"

export function useMeta({
  title,
  description = "",
  image = "/",
}: {
  title: string
  description?: string
  image?: string
}) {
  useHead({
    title,
    titleTemplate: (t) => (t ? `${t} | Jekk` : "Jekk"),
    meta: [
      { name: "description", content: description },
      { name: "robots", content: "index, follow" },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:image", content: image },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  })
}
