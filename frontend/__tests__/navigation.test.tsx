import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import Navigation from '@/components/Navigation'

// Mock next/navigation usePathname to control active route
vi.mock('next/navigation', () => ({
  usePathname: () => '/funds',
}))

describe('Navigation', () => {
  it('renders all nav links and marks active one', () => {
    render(<Navigation />)

    // Links exist
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Upload')).toBeInTheDocument()
    expect(screen.getByText('Chat')).toBeInTheDocument()
    expect(screen.getByText('Funds')).toBeInTheDocument()
    expect(screen.getByText('Compare')).toBeInTheDocument()
    expect(screen.getByText('Documents')).toBeInTheDocument()

    // Active state for /funds
    const fundsLink = screen.getByText('Funds').closest('a')
    expect(fundsLink).toHaveClass('bg-blue-50')
  })
})