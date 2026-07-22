import { useSyncExternalStore } from "react"

const QUERY = "(prefers-color-scheme: dark)"

function subscribe(callback: () => void): () => void {
  const mediaQuery = window.matchMedia(QUERY)
  mediaQuery.addEventListener("change", callback)
  return () => mediaQuery.removeEventListener("change", callback)
}

function getSnapshot(): boolean {
  return window.matchMedia(QUERY).matches
}

/** Tracks the OS/browser `prefers-color-scheme`, updating live if the user
 * changes their system theme while the app is open.
 */
export function usePrefersDarkMode(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot)
}
