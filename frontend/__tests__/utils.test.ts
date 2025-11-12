import { describe, it, expect } from 'vitest'
import { cn, formatCurrency, formatPercentage, formatDate, renderMath, formatLLMResponse } from '@/lib/utils'

describe('utils', () => {
  it('cn merges class names', () => {
    const result = cn('foo', 'bar')
    expect(result).toContain('foo')
    expect(result).toContain('bar')
  })

  it('formatCurrency formats USD without decimals', () => {
    expect(formatCurrency(1234)).toBe('$1,234')
    expect(formatCurrency(1000000)).toBe('$1,000,000')
  })

  it('formatPercentage formats to two decimals', () => {
    expect(formatPercentage(12.345)).toBe('12.35%')
    expect(formatPercentage(0)).toBe('0.00%')
  })

  it('formatDate formats YYYY-MM-DD', () => {
    expect(formatDate('2024-01-02')).toMatch(/Jan\s2,\s2024/)
  })

  it('renderMath converts $expr$ into KaTeX markup', () => {
    const html = renderMath('Compute $a+b$ now')
    expect(html).toContain('katex')
    expect(html).not.toContain('$a+b$')
  })

  it('formatLLMResponse converts markdown and cleans LaTeX escapes', () => {
    const raw = '**Bold**\n\n- foo\n- bar\n\nTable:\n| A | B |\n| 1 | 2 |\n\\(x+y\\)'
    const html = formatLLMResponse(raw)
    expect(html).toContain('<strong>Bold</strong>')
    expect(html).toContain('<ul')
    expect(html).toContain('<li') // at least one bullet item rendered
    expect(html).toContain('<table')
    expect(html).toContain('foo')
    expect(html).toContain('bar')
    expect(html).toContain('x+y') // LaTeX inline cleaned
  })
})