'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { format } from 'date-fns'
import { EarningsCalendar } from '@/components/earnings-calendar'
import { EarningsTable, EarningsData } from '@/components/earnings-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { toast } from 'sonner'

// Removed mock data - only using real data from API/database

export default function EarningsPage() {
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [earningsData, setEarningsData] = useState<EarningsData[]>([])
  const [loading, setLoading] = useState(true)
  const [earningsDates, setEarningsDates] = useState<Date[]>([])
  const [isFetching, setIsFetching] = useState(false)
  const [analysisProgress, setAnalysisProgress] = useState<{
    current: number
    total: number
    ticker: string
    percentage: number
  } | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Setup WebSocket connection for progress tracking
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/progress')
    
    ws.onopen = () => {
      console.log('🚀 ~ file: page.tsx:34 → WebSocket connected')
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('🚀 ~ file: page.tsx:38 → WebSocket message:', data)
      
      if (data.type === 'analysis_progress') {
        setAnalysisProgress({
          current: data.current,
          total: data.total,
          ticker: data.ticker,
          percentage: data.percentage
        })
      } else if (data.type === 'analysis_complete') {
        setAnalysisProgress(null)
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    wsRef.current = ws
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

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
        console.error('🚀 ~ file: page.tsx:40 → fetchEarningsDates → error:', error)
      }
    }
    
    fetchEarningsDates()
  }, []) // Only run once on mount

  // Fetch earnings data for selected date
  useEffect(() => {
    // Prevent multiple simultaneous fetches
    if (isFetching) return
    
    const fetchEarningsData = async () => {
      setIsFetching(true)
      setLoading(true)
      
      try {
        const dateKey = format(selectedDate, 'yyyy-MM-dd')
        console.log('🚀 ~ file: page.tsx:48 → fetchEarningsData → Fetching data for date:', dateKey)
        
        // Try to fetch from API first with analysis data
        const url = `http://localhost:8000/api/earnings/${dateKey}?include_analysis=true`
        console.log('🚀 ~ file: page.tsx:52 → fetchEarningsData → API URL:', url)
        
        const response = await fetch(url)
        console.log('🚀 ~ file: page.tsx:55 → fetchEarningsData → Response status:', response.status)
        
        if (response.ok) {
          const data = await response.json()
          console.log('🚀 ~ file: page.tsx:59 → fetchEarningsData → Data received:', {
            date: data.date,
            source: data.source,
            count: data.earnings?.length || 0,
            hasData: !!data.earnings
          })
          
          if (data.earnings) {
            setEarningsData(data.earnings)
          } else {
            setEarningsData([])
          }
        } else {
          // API error - show empty state
          console.error('🚀 ~ file: page.tsx:73 → fetchEarningsData → API returned error status:', response.status)
          setEarningsData([])
          toast.error('Failed to fetch earnings data')
        }
      } catch (error) {
        console.error('🚀 ~ file: page.tsx:67 → fetchEarningsData → error:', error)
        setEarningsData([])
        toast.error('Failed to connect to earnings service')
      } finally {
        setLoading(false)
        setIsFetching(false)
      }
    }

    fetchEarningsData()
  }, [selectedDate])

  const handleDateSelect = useCallback((date: Date) => {
    setSelectedDate(date)
  }, [])



  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Earnings Calendar</h1>
        <p className="text-muted-foreground mt-2">
          Track upcoming earnings reports and analyze trading opportunities
        </p>
      </div>

      {/* Calendar Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Select Date</CardTitle>
            </CardHeader>
            <CardContent>
              <EarningsCalendar 
                onDateSelect={handleDateSelect}
                earningsDates={earningsDates}
              />
              <div className="mt-4 p-3 bg-muted rounded-lg">
                <p className="text-sm font-medium">
                  Selected: {format(selectedDate, 'MMMM d, yyyy')}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recommended Trades Box */}
        <div className="lg:col-span-2">
          <Card className="h-full">
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
                  {earningsData
                    .filter(stock => stock.recommendation === 'RECOMMENDED')
                    .slice(0, 5)
                    .map((stock) => (
                      <div key={stock.ticker} className="border-l-4 border-green-600 pl-4 py-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="font-semibold">{stock.ticker}</h4>
                            <p className="text-sm text-muted-foreground">{stock.companyName}</p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {stock.reportTime} • {stock.marketCap}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium">Position Size</p>
                            <p className="text-lg font-bold text-green-600">
                              {stock.position_size ? `${stock.position_size}%` : '6%'}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  {earningsData.filter(stock => stock.recommendation === 'RECOMMENDED').length === 0 && (
                    <p className="text-muted-foreground text-center py-8">
                      No recommended trades for this date
                    </p>
                  )}
                  {earningsData.filter(stock => stock.recommendation === 'RECOMMENDED').length > 5 && (
                    <p className="text-sm text-muted-foreground text-center pt-2">
                      +{earningsData.filter(stock => stock.recommendation === 'RECOMMENDED').length - 5} more trades available
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
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
                <p className="text-lg text-foreground mt-4">Loading earnings data...</p>
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
                ) : (
                  <p className="text-sm text-muted-foreground">Fetching and analyzing stocks</p>
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