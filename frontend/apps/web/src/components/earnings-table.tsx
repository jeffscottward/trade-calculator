'use client'

import { useState, useMemo, useRef, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  getFilteredRowModel,
  SortingState,
} from '@tanstack/react-table'
import { Input } from './ui/input'
import { Button } from './ui/button'
import { ArrowUpDown } from 'lucide-react'
import Fuse from 'fuse.js'

export interface EarningsData {
  id: string
  ticker: string
  companyName: string
  company_name?: string // API returns snake_case
  reportTime?: 'BMO' | 'AMC' | 'DMH' | 'TBD'
  report_time?: 'BMO' | 'AMC' | 'DMH' | 'TBD' // API returns snake_case
  reportDate?: string
  report_date?: string // API returns snake_case
  marketCap?: string
  market_cap?: string // API returns snake_case
  market_cap_numeric?: number
  estimate?: string
  eps_forecast?: string // API returns snake_case
  fiscalQuarterEnding?: string
  fiscal_quarter_ending?: string // API returns snake_case
  marketCapRaw?: string | number // Raw value for sorting
  recommendation?: 'RECOMMENDED' | 'CONSIDER' | 'AVOID'
  riskLevel?: 'HIGH' | 'MODERATE' | 'LOW' | 'UNKNOWN'
}

interface EarningsTableProps {
  data: EarningsData[]
}



// Helper function to format market cap
function formatMarketCap(marketCap?: string | number): string {
  if (!marketCap) return '-'
  
  // If it's already a formatted string, parse it
  if (typeof marketCap === 'string') {
    // Remove currency symbols and commas
    const cleanStr = marketCap.replace(/[$,]/g, '')
    const num = parseFloat(cleanStr)
    if (!isNaN(num)) {
      marketCap = num
    } else {
      return marketCap // Return as-is if can't parse
    }
  }
  
  const num = marketCap as number
  
  // Format as billions/millions with 1 decimal place
  if (num >= 1e12) return `$${(num / 1e12).toFixed(1)}T`
  if (num >= 1e9) return `$${(num / 1e9).toFixed(1)}B`
  if (num >= 1e6) return `$${(num / 1e6).toFixed(1)}M`
  if (num >= 1e3) return `$${(num / 1e3).toFixed(0)}K`
  return `$${num.toFixed(0)}`
}

export function EarningsTable({ data }: EarningsTableProps) {
  const router = useRouter()
  const [sorting, setSorting] = useState<SortingState>([
    {
      id: 'recommendation',
      desc: false, // false = ascending, which puts RECOMMENDED first
    },
    {
      id: 'priority_score',
      desc: true, // Secondary sort by priority score (high to low)
    }
  ])
  const [searchQuery, setSearchQuery] = useState('')
  const [columnFilters, setColumnFilters] = useState<any[]>([])
  const [epsSort, setEpsSort] = useState<'desc' | 'asc' | null>(null)
  
  
  const columnHelper = createColumnHelper<EarningsData>()

  // Normalize data from snake_case to camelCase
  const normalizedData = useMemo(() => {
    return data.map(item => {
      const reportDate = item.reportDate || item.report_date
      const marketCapValue = item.market_cap_numeric || item.marketCap || item.market_cap
      
      return {
        ...item,
        companyName: item.companyName || item.company_name || '',
        reportTime: item.reportTime || item.report_time || 'TBD',
        reportDate: reportDate,
        marketCap: formatMarketCap(marketCapValue),
        marketCapRaw: marketCapValue, // Keep raw value for sorting
        estimate: item.estimate || item.eps_forecast,
        fiscalQuarterEnding: item.fiscalQuarterEnding || item.fiscal_quarter_ending,
      }
    })
  }, [data])


  const fuse = useMemo(
    () =>
      new Fuse(normalizedData, {
        keys: ['ticker', 'companyName'],
        threshold: 0.3,
      }),
    [normalizedData]
  )

  const filteredData = useMemo(() => {
    let result = normalizedData
    
    // Apply search filter
    if (searchQuery) {
      result = fuse.search(searchQuery).map((result) => result.item)
    }
    
    // Filter out nulls when EPS sorting is active
    if (epsSort !== null) {
      result = result.filter(item => {
        const estimate = item.estimate || item.eps_forecast
        return estimate && estimate !== '-'
      })
    }
    
    return result
  }, [searchQuery, fuse, normalizedData, epsSort])

  const columns = useMemo(() => {
    return [
      columnHelper.accessor('ticker', {
        header: ({ column }) => (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-auto !px-0 py-0 font-medium text-sm justify-start w-full"
            style={{ padding: '0' }}
          >
            Ticker
            <ArrowUpDown className="ml-1 h-3 w-3" />
          </Button>
        ),
      cell: (info) => (
        <Link 
          href={`/earnings/${info.getValue()}`} 
          className="font-mono font-bold hover:underline text-primary"
        >
          {info.getValue()}
        </Link>
      ),
      size: 80,
      minSize: 60,
      maxSize: 100,
    }),
      columnHelper.accessor('companyName', {
        header: ({ column }) => (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-auto !px-0 py-0 font-medium text-sm justify-start text-left w-full"
            style={{ padding: '0' }}
          >
            Company
            <ArrowUpDown className="ml-1 h-3 w-3" />
          </Button>
        ),
        size: 350,
        minSize: 300,
        maxSize: 400,
      }),
    columnHelper.accessor('reportTime', {
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto !px-0 py-0 font-medium text-sm justify-start text-left w-full"
          style={{ padding: '0' }}
        >
          Report Time
          <ArrowUpDown className="ml-1 h-3 w-3" />
        </Button>
      ),
      cell: (info) => {
        const time = info.getValue() as string
        const timeMap: Record<string, string> = {
          BMO: 'Before Open',
          AMC: 'After Close',
          DMH: 'During Hours',
          TBD: 'TBD',
        }
        const displayTime = timeMap[time] || time || 'TBD'
        return (
          <span className={`inline-block whitespace-nowrap px-2 py-1 rounded text-xs font-medium ${
            time === 'BMO' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
            time === 'AMC' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' :
            time === 'TBD' || !time ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
            'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
          }`}>
            {displayTime}
          </span>
        )
      },
      sortingFn: (rowA, rowB) => {
        const order = { 'BMO': 0, 'AMC': 1, 'DMH': 2, 'TBD': 3 }
        const a = order[rowA.getValue('reportTime')] ?? 4
        const b = order[rowB.getValue('reportTime')] ?? 4
        return a - b
      },
      size: 120,
      minSize: 100,
      maxSize: 140,
    }),
    columnHelper.accessor('marketCap', {
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto !px-0 py-0 font-medium text-sm justify-end text-right w-full"
          style={{ padding: '0' }}
        >
          Market Cap
          <ArrowUpDown className="ml-1 h-3 w-3" />
        </Button>
      ),
      cell: (info) => {
        const value = info.getValue() as string
        if (!value || value === '-') {
          return <div className="text-right text-muted-foreground">-</div>
        }
        
        // Determine the suffix and apply color coding
        const isTrillions = value.includes('T')
        const isBillions = value.includes('B')
        const isMillions = value.includes('M')
        const isThousands = value.includes('K')
        
        return (
          <div className="text-right font-medium">
            <span 
              className={
                isBillions ? 'text-lime-500 dark:text-lime-400 font-semibold' :
                isMillions ? 'text-green-600 dark:text-green-500' :
                isThousands ? 'text-gray-500 dark:text-gray-400 text-sm' :
                ''
              }
              style={isTrillions ? { color: '#00ff00', fontWeight: 'bold' } : undefined}
            >
              {value}
            </span>
          </div>
        )
      },
      sortingFn: (rowA, rowB) => {
        const a = rowA.original.marketCapRaw
        const b = rowB.original.marketCapRaw
        if (!a && !b) return 0
        if (!a) return 1
        if (!b) return -1
        const numA = typeof a === 'string' ? parseFloat(a.replace(/[$,]/g, '')) : a
        const numB = typeof b === 'string' ? parseFloat(b.replace(/[$,]/g, '')) : b
        return numA - numB
      },
      size: 110,
      minSize: 90,
      maxSize: 130,
    }),
    columnHelper.accessor('recommendation', {
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto !px-0 py-0 font-medium text-sm justify-start text-left w-full"
          style={{ padding: '0' }}
        >
          Recommendation
          <ArrowUpDown className="ml-1 h-3 w-3" />
        </Button>
      ),
      cell: (info) => {
        const rec = info.getValue()
        if (!rec) return <span className="text-muted-foreground">-</span>
        
        // Handle any legacy "WAIT" values as "AVOID"
        const displayRec = rec === 'WAIT' ? 'AVOID' : rec
        
        return (
          <div className="flex justify-start">
            <span className={`inline-block px-2 py-1 rounded text-xs font-bold ${
            displayRec === 'RECOMMENDED' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
            displayRec === 'CONSIDER' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
            displayRec === 'AVOID' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
            'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
          }`}>
            {displayRec}
          </span>
          </div>
        )
      },
      sortingFn: (rowA, rowB) => {
        const order = { 'RECOMMENDED': 0, 'CONSIDER': 1, 'AVOID': 2 }
        const a = order[rowA.getValue('recommendation')] ?? 3
        const b = order[rowB.getValue('recommendation')] ?? 3
        return a - b
      },
      size: 140,
      minSize: 120,
      maxSize: 160,
    }),
    columnHelper.accessor('priority_score', {
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto !px-0 py-0 font-medium text-sm justify-start text-left w-full"
          style={{ padding: '0' }}
        >
          Priority
          <ArrowUpDown className="ml-1 h-3 w-3" />
        </Button>
      ),
      cell: (info) => {
        const score = info.getValue()
        const recommendation = info.row.original.recommendation
        
        // Only show scores for trades with recommendations
        if (!score || score === 0 || recommendation === 'AVOID') {
          return <span className="text-muted-foreground">-</span>
        }
        
        return (
          <span className="font-medium">
            {score.toFixed(1)}
          </span>
        )
      },
      sortingFn: (rowA, rowB) => {
        const a = rowA.getValue('priority_score') || 0
        const b = rowB.getValue('priority_score') || 0
        return a - b
      },
      size: 80,
      minSize: 60,
      maxSize: 100,
    }),
    columnHelper.accessor('estimate', {
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => {
            // Three-state cycle: desc → asc → null → desc
            if (epsSort === null) {
              setEpsSort('desc')
              setSorting([{ id: 'estimate', desc: true }])
            } else if (epsSort === 'desc') {
              setEpsSort('asc')
              setSorting([{ id: 'estimate', desc: false }])
            } else {
              setEpsSort(null)
              setSorting(prev => prev.filter(s => s.id !== 'estimate'))
            }
          }}
          className="h-auto !px-0 py-0 font-medium text-sm justify-end text-right w-full"
          style={{ padding: '0' }}
        >
          EPS Est.
          <ArrowUpDown className="ml-1 h-3 w-3" />
        </Button>
      ),
      size: 80,
      minSize: 70,
      maxSize: 100,
      cell: (info) => {
        const value = info.getValue() as string | undefined
        if (!value || value === '-') return <div className="text-right text-muted-foreground">-</div>
        
        // Check if it's a negative value (has parentheses)
        const isNegative = value.includes('(')
        
        // Remove parentheses and dollar sign, extract the number
        let cleanValue = value.replace(/[()$]/g, '').trim()
        
        // Format with + or - sign
        const formattedValue = isNegative ? `-$${cleanValue}` : `+$${cleanValue}`
        
        return (
          <div className="text-right">
            <span className={isNegative ? 'text-red-600 dark:text-red-400 font-medium' : 'text-green-600 dark:text-green-400 font-medium'}>
              {formattedValue}
            </span>
          </div>
        )
      },
      sortingFn: (rowA, rowB, columnId) => {
        const a = rowA.getValue('estimate') as string | undefined
        const b = rowB.getValue('estimate') as string | undefined
        
        // Since nulls are filtered out when sorting is active,
        // we can simplify this to just parse and compare
        if (!a && !b) return 0
        if (!a) return 1
        if (!b) return -1
        
        const aIsNegative = a.includes('(')
        const aNum = parseFloat(a.replace(/[()$]/g, '')) * (aIsNegative ? -1 : 1)
        
        const bIsNegative = b.includes('(')
        const bNum = parseFloat(b.replace(/[()$]/g, '')) * (bIsNegative ? -1 : 1)
        
        return aNum - bNum
      },
    }),
    ]
  }, [columnHelper, epsSort])

  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
      columnFilters,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    sortDescFirst: false,
    enableSortingRemoval: true,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Input
          placeholder="Search stocks..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-sm"
        />
        <div className="text-sm text-muted-foreground">
          {filteredData.length} stocks reporting
        </div>
      </div>

      <div className="rounded-md border">
        <table className="w-full">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b">
                {headerGroup.headers.map((header) => {
                  const colId = header.column.id
                  const alignment = 
                    colId === 'marketCap' || colId === 'estimate' ? 'text-right' :
                    'text-left'
                  return (
                    <th key={header.id} className={`px-3 py-2 ${alignment}`}
                        style={{ width: header.column.getSize() }}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <tr 
                  key={row.id} 
                  className="border-b hover:bg-muted/50 cursor-pointer"
                  onClick={() => {
                    const ticker = row.original.ticker
                    router.push(`/earnings/${ticker}`)
                  }}
                >
                  {row.getVisibleCells().map((cell) => {
                    const colId = cell.column.id
                    const alignment = 
                      colId === 'marketCap' || colId === 'estimate' ? '' :
                      ''
                    return (
                      <td key={cell.id} className={`px-3 py-2 ${alignment}`}
                          style={{ width: cell.column.getSize() }}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    )
                  })}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="h-24 text-center">
                  No earnings reports for this date.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}