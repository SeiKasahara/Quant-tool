export function formatDate(input: string | number | Date | undefined | null): string {
  if (!input) return ''
  try {
    const d = typeof input === 'string' || typeof input === 'number' ? new Date(input) : input
    return d.toLocaleString()
  } catch (e) {
    return String(input)
  }
}

export function formatPercentage(value: number | undefined | null, opts: { digits?: number } = {}): string {
  if (value === undefined || value === null || Number.isNaN(value)) return 'N/A'
  const digits = opts.digits ?? 0
  return `${(value * 100).toFixed(digits)}%`
}

export function getDirectionColor(direction?: string) {
  if (!direction) return 'text-gray-600'
  if (direction === 'up') return 'text-green-600'
  if (direction === 'down') return 'text-red-600'
  return 'text-gray-600'
}

export function getConfidenceColor(confidence?: number) {
  if (confidence === undefined || confidence === null || Number.isNaN(confidence)) return 'bg-gray-400'
  if (confidence >= 0.8) return 'bg-green-500'
  if (confidence >= 0.6) return 'bg-yellow-500'
  return 'bg-red-500'
}

export default { formatDate, formatPercentage, getDirectionColor, getConfidenceColor }
