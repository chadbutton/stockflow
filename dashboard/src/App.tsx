import { useState, useMemo, useEffect, useRef } from 'react'
import {
  Box,
  Container,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  Link,
  Button,
  Tabs,
  Tab,
} from '@mui/material'
import ContentPasteIcon from '@mui/icons-material/ContentPaste'
import RealTimeDashboard from './RealTimeDashboard'

const API_BASE = '/api'

function apiDetailToString(detail: unknown): string {
  if (detail == null) return ''
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg?: string }).msg) : JSON.stringify(d)))
    return parts.join('; ')
  }
  if (typeof detail === 'object') return JSON.stringify(detail)
  return String(detail)
}

type WatchlistEntry = {
  symbol: string
  setup_id: string
  direction: string
  ma_used: number
  as_of_date: string
  price: number | null
  ema_20: number | null
  ma_50: number | null
  ma_200: number | null
  atr: number | null
  current_price: number | null
  performance_pct: number | null
  sector?: string | null
  industry?: string | null
  rank?: number
}

type WatchlistResponse = {
  as_of_date: string
  setup_id: string
  entries: WatchlistEntry[]
}

function formatPct(value: number | null): string {
  if (value === null) return '—'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function getPast60Days(): string[] {
  const out: string[] = []
  const today = new Date()
  for (let i = 0; i < 60; i++) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    out.push(d.toISOString().slice(0, 10))
  }
  return out
}

const SETUP_OPTIONS = [{ id: 'unr', label: 'UnR' }]

function formatSetupId(id: string): string {
  if (id === 'unr') return 'UnR'
  return id.charAt(0).toUpperCase() + id.slice(1).toLowerCase()
}

function tradingViewChartUrl(symbol: string): string {
  return `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}`
}

function atrDistance(currentPrice: number | null, ma: number | null, atr: number | null): number | null {
  if (currentPrice == null || ma == null || atr == null || atr <= 0) return null
  return (currentPrice - ma) / atr
}

function formatAtrDist(dist: number | null): string {
  if (dist === null) return '—'
  const sign = dist >= 0 ? '+' : ''
  return `${sign}${dist.toFixed(2)}`
}

function atrDistSx(dist: number | null): { color: string } {
  if (dist === null) return { color: 'text.secondary' }
  if (dist >= 0) return { color: 'success.main' }
  return { color: 'error.main' }
}

export default function App() {
  const [page, setPage] = useState<'watchlist' | 'realtime'>('watchlist')
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    const t = new Date()
    return t.toISOString().slice(0, 10)
  })
  const [selectedSetup, setSelectedSetup] = useState<string>('unr')
  const [data, setData] = useState<WatchlistResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const dateOptions = useMemo(() => getPast60Days(), [])
  const filteredEntries = useMemo(() => {
    if (!data?.entries) return []
    return data.entries.filter((e) => e.setup_id === selectedSetup)
  }, [data?.entries, selectedSetup])
  const longEntries = useMemo(() => filteredEntries.filter((e) => e.direction === 'long'), [filteredEntries])
  const shortEntries = useMemo(() => filteredEntries.filter((e) => e.direction === 'short'), [filteredEntries])
  const longSymbolsCsv = useMemo(() => {
    const symbols = [...new Set(longEntries.map((e) => e.symbol))].sort()
    return symbols.join(',')
  }, [longEntries])
  const shortSymbolsCsv = useMemo(() => {
    const symbols = [...new Set(shortEntries.map((e) => e.symbol))].sort()
    return symbols.join(',')
  }, [shortEntries])

  const [copyLongFeedback, setCopyLongFeedback] = useState<string | null>(null)
  const [copyShortFeedback, setCopyShortFeedback] = useState<string | null>(null)
  const watchlistCacheRef = useRef<Record<string, WatchlistResponse>>({})

  const handleCopyLongs = async () => {
    if (!longSymbolsCsv) return
    try {
      await navigator.clipboard.writeText(longSymbolsCsv)
      setCopyLongFeedback('Copied!')
      setTimeout(() => setCopyLongFeedback(null), 1500)
    } catch {
      setCopyLongFeedback('Copy failed')
      setTimeout(() => setCopyLongFeedback(null), 2000)
    }
  }
  const handleCopyShorts = async () => {
    if (!shortSymbolsCsv) return
    try {
      await navigator.clipboard.writeText(shortSymbolsCsv)
      setCopyShortFeedback('Copied!')
      setTimeout(() => setCopyShortFeedback(null), 1500)
    } catch {
      setCopyShortFeedback('Copy failed')
      setTimeout(() => setCopyShortFeedback(null), 2000)
    }
  }

  const loadWatchlist = async (date: string) => {
    const cached = watchlistCacheRef.current[date]
    if (cached) {
      setData(cached)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/watchlist?date=${date}&use_cache=true`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        const msg = err?.detail != null ? apiDetailToString(err.detail) : res.statusText || 'Failed to load'
        throw new Error(msg || 'Failed to load')
      }
      const json: WatchlistResponse = await res.json()
      watchlistCacheRef.current[date] = json
      setData(json)
    } catch (e) {
      let msg = e instanceof Error ? e.message : 'Failed to load watchlist'
      if (msg === '[object Object]') msg = 'Failed to load watchlist'
      const isRefused = msg.includes('Failed to fetch') || msg.includes('NetworkError')
      setError(
        isRefused
          ? 'Cannot reach the API (connection refused). Start the backend: cd backend, set PYTHONPATH, then run: python -m uvicorn server.app:app --port 8000'
          : msg
      )
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  const handleDateChange = (date: string) => {
    setSelectedDate(date)
    loadWatchlist(date)
  }

  useEffect(() => {
    loadWatchlist(selectedDate)
  }, [selectedDate])

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: 'background.default',
        py: 3,
      }}
    >
      <Container maxWidth="xl">
        <Tabs value={page} onChange={(_, v) => setPage(v)} sx={{ mb: 2 }}>
          <Tab label="Watchlist" value="watchlist" />
          <Tab label="RealTime Dashboard" value="realtime" />
        </Tabs>
        {page === 'realtime' ? (
          <RealTimeDashboard />
        ) : (
          <>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 700 }}>
            Watchlist
          </Typography>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel id="setup-label">Setup</InputLabel>
            <Select
              labelId="setup-label"
              value={selectedSetup}
              label="Setup"
              onChange={(e) => setSelectedSetup(e.target.value)}
            >
              {SETUP_OPTIONS.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel id="date-label">As of date</InputLabel>
            <Select
              labelId="date-label"
              value={selectedDate}
              label="As of date"
              onChange={(e) => handleDateChange(e.target.value)}
            >
              {dateOptions.map((d) => (
                <MenuItem key={d} value={d}>
                  {d}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            size="small"
            onClick={handleCopyLongs}
            disabled={!longSymbolsCsv}
            startIcon={<ContentPasteIcon />}
            sx={{ alignSelf: 'stretch' }}
          >
            {copyLongFeedback ?? 'Copy Long List'}
          </Button>
          <Button
            variant="outlined"
            size="small"
            onClick={handleCopyShorts}
            disabled={!shortSymbolsCsv}
            startIcon={<ContentPasteIcon />}
            sx={{ alignSelf: 'stretch' }}
          >
            {copyShortFeedback ?? 'Copy Short List'}
          </Button>
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
          ) : data ? (
            <>
              <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
                <Typography variant="body2">
                  Watchlist as of <strong>{data.as_of_date}</strong>
                  {filteredEntries.length ? ` · ${filteredEntries.length} entr${filteredEntries.length === 1 ? 'y' : 'ies'}` : ''}
                </Typography>
              </Box>

              <Box sx={{ px: 2, py: 1.5 }}>
                <Typography variant="subtitle2" sx={{ color: 'success.main', fontWeight: 600, mb: 1 }}>
                  Long ({longEntries.length})
                </Typography>
                <TableContainer>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Rank</TableCell>
                        <TableCell>Symbol</TableCell>
                        <TableCell>Setup</TableCell>
                        <TableCell>Industry / Sector</TableCell>
                        <TableCell>MA</TableCell>
                        <TableCell align="right">Price (then)</TableCell>
                        <TableCell align="right" title="ATR dist from EMA 20">20ema</TableCell>
                        <TableCell align="right" title="ATR dist from MA 50">50sma</TableCell>
                        <TableCell align="right" title="ATR dist from MA 200">200sma</TableCell>
                        <TableCell align="right">ATR</TableCell>
                        <TableCell align="right">Current</TableCell>
                        <TableCell align="right">Performance</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {longEntries.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={12} align="center" sx={{ py: 3 }}>
                            No long entries for this date and setup.
                          </TableCell>
                        </TableRow>
                      ) : (
                        longEntries.map((row, i) => (
                          <TableRow key={`long-${row.symbol}-${row.setup_id}-${row.ma_used}-${i}`}>
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
                              {row.price != null ? row.price.toFixed(2) : '—'}
                            </TableCell>
                            <TableCell align="right" sx={atrDistSx(atrDistance(row.current_price, row.ema_20, row.atr))}>
                              {formatAtrDist(atrDistance(row.current_price, row.ema_20, row.atr))}
                            </TableCell>
                            <TableCell align="right" sx={atrDistSx(atrDistance(row.current_price, row.ma_50, row.atr))}>
                              {formatAtrDist(atrDistance(row.current_price, row.ma_50, row.atr))}
                            </TableCell>
                            <TableCell align="right" sx={atrDistSx(atrDistance(row.current_price, row.ma_200, row.atr))}>
                              {formatAtrDist(atrDistance(row.current_price, row.ma_200, row.atr))}
                            </TableCell>
                            <TableCell align="right">
                              {row.atr != null ? row.atr.toFixed(2) : '—'}
                            </TableCell>
                            <TableCell align="right">
                              {row.current_price != null ? row.current_price.toFixed(2) : '—'}
                            </TableCell>
                            <TableCell align="right">
                              {row.performance_pct != null ? (
                                <Typography
                                  component="span"
                                  sx={{
                                    color: row.performance_pct >= 0 ? 'success.main' : 'error.main',
                                    fontWeight: 600,
                                  }}
                                >
                                  {formatPct(row.performance_pct)}
                                </Typography>
                            ) : (
                              '—'
                            )}
                          </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>

              <Box sx={{ px: 2, py: 1.5, pt: 0 }}>
                <Typography variant="subtitle2" sx={{ color: 'error.main', fontWeight: 600, mb: 1 }}>
                  Short ({shortEntries.length})
                </Typography>
                <TableContainer>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Rank</TableCell>
                        <TableCell>Symbol</TableCell>
                        <TableCell>Setup</TableCell>
                        <TableCell>Industry / Sector</TableCell>
                        <TableCell>MA</TableCell>
                        <TableCell align="right">Price (then)</TableCell>
                        <TableCell align="right" title="ATR dist from EMA 20">20ema</TableCell>
                        <TableCell align="right" title="ATR dist from MA 50">50sma</TableCell>
                        <TableCell align="right" title="ATR dist from MA 200">200sma</TableCell>
                        <TableCell align="right">ATR</TableCell>
                        <TableCell align="right">Current</TableCell>
                        <TableCell align="right">Performance</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {shortEntries.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={12} align="center" sx={{ py: 3 }}>
                            No short entries for this date and setup.
                          </TableCell>
                        </TableRow>
                      ) : (
                        shortEntries.map((row, i) => (
                          <TableRow key={`short-${row.symbol}-${row.setup_id}-${row.ma_used}-${i}`}>
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
                              {row.price != null ? row.price.toFixed(2) : '—'}
                            </TableCell>
                            <TableCell align="right" sx={atrDistSx(atrDistance(row.current_price, row.ema_20, row.atr))}>
                              {formatAtrDist(atrDistance(row.current_price, row.ema_20, row.atr))}
                            </TableCell>
                            <TableCell align="right" sx={atrDistSx(atrDistance(row.current_price, row.ma_50, row.atr))}>
                              {formatAtrDist(atrDistance(row.current_price, row.ma_50, row.atr))}
                            </TableCell>
                            <TableCell align="right" sx={atrDistSx(atrDistance(row.current_price, row.ma_200, row.atr))}>
                              {formatAtrDist(atrDistance(row.current_price, row.ma_200, row.atr))}
                            </TableCell>
                            <TableCell align="right">
                              {row.atr != null ? row.atr.toFixed(2) : '—'}
                            </TableCell>
                            <TableCell align="right">
                              {row.current_price != null ? row.current_price.toFixed(2) : '—'}
                            </TableCell>
                            <TableCell align="right">
                              {row.performance_pct != null ? (
                                <Typography
                                  component="span"
                                  sx={{
                                    color: row.performance_pct >= 0 ? 'success.main' : 'error.main',
                                    fontWeight: 600,
                                  }}
                                >
                                  {formatPct(row.performance_pct)}
                                </Typography>
                            ) : (
                              '—'
                            )}
                          </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            </>
          ) : null}
        </Paper>
          </>
        )}
      </Container>
    </Box>
  )
}
