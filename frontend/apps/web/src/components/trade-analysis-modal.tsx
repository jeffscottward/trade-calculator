'use client'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'

interface TradeAnalysisData {
  ticker: string
  status: string
  data?: {
    current_iv: string
    historical_iv: string
    iv_rank: number
    suggested_strategy: string
    expected_move: string
    front_month_expiry: string
    back_month_expiry: string
    term_structure: {
      front_month_iv: string
      back_month_iv: string
      slope: string
    }
    trade_details: {
      strategy: string
      sell: string
      buy: string
      net_credit: string
      max_profit: string
      max_loss: string
      breakeven: string[]
    }
  }
}

interface TradeAnalysisModalProps {
  isOpen: boolean
  onClose: () => void
  analysis: TradeAnalysisData | null
}

export function TradeAnalysisModal({ isOpen, onClose, analysis }: TradeAnalysisModalProps) {
  if (!analysis || !analysis.data) return null

  const { data } = analysis

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-2xl flex items-center gap-2">
            Trade Analysis: {analysis.ticker}
            <Badge variant={data.term_structure.slope === 'negative' ? 'default' : 'secondary'}>
              {data.term_structure.slope.toUpperCase()} SLOPE
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Options strategy analysis for earnings trade
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6">
          {/* Volatility Metrics */}
          <div>
            <h3 className="font-semibold text-lg mb-3">Volatility Analysis</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Current IV</p>
                <p className="text-lg font-mono">{data.current_iv}</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Historical IV</p>
                <p className="text-lg font-mono">{data.historical_iv}</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">IV Rank</p>
                <p className="text-lg font-mono">{data.iv_rank}%</p>
              </div>
            </div>
          </div>

          {/* Term Structure */}
          <div>
            <h3 className="font-semibold text-lg mb-3">Term Structure</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Front Month IV</p>
                <p className="text-lg font-mono">{data.term_structure.front_month_iv}</p>
                <p className="text-xs text-muted-foreground">{data.front_month_expiry}</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Back Month IV</p>
                <p className="text-lg font-mono">{data.term_structure.back_month_iv}</p>
                <p className="text-xs text-muted-foreground">{data.back_month_expiry}</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Expected Move</p>
                <p className="text-lg font-mono">{data.expected_move}</p>
              </div>
            </div>
          </div>

          {/* Trade Details */}
          <div>
            <h3 className="font-semibold text-lg mb-3">Recommended Trade</h3>
            <div className="bg-muted p-4 rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Strategy:</span>
                <Badge variant="outline" className="font-mono">{data.trade_details.strategy}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Sell:</span>
                <span className="font-mono text-sm">{data.trade_details.sell}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Buy:</span>
                <span className="font-mono text-sm">{data.trade_details.buy}</span>
              </div>
              <div className="border-t pt-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Net Credit:</span>
                  <span className="font-mono text-green-600 dark:text-green-400">{data.trade_details.net_credit}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Max Profit:</span>
                  <span className="font-mono text-green-600 dark:text-green-400">{data.trade_details.max_profit}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Max Loss:</span>
                  <span className="font-mono text-red-600 dark:text-red-400">{data.trade_details.max_loss}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Breakeven:</span>
                  <span className="font-mono text-sm">{data.trade_details.breakeven.join(' / ')}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}