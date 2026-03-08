import { createTheme, alpha } from '@mui/material/styles'

// Replit-style dark dashboard: deep dark bg, soft cards, accent color
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#0ea5e9',
      light: '#38bdf8',
      dark: '#0284c7',
    },
    background: {
      default: '#0f1419',
      paper: '#1a1f26',
    },
    success: {
      main: '#22c55e',
      light: '#4ade80',
      dark: '#16a34a',
    },
    error: {
      main: '#ef4444',
      light: '#f87171',
      dark: '#dc2626',
    },
    warning: {
      main: '#eab308',
      light: '#fde047',
      dark: '#ca8a04',
    },
    text: {
      primary: '#e6edf3',
      secondary: '#8b949e',
      disabled: '#6e7681',
    },
    divider: alpha('#e6edf3', 0.08),
  },
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: '"DM Sans", "Segoe UI", system-ui, sans-serif',
    h4: {
      fontWeight: 600,
      letterSpacing: '-0.02em',
    },
    h6: {
      fontWeight: 600,
    },
    body2: {
      color: '#8b949e',
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#0f1419',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: '#1a1f26',
          border: '1px solid rgba(255,255,255,0.06)',
          boxShadow: '0 4px 24px rgba(0,0,0,0.24)',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          paddingTop: 6,
          paddingBottom: 6,
          paddingLeft: 12,
          paddingRight: 12,
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-root': {
            fontWeight: 600,
            color: '#8b949e',
            backgroundColor: 'rgba(255,255,255,0.02)',
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        select: {
          paddingTop: 10,
          paddingBottom: 10,
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          '&.Mui-selected': {
            backgroundColor: alpha('#0ea5e9', 0.16),
          },
        },
      },
    },
  },
})

export { theme }
