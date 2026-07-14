import { useCallback, useEffect, useRef, useState } from 'react'

const DEFAULT_INTERVAL_MS = 45_000

export function useAdminPoll<T>(
  fetcher: () => Promise<T>,
  intervalMs = DEFAULT_INTERVAL_MS,
): { data: T | null; loading: boolean; error: string | null; refresh: () => void } {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const refresh = useCallback(async () => {
    try {
      setError(null)
      const result = await fetcherRef.current()
      setData(result)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
    const id = window.setInterval(() => { void refresh() }, intervalMs)
    return () => window.clearInterval(id)
  }, [refresh, intervalMs])

  return { data, loading, error, refresh }
}
