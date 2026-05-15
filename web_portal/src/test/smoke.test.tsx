import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'

describe('vitest smoke', () => {
  it('renders a div', () => {
    const { container } = render(<div data-testid="smoke">hello</div>)
    expect(container.firstChild).toHaveTextContent('hello')
  })
})
