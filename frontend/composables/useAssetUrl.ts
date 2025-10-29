export const useAssetUrl = (path: string) => {
  const config = useRuntimeConfig()
  return `${config.public.API_BASE_URL}${path}`
}
