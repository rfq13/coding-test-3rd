'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'
import { fundApi } from '@/lib/api'
import { formatCurrency, formatPercentage, formatDate } from '@/lib/utils'
import { Loader2, TrendingUp, DollarSign, Calendar, Download } from 'lucide-react'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar } from 'recharts'

export default function FundDetailPage() {
  const params = useParams()
  const fundId = parseInt(params.id as string)
  const [exporting, setExporting] = useState(false)
  const [include, setInclude] = useState<'all' | 'transactions' | 'metrics'>('all')
  const [capitalPage, setCapitalPage] = useState(1)
  const [distPage, setDistPage] = useState(1)
  const limit = 10

  const { data: fund, isLoading: fundLoading } = useQuery({
    queryKey: ['fund', fundId],
    queryFn: () => fundApi.get(fundId)
  })

  const { data: capitalCalls } = useQuery({
    queryKey: ['transactions', fundId, 'capital_calls', capitalPage, limit],
    queryFn: () => fundApi.getTransactions(fundId, 'capital_calls', capitalPage, limit)
  })

  // Data untuk charts (ambil lebih banyak data untuk visualisasi)
  const { data: capitalCallsAll } = useQuery({
    queryKey: ['transactions', fundId, 'capital_calls', 'chart'],
    queryFn: () => fundApi.getTransactions(fundId, 'capital_calls', 1, 100)
  })

  const { data: distributions } = useQuery({
    queryKey: ['transactions', fundId, 'distributions', distPage, limit],
    queryFn: () => fundApi.getTransactions(fundId, 'distributions', distPage, limit)
  })

  const { data: distributionsAll } = useQuery({
    queryKey: ['transactions', fundId, 'distributions', 'chart'],
    queryFn: () => fundApi.getTransactions(fundId, 'distributions', 1, 100)
  })

  if (fundLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (!fund) {
    return <div>Fund not found</div>
  }

  const metrics = fund.metrics || {}

  const handleExport = async () => {
    try {
      setExporting(true)
      const blob = await fundApi.exportExcel(fundId, include)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `fund_${fundId}_export.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Failed to export Excel', e)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold mb-2">{fund.name}</h1>
            <div className="flex items-center space-x-4 text-gray-600">
              {fund.gp_name && <span>GP: {fund.gp_name}</span>}
              {fund.vintage_year && <span>Vintage: {fund.vintage_year}</span>}
              {fund.fund_type && <span>Type: {fund.fund_type}</span>}
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <label className="text-sm text-gray-600">Include</label>
              <select
                value={include}
                onChange={(e) => setInclude(e.target.value as 'all' | 'transactions' | 'metrics')}
                className="border rounded-md px-2 py-1 text-sm"
              >
                <option value="all">All</option>
                <option value="metrics">Metrics only</option>
                <option value="transactions">Transactions only</option>
              </select>
            </div>
            <button
              onClick={handleExport}
              disabled={exporting}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed shadow"
            >
              {exporting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Download className="w-4 h-4 mr-2" />
              )}
              Export Excel
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="DPI"
          value={metrics.dpi?.toFixed(2) + 'x' || 'N/A'}
          description="Distribution to Paid-In"
          icon={<TrendingUp className="w-6 h-6" />}
          color="blue"
        />
        <MetricCard
          title="IRR"
          value={metrics.irr ? formatPercentage(metrics.irr) : 'N/A'}
          description="Internal Rate of Return"
          icon={<TrendingUp className="w-6 h-6" />}
          color="green"
        />
        <MetricCard
          title="Paid-In Capital"
          value={metrics.pic ? formatCurrency(metrics.pic) : 'N/A'}
          description="Total capital called"
          icon={<DollarSign className="w-6 h-6" />}
          color="purple"
        />
        <MetricCard
          title="Distributions"
          value={metrics.total_distributions ? formatCurrency(metrics.total_distributions) : 'N/A'}
          description="Total distributions"
          icon={<DollarSign className="w-6 h-6" />}
          color="orange"
        />
      </div>

      {/* Transactions Tables */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Capital Calls */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Capital Calls</h2>
          {capitalCalls && capitalCalls.items.length > 0 ? (
            <div className="space-y-3">
              {capitalCalls.items.map((call: any) => (
                <TransactionRow
                  key={call.id}
                  date={call.call_date}
                  type={call.call_type}
                  amount={call.amount}
                  isNegative
                />
              ))}
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-gray-500">
                  Page {capitalCalls?.page ?? capitalPage} of {capitalCalls?.pages ?? 1}
                </p>
                <div className="space-x-2">
                  <button
                    onClick={() => setCapitalPage(p => Math.max(1, p - 1))}
                    disabled={(capitalCalls?.page ?? capitalPage) <= 1}
                    className="px-3 py-1 border rounded-md text-sm disabled:opacity-50"
                  >
                    Prev
                  </button>
                  <button
                    onClick={() => setCapitalPage(p => p + 1)}
                    disabled={!capitalCalls || capitalPage >= capitalCalls.pages}
                    className="px-3 py-1 border rounded-md text-sm disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No capital calls found</p>
          )}
        </div>

        {/* Distributions */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Distributions</h2>
          {distributions && distributions.items.length > 0 ? (
            <div className="space-y-3">
              {distributions.items.map((dist: any) => (
                <TransactionRow
                  key={dist.id}
                  date={dist.distribution_date}
                  type={dist.distribution_type}
                  amount={dist.amount}
                  isRecallable={dist.is_recallable}
                />
              ))}
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-gray-500">
                  Page {distributions?.page ?? distPage} of {distributions?.pages ?? 1}
                </p>
                <div className="space-x-2">
                  <button
                    onClick={() => setDistPage(p => Math.max(1, p - 1))}
                    disabled={(distributions?.page ?? distPage) <= 1}
                    className="px-3 py-1 border rounded-md text-sm disabled:opacity-50"
                  >
                    Prev
                  </button>
                  <button
                    onClick={() => setDistPage(p => p + 1)}
                    disabled={!distributions || distPage >= distributions.pages}
                    className="px-3 py-1 border rounded-md text-sm disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No distributions found</p>
          )}
        </div>
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-6 mt-8">
        {/* Capital Calls Chart */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Capital Calls Over Time</h2>
          {capitalCallsAll && capitalCallsAll.items.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={capitalCallsAll.items.map((c: any) => ({
                    date: c.call_date,
                    amount: Number(c.amount),
                  }))}
                  margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="colorCall" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.6}/>
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(val: any) => formatCurrency(Number(val))} labelFormatter={(label) => formatDate(label)} />
                  <Area type="monotone" dataKey="amount" stroke="#2563eb" fillOpacity={1} fill="url(#colorCall)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No capital calls data for chart</p>
          )}
        </div>

        {/* Distributions Chart */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Distributions Over Time</h2>
          {distributionsAll && distributionsAll.items.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={distributionsAll.items.map((d: any) => ({
                    date: d.distribution_date,
                    amount: Number(d.amount),
                  }))}
                  margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(val: any) => formatCurrency(Number(val))} labelFormatter={(label) => formatDate(label)} />
                  <Bar dataKey="amount" fill="#16a34a" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No distributions data for chart</p>
          )}
        </div>
      </div>
    </div>
  )
}

function MetricCard({ title, value, description, icon, color }: {
  title: string
  value: string
  description: string
  icon: React.ReactNode
  color: 'blue' | 'green' | 'purple' | 'orange'
}) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600',
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className={`w-12 h-12 rounded-lg ${colorClasses[color]} flex items-center justify-center mb-4`}>
        {icon}
      </div>
      <h3 className="text-sm font-medium text-gray-600 mb-1">{title}</h3>
      <p className="text-2xl font-bold text-gray-900 mb-1">{value}</p>
      <p className="text-xs text-gray-500">{description}</p>
    </div>
  )
}

function TransactionRow({ date, type, amount, isNegative, isRecallable }: {
  date: string
  type: string
  amount: number
  isNegative?: boolean
  isRecallable?: boolean
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-900">{type}</p>
        <div className="flex items-center space-x-2 mt-1">
          <Calendar className="w-3 h-3 text-gray-400" />
          <p className="text-xs text-gray-500">{formatDate(date)}</p>
          {isRecallable && (
            <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
              Recallable
            </span>
          )}
        </div>
      </div>
      <p className={`text-sm font-semibold ${isNegative ? 'text-red-600' : 'text-green-600'}`}>
        {isNegative ? '-' : '+'}{formatCurrency(Math.abs(amount))}
      </p>
    </div>
  )
}
