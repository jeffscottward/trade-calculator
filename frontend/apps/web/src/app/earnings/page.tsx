'use client'

import { useState, useCallback, useEffect, useMemo, Suspense } from 'react'
import { format, parseISO, isValid, addMonths, subWeeks } from 'date-fns'
import { useSearchParams, useRouter } from 'next/navigation'
import { EarningsCalendar } from '@/components/earnings-calendar'
import { EarningsTable, EarningsData } from '@/components/earnings-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { toast } from 'sonner'
import { useEarningsQuery, usePrefetchEarnings } from '@/hooks/useEarnings'
import { StockNewsFeed } from '@/components/stock-news-feed'

// Removed mock data - only using real data from API/database

function EarningsPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  
  // Dynamic date cutoff - 2 months forward from current date minus 1 week
  const DYNAMIC_CUTOFF = useMemo(() => {
    const currentDate = new Date()
    const twoMonthsForward = addMonths(currentDate, 2)
    return subWeeks(twoMonthsForward, 1)
  }, [])
  
  // Get date from URL parameter
  const dateParam = searchParams.get('date')
  
  // Redirect to current date if no date parameter is provided
  useEffect(() => {
    if (!dateParam) {
      const currentDate = new Date()
      const currentDateStr = format(currentDate, 'yyyy-MM-dd')
      router.replace(`/earnings?date=${currentDateStr}`)
    }
  }, [dateParam, router])
  
  const selectedDate = useMemo(() => {
    if (dateParam) {
      const parsedDate = parseISO(dateParam)
      if (isValid(parsedDate)) {
        return parsedDate
      }
    }
    // Fallback to current date while redirect is happening
    return new Date()
  }, [dateParam])
  
  const [earningsDates, setEarningsDates] = useState<Date[]>([])
  const prefetchEarnings = usePrefetchEarnings()
  
  // Preserve scroll position during hot reloads
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedPosition = sessionStorage.getItem('earnings-scroll-position')
      if (savedPosition) {
        window.scrollTo(0, parseInt(savedPosition))
        sessionStorage.removeItem('earnings-scroll-position')
      }
    }
  }, [])
  
  // Save scroll position during Fast Refresh rebuilds
  useEffect(() => {
    const saveScrollPosition = () => {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('earnings-scroll-position', window.scrollY.toString())
      }
    }
    
    // Save position every few seconds during development
    const interval = setInterval(saveScrollPosition, 2000)
    window.addEventListener('beforeunload', saveScrollPosition)
    
    return () => {
      clearInterval(interval)
      window.removeEventListener('beforeunload', saveScrollPosition)
    }
  }, [])
  
  // Use React Query for earnings data
  const { 
    data: earningsData = [], 
    isLoading: loading, 
    progress, 
    isStreaming 
  } = useEarningsQuery(selectedDate, {
    onProgress: (progress) => {
      // Progress updates handled by the hook internally
    }
  })
  
  // Calculate percentage for progress bar
  const analysisProgress = progress && progress.type === 'progress' && progress.current && progress.total
    ? {
        current: progress.current,
        total: progress.total,
        ticker: progress.ticker || '',
        percentage: Math.round((progress.current / progress.total) * 100)
      }
    : null

  // Get all dates that have earnings (for calendar highlighting)
  useEffect(() => {
    const fetchEarningsDates = async () => {
      const currentDate = new Date()
      const year = currentDate.getFullYear()
      const month = currentDate.getMonth() + 1 // JavaScript months are 0-indexed
      
      try {
        const response = await fetch(`http://localhost:8000/api/earnings/calendar/month?year=${year}&month=${month}`)
        if (response.ok) {
          const data = await response.json()
          const dates = data.earnings_dates.map((dateStr: string) => new Date(dateStr))
          setEarningsDates(dates)
        }
      } catch (error) {
        console.error('Failed to fetch earnings dates:', error)
      }
    }
    
    fetchEarningsDates()
  }, []) // Only run once on mount


  const handleDateSelect = useCallback((date: Date) => {
    // Check if date is beyond dynamic cutoff (2 months - 1 week) and show warning
    if (date > DYNAMIC_CUTOFF) {
      toast.warning("Data may not be available beyond 2 months from current date")
    }
    
    // Save current scroll position before updating
    const currentScrollY = window.scrollY
    
    // Update URL with new date
    const newDateStr = format(date, 'yyyy-MM-dd')
    router.replace(`/earnings?date=${newDateStr}`, { scroll: false })
    
    // Restore scroll position after a small delay to ensure DOM has updated
    setTimeout(() => {
      window.scrollTo(0, currentScrollY)
    }, 0)
  }, [DYNAMIC_CUTOFF, router])
  
  // Prefetch adjacent dates for smoother navigation
  const handleDateHover = useCallback((date: Date) => {
    // Prefetch the hovered date
    prefetchEarnings(date)
  }, [prefetchEarnings])



  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Earnings Calendar</h1>
        <p className="text-muted-foreground mt-2">
          Track upcoming earnings reports and analyze trading opportunities
        </p>
      </div>

      {/* Calendar Section */}
      <div className="flex flex-col lg:flex-row gap-6 mb-6">
        <div>
          <Card className="w-fit">
            <CardHeader>
              <CardTitle>Select Date</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4 p-3 bg-muted rounded-lg">
                <p className="text-sm font-medium">
                  Selected: {format(selectedDate, 'MMMM d, yyyy')}
                </p>
              </div>
              <EarningsCalendar 
                onDateSelect={handleDateSelect}
                earningsDates={earningsDates}
                maxDate={DYNAMIC_CUTOFF}
              />
            </CardContent>
          </Card>
        </div>

        {/* Recommended Trades Box */}
        <div className="flex-1 lg:flex-none">
          <Card className="w-full lg:w-[400px] h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-green-600">●</span>
                Recommended Trades
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  <div className="animate-pulse space-y-2">
                    <div className="h-4 bg-muted rounded w-3/4" />
                    <div className="h-4 bg-muted rounded w-1/2" />
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {(() => {
                    const recommendedTrades = earningsData
                      .filter(stock => stock.recommendation === 'RECOMMENDED')
                      .sort((a, b) => {
                        // Sort by market cap (larger = better for options liquidity)
                        const getMarketCapValue = (cap: string) => {
                          if (!cap) return 0
                          const num = parseFloat(cap.replace(/[$,BM]/g, ''))
                          if (cap.includes('B')) return num * 1000000000
                          if (cap.includes('M')) return num * 1000000
                          return num
                        }
                        return getMarketCapValue(b.marketCap || '') - getMarketCapValue(a.marketCap || '')
                      })
                    
                    if (recommendedTrades.length === 0) {
                      return (
                        <p className="text-muted-foreground text-center py-8">
                          No recommended trades for this date
                        </p>
                      )
                    }
                    
                    return (
                      <div style={{height: '370px'}} className="overflow-y-auto space-y-3 pr-2">
                        {recommendedTrades.map((stock, index) => (
                          <div key={stock.ticker} className="border-l-4 border-green-600 pl-4 py-2">
                            <div className="flex justify-between items-start">
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="bg-green-600 text-white text-xs font-bold px-2 py-1 rounded">
                                    #{index + 1}
                                  </span>
                                  <h4 className="font-semibold">{stock.ticker}</h4>
                                </div>
                                <p className="text-sm text-muted-foreground">{stock.companyName}</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                  {stock.reportTime} • {stock.marketCap}
                                </p>
                              </div>
                              <div className="text-right">
                                <p className="text-sm font-medium">Position Size</p>
                                <p className="text-lg font-bold text-green-600">
                                  {stock.position_size || '6%'}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                        {recommendedTrades.length > 3 && (
                          <p className="text-sm text-muted-foreground text-center pt-2 pb-1">
                            Total: {recommendedTrades.length} recommended trades
                          </p>
                        )}
                      </div>
                    )
                  })()}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Stock News Feed */}
        <div className="flex-1">
          <StockNewsFeed />
        </div>
      </div>

      {/* Table Section - Full Width */}
      <Card>
        <CardHeader>
          <CardTitle>
            Earnings Reports - {format(selectedDate, 'MMMM d, yyyy')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="relative">
              {/* Pulsing skeleton animation underneath */}
              <div className="space-y-3">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
              {/* Loading text overlay */}
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
                <div className="animate-pulse">
                  <div className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
                <p className="text-lg text-foreground mt-4">
                  {isStreaming ? 'Analyzing earnings data...' : 'Loading earnings data...'}
                </p>
                {analysisProgress ? (
                  <div className="mt-4 w-64 space-y-2">
                    <p className="text-sm text-muted-foreground text-center">
                      Analyzing {analysisProgress.ticker} ({analysisProgress.current}/{analysisProgress.total})
                    </p>
                    <Progress value={analysisProgress.percentage} className="h-2" />
                    <p className="text-xs text-muted-foreground text-center">
                      {analysisProgress.percentage}% complete
                    </p>
                  </div>
                ) : isStreaming ? (
                  <p className="text-sm text-muted-foreground">Starting analysis...</p>
                ) : (
                  <p className="text-sm text-muted-foreground">Fetching earnings data</p>
                )}
              </div>
            </div>
          ) : (
            <EarningsTable 
              data={earningsData}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// Wrap with Suspense to handle searchParams hydration
export default function EarningsPage() {
  return (
    <Suspense 
      fallback={
        <div className="container mx-auto p-6 max-w-7xl">
          <div className="animate-pulse">
            <div className="h-10 bg-muted rounded w-1/3 mb-4"></div>
            <div className="h-6 bg-muted rounded w-1/2"></div>
          </div>
        </div>
      }
    >
      <EarningsPageContent />
    </Suspense>
  )
}