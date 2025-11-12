import { describe, it, expect } from 'vitest'
import { evaluateFormula } from '@/lib/formula'

describe('evaluateFormula', () => {
  const vars = {
    dpi: 0.8,
    irr: 15,
    tvpi: 1.5,
    rvpi: 0.7,
    pic: 100,
    total_distributions: 80,
    nav: 70,
  }

  it('computes basic arithmetic', () => {
    expect(evaluateFormula('1 + 2 * 3', vars)).toBe(7)
    expect(evaluateFormula('(1 + 2) * 3', vars)).toBe(9)
  })

  it('uses variables', () => {
    expect(evaluateFormula('dpi + rvpi', vars)).toBeCloseTo(1.5, 6)
    expect(evaluateFormula('tvpi * pic', vars)).toBeCloseTo(150, 6)
  })

  it('handles division by zero safely', () => {
    const res = evaluateFormula('1 / (pic - 100)', vars)
    expect(Number.isNaN(res)).toBe(true)
  })

  it('throws on unknown variables', () => {
    expect(() => evaluateFormula('unknown + 1', vars)).toThrow()
  })

  it('throws on invalid expression', () => {
    expect(() => evaluateFormula('1 + * 2', vars)).toThrow()
    expect(() => evaluateFormula('(1 + 2', vars)).toThrow()
  })
})