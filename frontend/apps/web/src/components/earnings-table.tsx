'use client'

import { useState, useMemo, useRef, useCallback } from 'react'
import Link from 'next/link'
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
  const [sorting, setSorting] = useState<SortingState>([
    {
      id: 'recommendation',
      desc: false, // false = ascending, which puts RECOMMENDED first
    }
  ])
  const [searchQuery, setSearchQuery] = useState('')
  const [columnFilters, setColumnFilters] = useState<any[]>([])
  
  
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
    if (!searchQuery) return normalizedData
    return fuse.search(searchQuery).map((result) => result.item)
  }, [searchQuery, fuse, normalizedData])

  const columns = useMemo(() => {
    return [
      columnHelper.accessor('ticker', {
        header: ({ column }) => (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-auto p-1 -m-1"
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
            className="h-auto p-1 -m-1 justify-start"
          >
            Company
            <ArrowUpDown className="ml-1 h-3 w-3" />
          </Button>
        ),
      }),
    columnHelper.accessor('reportTime', {
      header: 'Report Time',
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
    }),
    columnHelper.accessor('marketCap', {
      header: ({ column }) => (
        <div className="flex flex-col gap-1">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="h-auto p-1 -m-1"
          >
            Market Cap
            <ArrowUpDown className="ml-1 h-3 w-3" />
          </Button>
        </div>
      ),
      cell: (info) => {
        const value = info.getValue()
        return <span className="font-medium">{value || '-'}</span>
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
    }),
    columnHelper.accessor('recommendation', {
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto p-1 -m-1"
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
          <span className={`inline-block px-2 py-1 rounded text-xs font-bold ${
            displayRec === 'RECOMMENDED' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
            displayRec === 'CONSIDER' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
            displayRec === 'AVOID' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
            'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
          }`}>
            {displayRec}
          </span>
        )
      },
      sortingFn: (rowA, rowB) => {
        const order = { 'RECOMMENDED': 0, 'CONSIDER': 1, 'AVOID': 2 }
        const a = order[rowA.getValue('recommendation')] ?? 3
        const b = order[rowB.getValue('recommendation')] ?? 3
        return a - b
      },
    }),
    columnHelper.accessor('estimate', {
      header: 'EPS Estimate',
      cell: (info) => info.getValue() || '-',
    }),
    ]
  }, [columnHelper])

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
                {headerGroup.headers.map((header) => (
                  <th key={header.id} className="px-2 py-2 text-left" style={{ width: header.getSize() }}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="border-b hover:bg-muted/50">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-2 py-2">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
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