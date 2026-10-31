import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { ScenarioRequest } from './types'

// Prices change once a day, so analysis results stay fresh for a long time
const FIVE_MINUTES = 5 * 60 * 1000

export function usePortfolios() {
  return useQuery({ queryKey: ['portfolios'], queryFn: api.listPortfolios })
}

export function usePortfolio(id: string) {
  return useQuery({
    queryKey: ['portfolio', id],
    queryFn: () => api.getPortfolio(id),
    staleTime: FIVE_MINUTES,
  })
}

export function useRisk(id: string, confidence: number, horizon: number, lookback: number | null) {
  return useQuery({
    queryKey: ['risk', id, confidence, horizon, lookback],
    queryFn: () => api.getRisk(id, { confidence, horizon, lookback }),
    staleTime: FIVE_MINUTES,
  })
}

export function useBacktest(id: string, window: number) {
  return useQuery({
    queryKey: ['backtest', id, window],
    queryFn: () => api.getBacktest(id, window),
    staleTime: FIVE_MINUTES,
  })
}

export function useScenarioEvents() {
  return useQuery({
    queryKey: ['scenario-events'],
    queryFn: api.listScenarioEvents,
    staleTime: Infinity,
  })
}

export function useUploadPortfolio() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { file: File; name: string; benchmark: string }) =>
      api.uploadPortfolio(input.file, input.name, input.benchmark),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['portfolios'] }),
  })
}

export function useDeletePortfolio() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.deletePortfolio,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['portfolios'] }),
  })
}

export function useScenario(id: string) {
  return useMutation({ mutationFn: (body: ScenarioRequest) => api.runScenario(id, body) })
}
