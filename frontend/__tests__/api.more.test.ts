import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/msw-server'
import { fundApi, metricsApi } from '@/lib/api'

describe('API additional endpoints', () => {
  it('fundApi.get returns fund detail', async () => {
    server.use(
      http.get('/api/funds/1', (_req) => {
        return HttpResponse.json({ id: 1, name: 'Alpha Fund', vintage_year: 2020 })
      })
    )

    const fund = await fundApi.get(1)
    expect(fund.name).toBe('Alpha Fund')
    expect(fund.vintage_year).toBe(2020)
  })

  it('fundApi.getMetrics returns metrics for fund', async () => {
    server.use(
      http.get('/api/funds/1/metrics', (_req) => {
        return HttpResponse.json({ dpi: 0.8, irr: 15.2, tvpi: 1.5, rvpi: 0.7 })
      })
    )

    const metrics = await fundApi.getMetrics(1)
    expect(metrics.dpi).toBeCloseTo(0.8, 6)
    expect(metrics.irr).toBeCloseTo(15.2, 6)
  })

  it('metricsApi.getFundMetrics returns computed metrics', async () => {
    server.use(
      http.get('/api/metrics/funds/1/metrics', (req) => {
        const url = new URL(req.request.url)
        const metric = url.searchParams.get('metric')
        const payload = metric
          ? { [metric]: metric === 'irr' ? 12.34 : 1.23 }
          : { irr: 12.34, tvpi: 1.23 }
        return HttpResponse.json(payload)
      })
    )

    const all = await metricsApi.getFundMetrics(1)
    expect(all.irr).toBeCloseTo(12.34, 6)
    expect(all.tvpi).toBeCloseTo(1.23, 6)

    const onlyIrr = await metricsApi.getFundMetrics(1, 'irr')
    expect(onlyIrr.irr).toBeCloseTo(12.34, 6)
    expect(Object.keys(onlyIrr)).toEqual(['irr'])
  })
})