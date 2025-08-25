'use client'

import { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Calendar, 
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Percent,
  Target
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts'

// Mock portfolio history data
const mockPortfolioHistory = [
  { date: '2024-01-01', value: 10000 },
  { date: '2024-01-15', value: 10175 },
  { date: '2024-01-30', value: 10420 },
  { date: '2024-02-15', value: 11200 },
  { date: '2024-03-01', value: 10800 },
  { date: '2024-03-15', value: 11500 },
  { date: '2024-04-01', value: 12100 },
  { date: '2024-04-15', value: 13200 },
  { date: '2024-05-01', value: 12800 },
  { date: '2024-05-15', value: 13500 },
  { date: '2024-06-01', value: 14200 },
  { date: '2024-06-15', value: 15100 },
  { date: '2024-07-01', value: 14800 },
  { date: '2024-07-15', value: 15600 },
  { date: '2024-08-01', value: 16200 },
  { date: '2024-08-15', value: 16800 },
  { date: '2024-08-23', value: 17250 }
]

// Mock calendar spread trades data
const mockExecutedTrades = [
  {
    id: '1',
    ticker: 'AAPL',
    companyName: 'Apple Inc.',
    tradeType: 'Calendar Spread',
    earningsDate: new Date('2024-01-25'),
    entryDate: new Date('2024-01-24'),
    exitDate: new Date('2024-01-26'),
    // Front month (sold)
    frontStrike: 185,
    frontExpiry: 'Jan 26',
    frontPremium: 5.85,
    frontContracts: 10,
    // Back month (bought)
    backStrike: 185,
    backExpiry: 'Feb 23',
    backPremium: 7.20,
    backContracts: 10,
    // Trade metrics
    netDebit: 1.35,
    closingCredit: 3.10,
    pnl: 1750,
    pnlPercent: 129.6,
    ivCrush: 32, // % drop in IV
    actualMove: 2.3, // % stock moved
    expectedMove: 4.5, // % expected move
    status: 'closed',
    recommendation: 'RECOMMENDED',
    positionSize: '6%'
  },
  {
    id: '2',
    ticker: 'MSFT',
    companyName: 'Microsoft Corporation',
    tradeType: 'Calendar Spread',
    earningsDate: new Date('2024-01-24'),
    entryDate: new Date('2024-01-23'),
    exitDate: new Date('2024-01-25'),
    frontStrike: 415,
    frontExpiry: 'Jan 26',
    frontPremium: 8.50,
    frontContracts: 5,
    backStrike: 415,
    backExpiry: 'Feb 23',
    backPremium: 10.75,
    backContracts: 5,
    netDebit: 2.25,
    closingCredit: 1.80,
    pnl: -225,
    pnlPercent: -20,
    ivCrush: 28,
    actualMove: 5.2,
    expectedMove: 3.8,
    status: 'closed',
    recommendation: 'CONSIDER',
    positionSize: '3%'
  }
]

const mockCurrentHoldings = [
  {
    id: '4',
    ticker: 'NVDA',
    companyName: 'NVIDIA Corporation',
    tradeType: 'Calendar Spread',
    earningsDate: new Date('2024-08-28'),
    entryDate: new Date('2024-08-23'),
    // Front month (sold)
    frontStrike: 120,
    frontExpiry: 'Aug 30',
    frontPremium: 4.25,
    frontContracts: 20,
    // Back month (bought)
    backStrike: 120,
    backExpiry: 'Sep 27',
    backPremium: 5.80,
    backContracts: 20,
    // Current values
    netDebit: 1.55,
    currentValue: 1.85,
    unrealizedPnl: 600,
    unrealizedPnlPercent: 19.4,
    currentIV: 65,
    entryIV: 72,
    currentStockPrice: 118.75,
    daysToEarnings: 5,
    expectedMove: 8.5,
    status: 'open',
    recommendation: 'RECOMMENDED',
    positionSize: '6%'
  },
  {
    id: '5',
    ticker: 'TSLA',
    companyName: 'Tesla, Inc.',
    tradeType: 'Calendar Spread',
    earningsDate: new Date('2024-08-25'),
    entryDate: new Date('2024-08-22'),
    frontStrike: 240,
    frontExpiry: 'Aug 30',
    frontPremium: 8.95,
    frontContracts: 10,
    backStrike: 240,
    backExpiry: 'Sep 27',
    backPremium: 11.20,
    backContracts: 10,
    netDebit: 2.25,
    currentValue: 2.05,
    unrealizedPnl: -200,
    unrealizedPnlPercent: -8.9,
    currentIV: 58,
    entryIV: 61,
    currentStockPrice: 235.80,
    daysToEarnings: 2,
    expectedMove: 6.2,
    status: 'open',
    recommendation: 'CONSIDER',
    positionSize: '3%'
  }
]

interface CalendarSpreadTrade {
  id: string
  ticker: string
  companyName: string
  tradeType: string
  earningsDate: Date
  entryDate: Date
  exitDate?: Date
  // Options details
  frontStrike: number
  frontExpiry: string
  frontPremium: number
  frontContracts: number
  backStrike: number
  backExpiry: string
  backPremium: number
  backContracts: number
  // Trade metrics
  netDebit: number
  closingCredit?: number
  currentValue?: number
  pnl?: number
  pnlPercent?: number
  unrealizedPnl?: number
  unrealizedPnlPercent?: number
  ivCrush?: number
  actualMove?: number
  expectedMove: number
  currentIV?: number
  entryIV?: number
  currentStockPrice?: number
  daysToEarnings?: number
  status: 'open' | 'closed'
  recommendation: 'RECOMMENDED' | 'CONSIDER' | 'AVOID'
  positionSize: string
}

export default function TradesPage() {
  const [executedTrades, setExecutedTrades] = useState<CalendarSpreadTrade[]>([])
  const [currentHoldings, setCurrentHoldings] = useState<CalendarSpreadTrade[]>([])
  const [portfolioHistory, setPortfolioHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTrades = async () => {
      setLoading(true)
      
      try {
        // Fetch portfolio history
        const historyResponse = await fetch('http://localhost:8000/api/trades/portfolio-history')
        if (historyResponse.ok) {
          const historyData = await historyResponse.json()
          setPortfolioHistory(historyData.history?.map((item: any) => ({
            date: item.date,
            value: item.value || item.total_value || 10000
          })) || mockPortfolioHistory)
        } else {
          setPortfolioHistory(mockPortfolioHistory)
        }

        // Fetch executed trades
        const executedResponse = await fetch('http://localhost:8000/api/trades/executed')
        if (executedResponse.ok) {
          const executedData = await executedResponse.json()
          // Map API response to frontend format
          const mappedTrades = executedData.trades?.map((trade: any) => ({
            ...trade,
            earningsDate: trade.earningsDate ? new Date(trade.earningsDate) : new Date(),
            entryDate: trade.entryDate ? new Date(trade.entryDate) : new Date(),
            exitDate: trade.exitDate ? new Date(trade.exitDate) : new Date()
          })) || []
          console.log('🚀 ~ file: page.tsx:248 → mappedTrades:', mappedTrades)
          setExecutedTrades(mappedTrades.length > 0 ? mappedTrades : mockExecutedTrades)
        } else {
          setExecutedTrades(mockExecutedTrades)
        }

        // Fetch current holdings
        const holdingsResponse = await fetch('http://localhost:8000/api/trades/current')
        if (holdingsResponse.ok) {
          const holdingsData = await holdingsResponse.json()
          // Map API response to frontend format
          const mappedHoldings = holdingsData.holdings?.map((holding: any) => ({
            ...holding,
            earningsDate: holding.earningsDate ? new Date(holding.earningsDate) : new Date(),
            entryDate: holding.entryDate ? new Date(holding.entryDate) : new Date()
          })) || []
          console.log('🚀 ~ file: page.tsx:264 → mappedHoldings:', mappedHoldings)
          setCurrentHoldings(mappedHoldings.length > 0 ? mappedHoldings : mockCurrentHoldings)
        } else {
          setCurrentHoldings(mockCurrentHoldings)
        }
      } catch (error) {
        console.log('🚀 ~ file: page.tsx:229 → fetchTrades → error:', error)
        // Use mock data on error
        setExecutedTrades(mockExecutedTrades)
        setCurrentHoldings(mockCurrentHoldings)
        setPortfolioHistory(mockPortfolioHistory)
      }
      
      setLoading(false)
    }

    fetchTrades()
  }, [])

  const totalRealizedPnl = executedTrades.reduce((sum, trade) => sum + (trade.pnl || 0), 0)
  const totalUnrealizedPnl = currentHoldings.reduce((sum, holding) => sum + (holding.unrealizedPnl || 0), 0)
  const winRate = executedTrades.length > 0 
    ? (executedTrades.filter(trade => (trade.pnl || 0) > 0).length / executedTrades.length) * 100 
    : 0
  const currentPortfolioValue = portfolioHistory[portfolioHistory.length - 1]?.value || 10000
  const startingValue = portfolioHistory[0]?.value || 10000
  const totalReturn = ((currentPortfolioValue - startingValue) / startingValue) * 100

  const CalendarSpreadCard = ({ trade, isHolding = false }: { trade: CalendarSpreadTrade; isHolding?: boolean }) => (
    <Card className="mb-4">
      <CardContent className="pt-6">
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-lg font-semibold">{trade.ticker}</h3>
              <Badge variant={trade.recommendation === 'RECOMMENDED' ? 'default' : 'secondary'}>
                {trade.recommendation}
              </Badge>
              <Badge variant={trade.status === 'open' ? 'outline' : 'secondary'}>
                {trade.status.toUpperCase()}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{trade.companyName}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Earnings: {format(trade.earningsDate, 'MMM d, yyyy')}
            </p>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-2 mb-1">
              {(isHolding ? trade.unrealizedPnl : trade.pnl) && (isHolding ? trade.unrealizedPnl : trade.pnl)! > 0 ? (
                <ArrowUpRight className="h-5 w-5 text-green-600" />
              ) : (
                <ArrowDownRight className="h-5 w-5 text-red-600" />
              )}
              <div>
                <span className={`text-lg font-semibold ${
                  (isHolding ? trade.unrealizedPnl : trade.pnl) && (isHolding ? trade.unrealizedPnl : trade.pnl)! > 0 
                    ? 'text-green-600' 
                    : 'text-red-600'
                }`}>
                  ${Math.abs((isHolding ? trade.unrealizedPnl : trade.pnl) || 0).toFixed(0)}
                </span>
                <span className={`text-sm ml-2 ${
                  (isHolding ? trade.unrealizedPnlPercent : trade.pnlPercent) && (isHolding ? trade.unrealizedPnlPercent : trade.pnlPercent)! > 0 
                    ? 'text-green-600' 
                    : 'text-red-600'
                }`}>
                  ({(isHolding ? trade.unrealizedPnlPercent : trade.pnlPercent) || 0 > 0 ? '+' : ''}{(isHolding ? trade.unrealizedPnlPercent : trade.pnlPercent)?.toFixed(1)}%)
                </span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Position: {trade.positionSize}
            </p>
          </div>
        </div>

        {/* Options Legs */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-muted/30 rounded-lg mb-4">
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <Badge variant="destructive" className="text-xs">SOLD</Badge>
              Front Month
            </h4>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Strike:</span>
                <span className="font-medium">${trade.frontStrike}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Expiry:</span>
                <span className="font-medium">{trade.frontExpiry}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Premium:</span>
                <span className="font-medium">${trade.frontPremium.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Contracts:</span>
                <span className="font-medium">{trade.frontContracts}</span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <Badge variant="default" className="text-xs">BOUGHT</Badge>
              Back Month
            </h4>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Strike:</span>
                <span className="font-medium">${trade.backStrike}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Expiry:</span>
                <span className="font-medium">{trade.backExpiry}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Premium:</span>
                <span className="font-medium">${trade.backPremium.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Contracts:</span>
                <span className="font-medium">{trade.backContracts}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Trade Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Net Debit</p>
            <p className="font-medium">${(trade.netDebit * trade.frontContracts * 100).toFixed(0)}</p>
          </div>
          {isHolding ? (
            <>
              <div>
                <p className="text-muted-foreground">Current Value</p>
                <p className="font-medium">${(trade.currentValue! * trade.frontContracts * 100).toFixed(0)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Days to Earnings</p>
                <p className="font-medium">{trade.daysToEarnings} days</p>
              </div>
              <div>
                <p className="text-muted-foreground">Current IV</p>
                <p className="font-medium">{trade.currentIV}% (was {trade.entryIV}%)</p>
              </div>
            </>
          ) : (
            <>
              <div>
                <p className="text-muted-foreground">Closing Credit</p>
                <p className="font-medium">${(trade.closingCredit! * trade.frontContracts * 100).toFixed(0)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">IV Crush</p>
                <p className="font-medium text-green-600">-{trade.ivCrush}%</p>
              </div>
              <div>
                <p className="text-muted-foreground">Stock Move</p>
                <p className={`font-medium ${
                  Math.abs(trade.actualMove!) < trade.expectedMove ? 'text-green-600' : 'text-red-600'
                }`}>
                  {trade.actualMove}% (exp: {trade.expectedMove}%)
                </p>
              </div>
            </>
          )}
        </div>

        {isHolding && (
          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <p className="text-sm">
                  Expected Move: ±{trade.expectedMove}%
                </p>
              </div>
              <p className="text-sm">
                Current Price: ${trade.currentStockPrice?.toFixed(2)}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )

  const SummaryCard = ({ title, value, icon, trend, subtitle }: {
    title: string
    value: string
    icon: React.ReactNode
    trend?: 'up' | 'down' | 'neutral'
    subtitle?: string
  }) => (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <div className="flex items-center gap-2">
              <p className={`text-2xl font-bold ${
                trend === 'up' ? 'text-green-600' : 
                trend === 'down' ? 'text-red-600' : 
                'text-foreground'
              }`}>
                {value}
              </p>
              {trend === 'up' && <TrendingUp className="h-4 w-4 text-green-600" />}
              {trend === 'down' && <TrendingDown className="h-4 w-4 text-red-600" />}
            </div>
            {subtitle && (
              <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
            )}
          </div>
          <div className="text-muted-foreground">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  )

  if (loading) {
    return (
      <div className="container mx-auto p-6 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Options Trading Portfolio</h1>
          <p className="text-muted-foreground mt-2">
            Calendar spread positions and performance tracking
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <Skeleton className="h-4 w-20 mb-2" />
                <Skeleton className="h-8 w-16 mb-2" />
                <Skeleton className="h-3 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="mb-8">
          <CardContent className="pt-6">
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Options Trading Portfolio</h1>
        <p className="text-muted-foreground mt-2">
          Calendar spread positions and performance tracking
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <SummaryCard 
          title="Portfolio Value"
          value={`$${currentPortfolioValue.toLocaleString()}`}
          icon={<DollarSign className="h-6 w-6" />}
          trend={totalReturn > 0 ? 'up' : totalReturn < 0 ? 'down' : 'neutral'}
          subtitle={`${totalReturn > 0 ? '+' : ''}${totalReturn.toFixed(1)}% total return`}
        />
        <SummaryCard 
          title="Realized P&L"
          value={`$${totalRealizedPnl.toFixed(0)}`}
          icon={<TrendingUp className="h-6 w-6" />}
          trend={totalRealizedPnl > 0 ? 'up' : totalRealizedPnl < 0 ? 'down' : 'neutral'}
          subtitle={`${executedTrades.length} closed trades`}
        />
        <SummaryCard 
          title="Unrealized P&L"
          value={`$${totalUnrealizedPnl.toFixed(0)}`}
          icon={<Activity className="h-6 w-6" />}
          trend={totalUnrealizedPnl > 0 ? 'up' : totalUnrealizedPnl < 0 ? 'down' : 'neutral'}
          subtitle={`${currentHoldings.length} open positions`}
        />
        <SummaryCard 
          title="Win Rate"
          value={`${winRate.toFixed(0)}%`}
          icon={<Percent className="h-6 w-6" />}
          trend="neutral"
          subtitle="Historical performance"
        />
      </div>

      {/* Portfolio Value Chart */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Portfolio Value Over Time</CardTitle>
          <CardDescription>
            Track your portfolio growth and drawdowns
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={portfolioHistory}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => format(new Date(value), 'MMM d')}
                className="text-muted-foreground"
                interval={0}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis 
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                className="text-muted-foreground"
              />
              <Tooltip 
                formatter={(value: any) => [`$${value.toLocaleString()}`, 'Portfolio Value']}
                labelFormatter={(label) => format(new Date(label), 'MMM d, yyyy')}
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
              />
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke="#10b981" 
                strokeWidth={2}
                fill="url(#colorValue)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Trades Tabs */}
      <Tabs defaultValue="current" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="current">Open Positions ({currentHoldings.length})</TabsTrigger>
          <TabsTrigger value="executed">Trade History ({executedTrades.length})</TabsTrigger>
        </TabsList>
        
        <TabsContent value="current" className="mt-6">
          {currentHoldings.length === 0 ? (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center py-8">
                  <Calendar className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-lg font-medium">No open positions</p>
                  <p className="text-muted-foreground">Your active calendar spreads will appear here</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {currentHoldings.map(holding => (
                <CalendarSpreadCard key={holding.id} trade={holding} isHolding={true} />
              ))}
            </div>
          )}
        </TabsContent>
        
        <TabsContent value="executed" className="mt-6">
          {executedTrades.length === 0 ? (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center py-8">
                  <DollarSign className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-lg font-medium">No trade history</p>
                  <p className="text-muted-foreground">Your closed calendar spreads will appear here</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {executedTrades
                .sort((a, b) => (b.exitDate || new Date()).getTime() - (a.exitDate || new Date()).getTime())
                .map(trade => (
                  <CalendarSpreadCard key={trade.id} trade={trade} />
                ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}