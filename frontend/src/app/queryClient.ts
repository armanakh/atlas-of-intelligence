import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 45_000, retry: (count, error: unknown) => count < 1 && !(error instanceof Error && 'status' in error && (error as { status: number }).status < 500) },
  },
})
