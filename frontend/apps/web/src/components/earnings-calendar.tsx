'use client'

import { useState, useEffect } from 'react'
import { Calendar } from '@/components/ui/calendar'
import { format, startOfDay } from 'date-fns'

interface EarningsCalendarProps {
  onDateSelect: (date: Date) => void
  earningsDates?: Date[]
  maxDate?: Date
}

export function EarningsCalendar({ onDateSelect, earningsDates = [], maxDate }: EarningsCalendarProps) {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date())

  useEffect(() => {
    if (selectedDate) {
      onDateSelect(selectedDate)
    }
  }, [selectedDate, onDateSelect])

  // Convert earnings dates to a format the calendar can use for styling
  const earningsDateStrings = earningsDates.map(date => 
    format(startOfDay(date), 'yyyy-MM-dd')
  )

  // Custom modifier for earnings days
  const modifiers = {
    earnings: (date: Date) => {
      const dateStr = format(startOfDay(date), 'yyyy-MM-dd')
      return earningsDateStrings.includes(dateStr)
    }
  }

  const modifiersStyles = {
    earnings: {
      backgroundColor: 'hsl(var(--accent))',
      fontWeight: 'bold',
      color: 'hsl(var(--accent-foreground))'
    }
  }

  // Get today's date at start of day for comparison
  const today = startOfDay(new Date())
  
  // Disable past dates, weekends, and dates beyond API cutoff
  const isDateDisabled = (date: Date) => {
    const isPastDate = date < today
    const isWeekend = date.getDay() === 0 || date.getDay() === 6  // Sunday = 0, Saturday = 6
    const isBeyondApiRange = maxDate && date > maxDate
    return isPastDate || isWeekend || isBeyondApiRange
  }
  
  return (
    <Calendar
      mode="single"
      selected={selectedDate}
      onSelect={setSelectedDate}
      modifiers={modifiers}
      modifiersStyles={modifiersStyles}
      disabled={isDateDisabled}
      className="rounded-md border w-fit [&_td]:h-9 [&_tbody_button]:h-8 [&_tbody_button]:w-8 [&_tbody_button]:text-sm [&_tbody_button]:font-medium [&_.rdp-button_previous]:!h-8 [&_.rdp-button_previous]:!w-8 [&_.rdp-button_next]:!h-8 [&_.rdp-button_next]:!w-8"
    />
  )
}