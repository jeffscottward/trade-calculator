'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, TrendingUp, DollarSign } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'

interface StockDetails {
  ticker: string
  companyName: string
  reportDate: string
  reportTime: string
  marketCap: string
  estimate: string
  fiscalQuarterEnding: string
  lastYearEPS?: string
  numEstimates?: number
}

interface TradeAnalysis {
  ticker: string
  data?: {
    current_iv: string
    historical_iv: string
    iv_rank: number
    suggested_strategy: string
    expected_move: string
    trade_details?: {
      entry: string
      exit: string
      max_profit: string
      max_loss: string
      probability_of_profit: string
    }
  }
  error?: string
}

export default function StockDetailPage() {
  const params = useParams()
  const router = useRouter()
  const ticker = params.ticker as string
  
  const [stockDetails, setStockDetails] = useState<StockDetails | null>(null)
  const [analysis, setAnalysis] = useState<TradeAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  
  // Update page title with ticker
  useEffect(() => {
    document.title = `${ticker} - EVOL Optimus`
  }, [ticker])

  // Fetch all data in a single call
  useEffect(() => {
    const fetchAllData = async () => {
      try {
        // Fetch everything in a single API call
        const response = await fetch(`http://localhost:8000/api/stock/${ticker}/complete`)
        
        if (response.ok) {
          const data = await response.json()
          
          // Set stock details if available
          if (data.details) {
            setStockDetails({
              ticker: data.details.ticker,
              companyName: data.details.companyName || data.details.company_name,
              reportDate: data.details.reportDate || data.details.report_date,
              reportTime: data.details.reportTime || data.details.report_time || 'TBD',
              marketCap: data.details.marketCap || data.details.market_cap || '-',
              estimate: data.details.estimate || data.details.eps_forecast || '-',
              fiscalQuarterEnding: data.details.fiscalQuarterEnding || data.details.fiscal_quarter_ending || '-',
              lastYearEPS: data.details.lastYearEPS || data.details.last_year_eps,
              numEstimates: data.details.numEstimates || data.details.num_estimates,
            })
          }
          
          // Set analysis data if available
          if (data.analysis) {
            // If analysis failed but we have a database recommendation, use it
            if (data.analysis.error && data.details?.recommendation) {
              setAnalysis({
                ticker: ticker,
                data: {
                  ...data.analysis,
                  recommendation: data.details.recommendation,
                  position_size: data.details.position_size || '6%'
                }
              })
            } else {
              setAnalysis({
                ticker: ticker,
                data: data.analysis
              })
            }
          } else if (data.details?.recommendation) {
            // If no analysis but we have database details, use those
            setAnalysis({
              ticker: ticker,
              data: {
                recommendation: data.details.recommendation,
                position_size: data.details.position_size || '6%',
                current_iv: 'N/A',
                historical_iv: 'N/A',
                iv_rank: 0,
                suggested_strategy: 'Based on historical data',
                expected_move: 'N/A'
              }
            })
          }
        } else {
          console.error('Failed to fetch complete data:', response.status)
        }
      } catch (error) {
        console.error('🚀 ~ file: page.tsx:54 → fetchAllData → error:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAllData()
  }, [ticker])

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      {/* Back button at the top */}
      <div className="mb-4">
        <Button
          variant="outline"
          onClick={() => router.back()}
          size="sm"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Earnings Calendar
        </Button>
      </div>
      
      <div className="mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-4xl font-bold">{ticker}</h1>
          {stockDetails && (
            <span className="text-xl text-muted-foreground">
              {stockDetails.companyName}
            </span>
          )}
        </div>
      </div>

      {/* Top Cards - Trading Recommendation and Position Size */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card className={
          analysis?.data?.recommendation === 'RECOMMENDED' ? 'border-green-500 bg-green-50 dark:bg-green-950/20' :
          analysis?.data?.recommendation === 'CONSIDER' ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20' :
          analysis?.data?.recommendation === 'AVOID' ? 'border-red-500 bg-red-50 dark:bg-red-950/20' :
          'border-gray-200'
        }>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Trading Recommendation
            </CardTitle>
            <TrendingUp className={
              analysis?.data?.recommendation === 'RECOMMENDED' ? 'h-4 w-4 text-green-600' :
              analysis?.data?.recommendation === 'CONSIDER' ? 'h-4 w-4 text-yellow-600' :
              analysis?.data?.recommendation === 'AVOID' ? 'h-4 w-4 text-red-600' :
              'h-4 w-4 text-muted-foreground'
            } />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              analysis?.data?.recommendation === 'RECOMMENDED' ? 'text-green-700 dark:text-green-400' :
              analysis?.data?.recommendation === 'CONSIDER' ? 'text-yellow-700 dark:text-yellow-400' :
              analysis?.data?.recommendation === 'AVOID' ? 'text-red-700 dark:text-red-400' :
              ''
            }`}>
              {loading ? 'Loading...' : (analysis?.data?.recommendation || 'Loading...')}
            </div>
            <p className="text-xs text-muted-foreground">
              Based on volatility analysis
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Position Size
            </CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? 'Loading...' : (analysis?.data?.position_size || '6%')}
            </div>
            <p className="text-xs text-muted-foreground">
              Of portfolio (Kelly criterion)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Earnings Information and Trade Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Stock Details */}
        <Card>
          <CardHeader>
            <CardTitle>Earnings Information</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : stockDetails ? (
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Report Date</span>
                  <span className="font-medium">{stockDetails.reportDate}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Report Time</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    stockDetails.reportTime === 'BMO' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                    stockDetails.reportTime === 'AMC' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' :
                    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                  }`}>
                    {stockDetails.reportTime === 'BMO' ? 'Before Open' :
                     stockDetails.reportTime === 'AMC' ? 'After Close' : 
                     stockDetails.reportTime}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Market Cap</span>
                  <span className="font-medium">{stockDetails.marketCap}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">EPS Estimate</span>
                  <span className="font-medium">
                    {(() => {
                      const value = stockDetails.estimate
                      if (!value) return '-'
                      
                      // Check if it's a negative value (has parentheses)
                      const isNegative = value.includes('(')
                      
                      // Remove parentheses and dollar sign, extract the number
                      let cleanValue = value.replace(/[()$]/g, '').trim()
                      
                      // Format with + or - sign
                      const formattedValue = isNegative ? `-$${cleanValue}` : `+$${cleanValue}`
                      
                      return (
                        <span className={isNegative ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}>
                          {formattedValue}
                        </span>
                      )
                    })()}
                  </span>
                </div>
                {stockDetails.numEstimates && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Number of Estimates</span>
                    <span className="font-medium">{stockDetails.numEstimates}</span>
                  </div>
                )}
                {stockDetails.lastYearEPS && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Year EPS</span>
                    <span className="font-medium">
                      {(() => {
                        const value = stockDetails.lastYearEPS
                        if (!value) return '-'
                        
                        // Check if it's a negative value (has parentheses)
                        const isNegative = value.includes('(')
                        
                        // Remove parentheses and dollar sign, extract the number
                        let cleanValue = value.replace(/[()$]/g, '').trim()
                        
                        // Format with + or - sign
                        const formattedValue = isNegative ? `-$${cleanValue}` : `+$${cleanValue}`
                        
                        return (
                          <span className={isNegative ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}>
                            {formattedValue}
                          </span>
                        )
                      })()}
                    </span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Fiscal Quarter</span>
                  <span className="font-medium">{stockDetails.fiscalQuarterEnding}</span>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">No data available</p>
            )}
          </CardContent>
        </Card>

        {/* Trade Analysis */}
        <Card>
          <CardHeader>
            <CardTitle>Trade Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : analysis?.data ? (
              <div className="space-y-4">
                {analysis.data.current_iv !== 'N/A' && analysis.data.historical_iv !== 'N/A' ? (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">Current IV</p>
                      <p className="text-2xl font-bold">{analysis.data.current_iv}</p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">Historical IV</p>
                      <p className="text-2xl font-bold">{analysis.data.historical_iv}</p>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">
                    Real-time volatility analysis unavailable. Using historical data.
                  </div>
                )}
                
                {analysis.data.iv_rank > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">IV Rank</p>
                    <div className="w-full bg-secondary rounded-full h-2">
                      <div 
                        className="bg-primary h-2 rounded-full"
                        style={{ width: `${analysis.data.iv_rank}%` }}
                      />
                    </div>
                    <p className="text-sm font-medium">{analysis.data.iv_rank}%</p>
                  </div>
                )}

                <div className="pt-4 border-t">
                  <p className="text-sm text-muted-foreground mb-2">Suggested Strategy</p>
                  <p className="font-medium">{analysis.data.suggested_strategy}</p>
                </div>

                {analysis.data.expected_move && analysis.data.expected_move !== 'N/A' && (
                  <div className="pt-4 border-t">
                    <p className="text-sm text-muted-foreground mb-2">Expected Move</p>
                    <p className="text-xl font-bold">{analysis.data.expected_move}</p>
                  </div>
                )}

                {analysis.data.criteria_met && (
                  <div className="pt-4 border-t space-y-2">
                    <p className="font-medium mb-2">Qualification Criteria</p>
                    <div className="space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Avg Volume (>1.5M)</span>
                        <span className={`text-sm font-bold ${
                          analysis.data.criteria_met.volume_check ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {analysis.data.criteria_met.volume_check ? 'PASS' : 'FAIL'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">IV/RV Ratio (>1.25)</span>
                        <span className={`text-sm font-bold ${
                          analysis.data.criteria_met.iv_rv_ratio ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {analysis.data.criteria_met.iv_rv_ratio ? 'PASS' : 'FAIL'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Term Structure (Negative)</span>
                        <span className={`text-sm font-bold ${
                          analysis.data.criteria_met.term_structure ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {analysis.data.criteria_met.term_structure ? 'PASS' : 'FAIL'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {analysis.data.trade_details && (
                  <div className="pt-4 border-t space-y-2">
                    <p className="font-medium mb-2">Trade Details</p>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <span className="text-muted-foreground">Entry</span>
                      <span>{analysis.data.trade_details.entry}</span>
                      <span className="text-muted-foreground">Exit</span>
                      <span>{analysis.data.trade_details.exit}</span>
                      <span className="text-muted-foreground">Max Profit</span>
                      <span className="text-green-600">{analysis.data.trade_details.max_profit}</span>
                      <span className="text-muted-foreground">Max Loss</span>
                      <span className="text-red-600">{analysis.data.trade_details.max_loss}</span>
                      <span className="text-muted-foreground">Win Rate</span>
                      <span>{analysis.data.trade_details.probability_of_profit}</span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground">{analysis?.error || 'Analysis not available'}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Back button at the bottom */}
      <div className="mt-8">
        <Button
          variant="outline"
          onClick={() => router.back()}
          size="lg"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Earnings Calendar
        </Button>
      </div>
    </div>
  )
}