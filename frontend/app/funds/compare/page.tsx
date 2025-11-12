'use client'
import React from 'react'
import { useEffect } from 'react'

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fundApi } from '@/lib/api'
import { formatCurrency, formatPercentage } from '@/lib/utils'
import { Loader2, CheckSquare, Square, BarChart3, RotateCcw } from 'lucide-react'
import { evaluateFormula, allowedVariables } from '@/lib/formula'

type FundWithMetrics = {
  id: number
  name: string
  gp_name?: string
  fund_type?: string
  vintage_year?: number
  metrics?: {
    dpi?: number
    irr?: number
    tvpi?: number | null
    rvpi?: number | null
    pic?: number
    total_distributions?: number
    nav?: number | null
  }
}

export default function CompareFundsPage() {
  const { data: funds, isLoading, error, refetch } = useQuery({
    queryKey: ['funds'],
    queryFn: () => fundApi.list(),
    retry: false,
  })

  const [selected, setSelected] = useState<number[]>([])
  const [formula, setFormula] = useState<string>('dpi + rvpi')
  const [formulaError, setFormulaError] = useState<string | null>(null)

  const onToggle = (id: number) => {
    setSelected((prev) => (
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    ))
  }

  const selectedFunds: FundWithMetrics[] = useMemo(() => {
    if (!funds) return []
    const list = funds as FundWithMetrics[]
    return list.filter((f) => selected.includes(f.id))
  }, [funds, selected])

  const computeCustom = (f: FundWithMetrics) => {
    const vars: Record<string, number> = {
      dpi: typeof f.metrics?.dpi === 'number' ? f.metrics!.dpi : 0,
      irr: typeof f.metrics?.irr === 'number' ? f.metrics!.irr : 0,
      tvpi: typeof f.metrics?.tvpi === 'number' ? (f.metrics!.tvpi as number) : 0,
      rvpi: typeof f.metrics?.rvpi === 'number' ? (f.metrics!.rvpi as number) : 0,
      pic: typeof f.metrics?.pic === 'number' ? f.metrics!.pic : 0,
      total_distributions: typeof f.metrics?.total_distributions === 'number' ? f.metrics!.total_distributions as number : 0,
      nav: typeof f.metrics?.nav === 'number' ? (f.metrics!.nav as number) : 0,
    }
    try {
      return evaluateFormula(formula, vars)
    } catch {
      return NaN
    }
  }

  // Validate formula on change
  useEffect(() => {
    const testVars: Record<string, number> = Object.fromEntries(allowedVariables.map((v) => [v, 1]))
    try {
      evaluateFormula(formula, testVars)
      setFormulaError(null)
    } catch (e: any) {
      setFormulaError(e?.message || 'Invalid formula')
    }
  }, [formula])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 mb-3">Error loading funds: {(error as Error).message}</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition"
          >
            <RotateCcw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold mb-2">Compare Funds</h1>
          <p className="text-gray-600">Select multiple funds to compare key metrics side by side.</p>
        </div>
      </div>

      {/* Custom Formula */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Custom Calculation</h2>
        <div className="mb-2 text-sm text-gray-600">
          Use variables: {allowedVariables.join(', ')}. Example: <code className="bg-gray-100 px-1 rounded">(dpi + rvpi) * pic</code>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={formula}
            onChange={(e) => setFormula(e.target.value)}
            placeholder="Enter formula"
            className="flex-1 border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
          >
            Refresh Data
          </button>
        </div>
        {formulaError && (
          <div className="mt-2 text-sm text-red-600">{formulaError}</div>
        )}
      </div>

      {/* Empty state when no funds */}
      {Array.isArray(funds as any) && (funds as FundWithMetrics[]).length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center mb-6">
          <BarChart3 className="w-10 h-10 mx-auto text-gray-400 mb-3" />
          <h2 className="text-lg font-semibold mb-2">No funds found</h2>
          <p className="text-sm text-gray-600 mb-4">There are no funds to compare yet. Try refreshing.</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
          >
            <RotateCcw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      ) : (
        <>
      {/* Selector */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Select Funds</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.isArray(funds as any) && (funds as FundWithMetrics[]).map((f) => {
            const isSelected = selected.includes(f.id)
            const Icon = isSelected ? CheckSquare : Square
            return (
              <button
                key={f.id}
                onClick={() => onToggle(f.id)}
                className={`flex items-center justify-between w-full border rounded-md px-3 py-2 text-left transition ${
                  isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-gray-500" />
                  <div>
                    <div className="font-medium">{f.name}</div>
                    <div className="text-xs text-gray-500">{f.fund_type || '—'} · {(f.vintage_year != null ? f.vintage_year : '—')}</div>
                  </div>
                </div>
                <Icon className={isSelected ? 'w-4 h-4 text-blue-600' : 'w-4 h-4 text-gray-400'} />
              </button>
            )
          })}
        </div>
      </div>

      {/* Comparison Table */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="min-w-full">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Metric</th>
              {selectedFunds.map((f) => (
                <th key={f.id} className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                  {f.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* Custom Formula Result */}
            <tr className="border-t">
              <td className="px-4 py-3 text-sm text-gray-600">Custom</td>
              {selectedFunds.map((f) => (
                <td key={f.id} className="px-4 py-3 text-sm">
                  {(() => {
                    if (formulaError) return '—'
                    const val = computeCustom(f)
                    return Number.isFinite(val) ? val.toFixed(2) : '—'
                  })()}
                </td>
              ))}
            </tr>
            {/* DPI */}
            <tr className="border-t">
              <td className="px-4 py-3 text-sm text-gray-600">DPI</td>
              {selectedFunds.map((f) => {
                const dpi = f.metrics && typeof f.metrics.dpi === 'number' ? f.metrics.dpi : 0
                return (
                  <td key={f.id} className="px-4 py-3 text-sm">
                    {formatPercentage(dpi / 1)}
                  </td>
                )
              })}
            </tr>
            {/* IRR */}
            <tr className="border-t">
              <td className="px-4 py-3 text-sm text-gray-600">IRR</td>
              {selectedFunds.map((f) => {
                const irr = f.metrics && typeof f.metrics.irr === 'number' ? f.metrics.irr : null
                return (
                  <td key={f.id} className="px-4 py-3 text-sm">
                    {irr != null ? formatPercentage(irr / 100) : '—'}
                  </td>
                )
              })}
            </tr>
            {/* PIC */}
            <tr className="border-t">
              <td className="px-4 py-3 text-sm text-gray-600">Paid-In Capital (PIC)</td>
              {selectedFunds.map((f) => {
                const pic = f.metrics && typeof f.metrics.pic === 'number' ? f.metrics.pic : 0
                return (
                  <td key={f.id} className="px-4 py-3 text-sm">
                    {formatCurrency(pic)}
                  </td>
                )
              })}
            </tr>
            {/* Total Distributions */}
            <tr className="border-t">
              <td className="px-4 py-3 text-sm text-gray-600">Total Distributions</td>
              {selectedFunds.map((f) => {
                const dist = f.metrics && typeof f.metrics.total_distributions === 'number' ? f.metrics.total_distributions : 0
                return (
                  <td key={f.id} className="px-4 py-3 text-sm">
                    {formatCurrency(dist)}
                  </td>
                )
              })}
            </tr>
            {/* NAV (if available) */}
            <tr className="border-t">
              <td className="px-4 py-3 text-sm text-gray-600">NAV</td>
              {selectedFunds.map((f) => {
                const nav = f.metrics && typeof f.metrics.nav === 'number' ? f.metrics.nav : null
                return (
                  <td key={f.id} className="px-4 py-3 text-sm">
                    {nav != null ? formatCurrency(nav) : '—'}
                  </td>
                )
              })}
            </tr>
          </tbody>
        </table>
        {selectedFunds.length === 0 && (
          <div className="p-6 text-sm text-gray-500">Select one or more funds to view comparison.</div>
        )}
      </div>
        </>
      )}
    </div>
  )
}