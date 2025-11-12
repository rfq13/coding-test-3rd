type Vars = Record<string, number>

const OPERATORS = new Set(['+', '-', '*', '/', '(', ')'])
const PRECEDENCE: Record<string, number> = { '+': 1, '-': 1, '*': 2, '/': 2 }

function isOperator(tok: string) {
  return OPERATORS.has(tok)
}

function tokenize(expr: string): string[] {
  const tokens: string[] = []
  let i = 0
  while (i < expr.length) {
    const ch = expr[i]
    if (ch === ' ' || ch === '\t' || ch === '\n') { i++; continue }
    if (isOperator(ch)) { tokens.push(ch); i++; continue }
    if (/[0-9.]/.test(ch)) {
      let num = ch; i++
      while (i < expr.length && /[0-9.]/.test(expr[i])) { num += expr[i]; i++ }
      tokens.push(num)
      continue
    }
    if (/[a-zA-Z_]/.test(ch)) {
      let id = ch; i++
      while (i < expr.length && /[a-zA-Z0-9_]/.test(expr[i])) { id += expr[i]; i++ }
      tokens.push(id)
      continue
    }
    throw new Error(`Invalid character '${ch}'`)
  }
  return tokens
}

function toRPN(tokens: string[]): string[] {
  const output: string[] = []
  const stack: string[] = []
  for (const t of tokens) {
    if (isOperator(t)) {
      if (t === '(') { stack.push(t); continue }
      if (t === ')') {
        while (stack.length && stack[stack.length - 1] !== '(') {
          output.push(stack.pop() as string)
        }
        if (!stack.length) throw new Error('Mismatched parentheses')
        stack.pop(); continue
      }
      while (stack.length && isOperator(stack[stack.length - 1]) && stack[stack.length - 1] !== '(' && (PRECEDENCE[stack[stack.length - 1]] >= PRECEDENCE[t])) {
        output.push(stack.pop() as string)
      }
      stack.push(t)
    } else {
      output.push(t)
    }
  }
  while (stack.length) {
    const op = stack.pop() as string
    if (op === '(' || op === ')') throw new Error('Mismatched parentheses')
    output.push(op)
  }
  return output
}

function applyOp(op: string, a: number, b: number): number {
  switch (op) {
    case '+': return a + b
    case '-': return a - b
    case '*': return a * b
    case '/': return b === 0 ? NaN : a / b
    default: throw new Error(`Unknown operator ${op}`)
  }
}

export function evaluateFormula(expr: string, vars: Vars): number {
  const tokens = toRPN(tokenize(expr))
  const stack: number[] = []
  for (const t of tokens) {
    if (isOperator(t)) {
      const b = stack.pop()
      const a = stack.pop()
      if (a == null || b == null) throw new Error('Invalid expression')
      stack.push(applyOp(t, a, b))
    } else {
      const num = Number(t)
      if (!Number.isNaN(num)) {
        stack.push(num)
      } else {
        if (!(t in vars)) throw new Error(`Unknown variable '${t}'`)
        stack.push(vars[t])
      }
    }
  }
  if (stack.length !== 1) throw new Error('Invalid expression')
  return stack[0]
}

export const allowedVariables = [
  'dpi', 'irr', 'tvpi', 'rvpi', 'pic', 'total_distributions', 'nav'
]