export const useFlash = () => {
  const flash = useState<string | null>("flash", () => null)

  const setFlash = (msg: string) => {
    flash.value = msg
    setTimeout(() => (flash.value = null), 3000) // auto-clear after 3s
  }

  return {
    flash,
    setFlash,
  }
}
