import { useState, useMemo, useEffect, useRef } from 'react'
import {
  Box,
  Container,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  Link,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material'
import NotificationsIcon from '@mui/icons-material/Notifications'

const API_BASE = '/api'

type HourCandle = { o: number; h: number; l: number; c: number } | null

type ActionableEntry = {
  symbol: string
  setup_id: string
  direction: string
  ma_used: number
  previous_close: number | null
  current_price: number | null
  prev_hour: HourCandle
  current_hour: HourCandle
  sector?: string | null
  industry?: string | null
  rank?: number
}

type ActionableResponse = {
  as_of_date: string | null
  entries: ActionableEntry[]
  live?: boolean
}

function formatSetupId(id: string): string {
  if (id === 'unr') return 'UnR'
  return id.charAt(0).toUpperCase() + id.slice(1).toLowerCase()
}

function tradingViewChartUrl(symbol: string): string {
  return `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}`
}

function formatHourCandle(h: HourCandle): string {
  if (!h) return '—'
  return `O ${h.o}  H ${h.h}  L ${h.l}  C ${h.c}`
}

const ET_WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
const ET_TZ = 'America/New_York'

// Parse "MM/DD/YYYY" in ET to get next open calendar date in ET, then return Date for 9:30 AM ET that day
function nextOpenAtET(now: Date, dayOffset: number): Date {
  const etDateStr = now.toLocaleString('en-US', { timeZone: ET_TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
  const [m, d, y] = etDateStr.split('/').map(Number)
  const etNoon = new Date(Date.UTC(y, m - 1, d, 12, 0, 0))
  const next = new Date(etNoon.getTime() + dayOffset * 24 * 60 * 60 * 1000)
  const nextStr = next.toLocaleString('en-US', { timeZone: ET_TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
  const [nm, nd, ny] = nextStr.split('/').map(Number)
  const utc930EST = Date.UTC(ny, nm - 1, nd, 14, 30, 0)
  const utc930EDT = Date.UTC(ny, nm - 1, nd, 13, 30, 0)
  const formatter = new Intl.DateTimeFormat('en-US', { timeZone: ET_TZ, hour: '2-digit', minute: '2-digit', hour12: false })
  return formatter.format(new Date(utc930EST)) === '09:30' ? new Date(utc930EST) : new Date(utc930EDT)
}

// US market hours: 9:30 AM - 4:00 PM Eastern
function getMarketStatus(): { isOpen: boolean; nextOpenLabel: string; nextOpenAt: Date } {
  const now = new Date()
  const etStr = now.toLocaleString('en-US', { timeZone: ET_TZ, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  const [h, m, s] = etStr.split(':').map(Number)
  const etWeekdayName = now.toLocaleString('en-US', { timeZone: ET_TZ, weekday: 'long' })
  const etDay = ET_WEEKDAYS.indexOf(etWeekdayName)
  const isWeekday = etDay >= 1 && etDay <= 5
  const mins = h * 60 + m + s / 60
  const openMins = 9 * 60 + 30
  const closeMins = 16 * 60
  const isOpen = isWeekday && mins >= openMins && mins < closeMins

  let dayOffset = 0
  if (!isWeekday) {
    dayOffset = etDay === 0 ? 1 : etDay === 6 ? 2 : 0
  } else if (mins >= closeMins) {
    dayOffset = etDay === 5 ? 3 : 1
  } else if (mins < openMins) {
    dayOffset = 0
  } else {
    dayOffset = etDay === 5 ? 3 : 1
  }
  const nextOpenAt = nextOpenAtET(now, dayOffset)
  const nextOpenLabel = nextOpenAt.toLocaleString(undefined, {
    weekday: 'short',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  })
  return { isOpen, nextOpenLabel, nextOpenAt }
}

const REFRESH_OPTIONS = [
  { value: 5000, label: '5s' },
  { value: 60000, label: '1 min' },
  { value: 300000, label: '5 min' },
] as const
const ALERT_FLASH_MS = 60000

function rowKey(row: ActionableEntry): string {
  return `${row.symbol}-${row.setup_id}-${row.ma_used}`
}

export default function RealTimeDashboard() {
  const [refreshMs, setRefreshMs] = useState(300000)
  const [data, setData] = useState<ActionableResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [marketStatus, setMarketStatus] = useState<ReturnType<typeof getMarketStatus>>(() => getMarketStatus())
  const [alertUntil, setAlertUntil] = useState<Record<string, number>>({})
  const lastPriceRef = useRef<Record<string, number>>({})

  const actionableEntries = useMemo(() => {
    if (!data?.entries) return []
    return data.entries.filter((e) => {
      const prev = e.previous_close
      const curr = e.current_price
      if (prev == null || curr == null) return false
      if (e.direction === 'long') return curr < prev
      if (e.direction === 'short') return curr > prev
      return false
    })
  }, [data?.entries])

  useEffect(() => {
    let cancelled = false
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE}/realtime/actionable`)
        if (!res.ok) throw new Error('Failed to load')
        const json: ActionableResponse = await res.json()
        if (cancelled) return
        const entries = json.entries || []
        const actionable = entries.filter((e) => {
          const prev = e.previous_close
          const curr = e.current_price
          if (prev == null || curr == null) return false
          if (e.direction === 'long') return curr < prev
          if (e.direction === 'short') return curr > prev
          return false
        })
        actionable.forEach((e) => {
          const key = rowKey(e)
          const curr = e.current_price
          const prevC = e.prev_hour?.c
          if (curr == null || prevC == null) return
          const last = lastPriceRef.current[key]
          const isLong = e.direction === 'long'
          const crossed =
            isLong
              ? (last !== undefined && last <= prevC && curr > prevC)
              : (last !== undefined && last >= prevC && curr < prevC)
          if (crossed) {
            setAlertUntil((a) => ({ ...a, [key]: Date.now() + ALERT_FLASH_MS }))
          }
          lastPriceRef.current[key] = curr
        })
        setData(json)
        setError(null)
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load')
          setData(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    const t = setInterval(fetchData, refreshMs)
    return () => {
      cancelled = true
      clearInterval(t)
    }
  }, [refreshMs])

  useEffect(() => {
    const id = setInterval(() => setMarketStatus(getMarketStatus()), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const id = setInterval(() => {
      const now = Date.now()
      setAlertUntil((prev) => {
        const next = Object.fromEntries(
          Object.entries(prev).filter(([, until]) => until > now)
        )
        return Object.keys(next).length === Object.keys(prev).length ? prev : next
      })
    }, 1000)
    return () => clearInterval(id)
  }, [])

  const [countdown, setCountdown] = useState<string>('')
  useEffect(() => {
    if (marketStatus.isOpen) {
      setCountdown('')
      return
    }
    const tick = () => {
      const ms = marketStatus.nextOpenAt.getTime() - Date.now()
      if (ms <= 0) {
        setCountdown('Opening soon…')
        return
      }
      const h = Math.floor(ms / 3600000)
      const m = Math.floor((ms % 3600000) / 60000)
      const s = Math.floor((ms % 60000) / 1000)
      setCountdown(`${h}h ${m}m ${s}s`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [marketStatus.isOpen, marketStatus.nextOpenAt])

  const [currentTimeEt, setCurrentTimeEt] = useState('')
  useEffect(() => {
    const tick = () => {
      setCurrentTimeEt(
        new Date().toLocaleTimeString('en-US', {
          timeZone: 'America/New_York',
          hour12: true,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      )
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', py: 3 }}>
      <Container maxWidth="xl">
        <Box
          sx={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 2,
            mb: 3,
            flexWrap: 'wrap',
          }}
        >
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 600, mb: 0.5 }}>
              RealTime Dashboard
            </Typography>
            {marketStatus.isOpen ? (
              <Typography variant="body2" color="text.secondary">
                Market open · ET {currentTimeEt}
              </Typography>
          ) : (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              <Box
                component="span"
                sx={{
                  px: 1.25,
                  py: 0.4,
                  borderRadius: 1,
                  bgcolor: 'error.dark',
                  color: '#fff',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Market closed
              </Box>
              <Typography variant="body2" color="text.secondary">
                Next open: {marketStatus.nextOpenLabel}
              </Typography>
            </Box>
          )}
        </Box>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="refresh-label">Refresh Interval</InputLabel>
          <Select
            labelId="refresh-label"
            value={refreshMs}
            label="Refresh Interval"
            onChange={(e) => setRefreshMs(Number(e.target.value))}
          >
            {REFRESH_OPTIONS.map((o) => (
              <MenuItem key={o.value} value={o.value}>
                {o.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
          {marketStatus.isOpen ? (
            <Box
              component="span"
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                minWidth: '6.5rem',
                px: 1.5,
                py: 0.75,
                borderRadius: 2,
                bgcolor: 'primary.dark',
                color: '#fff',
                fontSize: '0.8rem',
                fontWeight: 600,
                fontVariantNumeric: 'tabular-nums',
                animation: 'badge-pulse 2s ease-in-out infinite',
                '@keyframes badge-pulse': {
                  '0%, 100%': { boxShadow: '0 0 0 0 rgba(14, 165, 233, 0.25)' },
                  '50%': { boxShadow: '0 0 0 4px rgba(14, 165, 233, 0.15)' },
                },
              }}
            >
              ET {currentTimeEt}
            </Box>
          ) : (
            <Box
              sx={{
                display: 'inline-flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 0.5,
              }}
            >
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Countdown to Opening Bell
              </Typography>
              <Box
                component="span"
                sx={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 0.75,
                  minWidth: '7rem',
                  px: 1.5,
                  py: 0.75,
                  borderRadius: 2,
                  bgcolor: 'rgba(234, 179, 8, 0.12)',
                  border: '1px solid',
                  borderColor: 'rgba(234, 179, 8, 0.35)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  fontVariantNumeric: 'tabular-nums',
                  color: 'warning.light',
                  animation: 'countdown-tick 1s ease-out infinite',
                  '@keyframes countdown-tick': {
                    '0%, 90%': { opacity: 1, boxShadow: 'none' },
                    '95%': { opacity: 0.92, boxShadow: 'inset 0 0 0 1px rgba(234,179,8,0.2)' },
                    '100%': { opacity: 1, boxShadow: 'none' },
                  },
                }}
              >
                <NotificationsIcon sx={{ fontSize: '1rem', color: 'warning.main' }} />
                {countdown || '—'}
              </Box>
            </Box>
          )}
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Paper sx={{ overflow: 'hidden' }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
                <Typography variant="body2" component="span" sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  Actionable: long setups below prior close, short setups above prior close
                  {data?.as_of_date ? ` · Watchlist as of ${data.as_of_date}` : ''}
                  {actionableEntries.length ? ` · ${actionableEntries.length} row(s)` : ''}
                  {data?.live ? (
                    <Box
                      component="span"
                      sx={{
                        px: 0.75,
                        py: 0.25,
                        borderRadius: 1,
                        bgcolor: 'success.dark',
                        color: '#fff',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                      }}
                    >
                      Live
                    </Box>
                  ) : null}
                </Typography>
              </Box>
              <TableContainer>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Rank</TableCell>
                      <TableCell>Symbol</TableCell>
                      <TableCell>Setup</TableCell>
                      <TableCell>Industry / Sector</TableCell>
                      <TableCell>MA</TableCell>
                      <TableCell align="right">Current Price</TableCell>
                      <TableCell>Current Hourly Candle</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {actionableEntries.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                          No actionable entries. Ensure watchlist is built for today and market data is available.
                        </TableCell>
                      </TableRow>
                    ) : (
                      actionableEntries.map((row, i) => {
                        const key = rowKey(row)
                        const flash = (alertUntil[key] ?? 0) > Date.now()
                        return (
                          <TableRow
                            key={`${key}-${i}`}
                            sx={{
                              bgcolor: flash ? 'warning.light' : undefined,
                              animation: flash ? 'flash 0.5s ease-in-out' : undefined,
                              '@keyframes flash': {
                                '0%, 100%': { opacity: 1 },
                                '50%': { opacity: 0.85 },
                              },
                            }}
                          >
                            <TableCell sx={{ fontWeight: 600 }}>{i + 1}</TableCell>
                            <TableCell sx={{ fontWeight: 500 }}>
                              <Link
                                href={tradingViewChartUrl(row.symbol)}
                                target="_blank"
                                rel="noopener noreferrer"
                                sx={{ color: 'primary.main' }}
                              >
                                {row.symbol}
                              </Link>
                            </TableCell>
                            <TableCell>{formatSetupId(row.setup_id)}</TableCell>
                            <TableCell sx={{ fontSize: '0.8rem', color: 'text.secondary' }}>
                              {[row.industry, row.sector].filter(Boolean).join(' · ') || '—'}
                            </TableCell>
                            <TableCell>{row.ma_used}</TableCell>
                            <TableCell align="right">
                              {row.current_price != null ? row.current_price.toFixed(2) : '—'}
                            </TableCell>
                            <TableCell sx={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>
                              {formatHourCandle(row.current_hour)}
                            </TableCell>
                          </TableRow>
                        )
                      })
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </Paper>
      </Container>
    </Box>
  )
}
