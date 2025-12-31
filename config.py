"""
SwingFinder Configuration
Centralized configuration for all constants and magic numbers.
"""

# ============================================================================
# API & AUTHENTICATION
# ============================================================================

# Tiingo API settings
TIINGO_BASE_URL = "https://api.tiingo.com"
TIINGO_TIMEOUT = 15  # seconds

# ============================================================================
# SCANNER CONFIGURATION
# ============================================================================

# Data fetching
SCAN_LOOKBACK_DAYS = 120  # how many days of Tiingo history to load
SCAN_TIMEOUT = 15  # seconds for API requests

# Concurrency settings
MAX_WORKERS = 8  # number of threads for concurrent scanning
REQUEST_PAUSE_S = 0.25  # delay between batches to be nice to API
BATCH_TICKER_COUNT = 50  # tickers per batch

# Default filter values
DEFAULT_MIN_PRICE = 5.0
DEFAULT_MAX_PRICE = 500.0
DEFAULT_MIN_VOLUME = 500_000

# ============================================================================
# RISK MANAGEMENT DEFAULTS
# ============================================================================

# Stop loss and target calculations
DEFAULT_STOP_ATR_MULT = 2.0  # Stop = Entry - (ATR * multiplier)
DEFAULT_TARGET_R_MULT = 2.0  # Target based on R:R ratio
DEFAULT_RR_RATIO = 2.0  # Risk/Reward ratio

# Position sizing
DEFAULT_ACCOUNT_SIZE = 10_000.0
DEFAULT_RISK_PER_TRADE = 1.0  # percentage

# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================

# Moving averages
EMA_SHORT_PERIOD = 20
EMA_LONG_PERIOD = 50

# RSI settings
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# ATR settings
ATR_PERIOD = 14

# Bollinger Bands
BB_PERIOD = 20
BB_STD_DEV = 2

# Lookback periods
LOOKBACK_HIGH_LOW = 20  # for HH20/LL20

# ============================================================================
# SETUP CLASSIFICATION
# ============================================================================

# Pullback criteria
PULLBACK_RSI_MAX = 45
PULLBACK_BAND_POS_MAX = 0.3

# Breakout criteria
BREAKOUT_RSI_MIN = 55
BREAKOUT_BAND_POS_MIN = 0.7

# ============================================================================
# SMART MODE / MARKET ANALYSIS
# ============================================================================

# Market snapshot settings
MARKET_SNAPSHOT_LOOKBACK = 60  # days
MARKET_SNAPSHOT_TTL = 60 * 60 * 6  # cache for 6 hours

# Volatility thresholds
HIGH_VOLATILITY_ATRP = 2.5  # ATR% threshold for high volatility

# Sector ETFs for analysis
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLI": "Industrials",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLC": "Communication Services",
}

# ============================================================================
# ACTIVE TRADES
# ============================================================================

# Price refresh settings
PRICE_REFRESH_TTL = 60  # seconds
INTRADAY_LOOKBACK_DAYS = 5
INTRADAY_TIMEFRAME = "1hour"

# ============================================================================
# CACHING
# ============================================================================

# Cache TTL (time-to-live) in seconds
CACHE_TTL_TICKERS = 60 * 60 * 24  # 24 hours
CACHE_TTL_HISTORY = 60 * 30  # 30 minutes
CACHE_TTL_SECTOR = 60 * 60 * 24  # 24 hours
CACHE_TTL_EARNINGS = 60 * 60 * 24  # 24 hours
CACHE_TTL_REALTIME = 60  # 1 minute
CACHE_TTL_INTRADAY = 600  # 10 minutes

# ============================================================================
# FILE PATHS
# ============================================================================

# Data directories
DATA_DIR = "data"
CACHE_DIR = ".cache"
ARCHIVE_DIR = "archive"

# Specific files
ACTIVE_TRADES_FILE = "data/active_trades.json"
WATCHLIST_FILE = ".cache/watchlist.json"
UNIVERSE_CACHE_FILE = "utils/filtered_universe.json"

# ============================================================================
# UNIVERSE BUILDER
# ============================================================================

# Exchange filters
ALLOWED_EXCHANGES = {"NASDAQ", "NYSE", "AMEX", "ARCA"}

# Asset type filters
ALLOWED_ASSET_TYPES = {"Stock", "REIT", "Equity", "ETF"}

# Price filters
UNIVERSE_MIN_PRICE = 1.0
UNIVERSE_MAX_PRICE = 10_000.0

# Volume filters
UNIVERSE_MIN_AVG_VOLUME = 100_000

# ============================================================================
# UI / DISPLAY
# ============================================================================

# Streamlit page config
PAGE_TITLE = "SwingFinder"
PAGE_LAYOUT = "wide"

# Progress bar update frequency
PROGRESS_UPDATE_FREQUENCY = 1  # update every N tickers

# ============================================================================
# LOGGING
# ============================================================================

# Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ============================================================================
# FEATURE FLAGS
# ============================================================================

# Enable/disable features
ENABLE_SMART_MODE = True
ENABLE_YAHOO_FALLBACK = True
ENABLE_SECTOR_ANALYSIS = True
ENABLE_EARNINGS_DATES = True
ENABLE_SENTIMENT_ANALYSIS = True

# ============================================================================
# ANALYZER SETTINGS
# ============================================================================

# Forecast settings
FORECAST_LOOKBACK = 20  # days for linear regression

# Chart settings
CHART_DEFAULT_DAYS = 200

# ============================================================================
# VALIDATION
# ============================================================================

# Input validation ranges
MIN_SHARES = 1
MAX_SHARES = 1_000_000
MIN_PRICE_INPUT = 0.01
MAX_PRICE_INPUT = 100_000.0

