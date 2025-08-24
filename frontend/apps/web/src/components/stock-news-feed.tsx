'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ExternalLink, TrendingUp, Clock } from 'lucide-react'
import { format, formatDistanceToNow } from 'date-fns'

interface NewsItem {
  id: string
  title: string
  description: string
  url: string
  source: string
  publishedAt: string
  category?: string
  sentiment?: 'positive' | 'negative' | 'neutral'
}

export function StockNewsFeed() {
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchNews = async () => {
      try {
        setLoading(true)
        setError(null)
        
        // Using RSS2JSON to convert RSS feeds to JSON (free, no API key needed)
        // We'll use multiple sources and combine them
        const sources = [
          {
            name: 'MarketWatch',
            url: 'https://api.rss2json.com/v1/api.json?rss_url=http://feeds.marketwatch.com/marketwatch/topstories'
          },
          {
            name: 'Yahoo Finance',
            url: 'https://api.rss2json.com/v1/api.json?rss_url=https://finance.yahoo.com/rss/topstories'
          }
        ]

        const newsPromises = sources.map(async (source) => {
          try {
            const response = await fetch(source.url)
            if (!response.ok) return []
            
            const data = await response.json()
            if (data.status !== 'ok' || !data.items) return []
            
            return data.items.slice(0, 5).map((item: any, index: number) => ({
              id: `${source.name}-${index}-${item.guid || item.link || item.title?.substring(0, 20)}`,
              title: item.title,
              description: item.description ? item.description.replace(/<[^>]*>?/gm, '').substring(0, 150).trim() : '',
              url: item.link,
              source: source.name,
              publishedAt: item.pubDate,
              category: item.categories?.[0] || 'Markets',
              sentiment: analyzeSentiment(item.title + ' ' + (item.description || ''))
            }))
          } catch (err) {
            console.log(`🚀 ~ file: stock-news-feed.tsx:58 → fetchNews → Error fetching ${source.name}:`, err)
            return []
          }
        })

        const allNews = await Promise.all(newsPromises)
        const combinedNews = allNews
          .flat()
          .sort((a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime())
          .slice(0, 10)
        
        setNews(combinedNews)
      } catch (err) {
        console.log('🚀 ~ file: stock-news-feed.tsx:71 → fetchNews → error:', err)
        setError('Failed to load news')
      } finally {
        setLoading(false)
      }
    }

    fetchNews()
    
    // Refresh news every 5 minutes
    const interval = setInterval(fetchNews, 5 * 60 * 1000)
    
    return () => clearInterval(interval)
  }, [])

  // Simple sentiment analysis based on keywords
  function analyzeSentiment(text: string): 'positive' | 'negative' | 'neutral' {
    const positive = ['surge', 'gain', 'rise', 'jump', 'rally', 'record', 'high', 'profit', 'beat', 'growth']
    const negative = ['fall', 'drop', 'plunge', 'loss', 'decline', 'crash', 'low', 'miss', 'cut', 'fear']
    
    const lowerText = text.toLowerCase()
    const posCount = positive.filter(word => lowerText.includes(word)).length
    const negCount = negative.filter(word => lowerText.includes(word)).length
    
    if (posCount > negCount) return 'positive'
    if (negCount > posCount) return 'negative'
    return 'neutral'
  }

  const getSentimentColor = (sentiment?: string) => {
    switch (sentiment) {
      case 'positive': return 'text-green-600 dark:text-green-400'
      case 'negative': return 'text-red-600 dark:text-red-400'
      default: return 'text-gray-600 dark:text-gray-400'
    }
  }

  return (
    <Card className="w-full h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Market News
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-3 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground">{error}</p>
          </div>
        ) : news.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground">No news available</p>
          </div>
        ) : (
          <div style={{ height: '370px' }} className="overflow-y-auto pr-2">
            {news.map((item, index) => (
              <article
                key={item.id}
                className="border-b last:border-0"
              >
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block py-3 px-1 hover:bg-muted/30 transition-colors rounded-md"
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <h3 className="font-medium text-sm line-clamp-2 flex-1">
                      {item.title}
                    </h3>
                    <ExternalLink className="h-3 w-3 mt-1 flex-shrink-0 text-muted-foreground" />
                  </div>
                  
                  {item.description && (
                    <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                      {item.description}
                    </p>
                  )}
                  
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {item.source}
                    </Badge>
                    <span className={`text-xs ${getSentimentColor(item.sentiment)}`}>
                      •
                    </span>
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDistanceToNow(new Date(item.publishedAt), { addSuffix: true })}
                    </span>
                  </div>
                </a>
              </article>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}