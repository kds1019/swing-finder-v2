"""
Rate Limiter for Tiingo API
Prevents hitting API rate limits (50 requests per minute for Power Plan)
"""

import time
from collections import deque
from datetime import datetime, timedelta
from typing import Optional
import streamlit as st
from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter for API calls.
    Tracks requests in a time window and blocks when limit is reached.
    """
    
    def __init__(self, max_requests: int = 50, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds (default: 60 seconds)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()  # Store timestamps of requests
        
        logger.info(f"Rate limiter initialized: {max_requests} requests per {window_seconds}s")
    
    def _clean_old_requests(self):
        """Remove requests older than the time window."""
        cutoff_time = time.time() - self.window_seconds
        
        # Remove old timestamps from the left of deque
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()
    
    def get_remaining_requests(self) -> int:
        """
        Get number of remaining requests available in current window.
        
        Returns:
            Number of requests remaining
        """
        self._clean_old_requests()
        remaining = self.max_requests - len(self.requests)
        return max(0, remaining)
    
    def get_wait_time(self) -> float:
        """
        Get time to wait (in seconds) before next request is allowed.
        
        Returns:
            Seconds to wait (0 if request can be made immediately)
        """
        self._clean_old_requests()
        
        if len(self.requests) < self.max_requests:
            return 0.0
        
        # Need to wait until oldest request expires
        oldest_request = self.requests[0]
        wait_time = (oldest_request + self.window_seconds) - time.time()
        return max(0.0, wait_time)
    
    def wait_if_needed(self, show_progress: bool = False) -> None:
        """
        Block execution if rate limit is reached.

        Args:
            show_progress: Whether to show a progress bar while waiting
        """
        wait_time = self.get_wait_time()

        # Only wait if we're REALLY over the limit (not just close)
        if wait_time > 0.5:  # Only wait if need to wait more than 500ms
            logger.warning(f"Rate limit reached. Waiting {wait_time:.1f}s...")

            if show_progress:
                progress_bar = st.progress(0)
                status_text = st.empty()

                start_time = time.time()
                while time.time() - start_time < wait_time:
                    elapsed = time.time() - start_time
                    progress = elapsed / wait_time
                    remaining = wait_time - elapsed

                    progress_bar.progress(min(progress, 1.0))
                    status_text.text(f"⏳ Rate limit reached. Waiting {remaining:.1f}s...")
                    time.sleep(0.1)

                progress_bar.empty()
                status_text.empty()
            else:
                time.sleep(wait_time)
        # If wait time is small (<500ms), just skip it for speed
    
    def record_request(self) -> None:
        """Record that a request was made."""
        self.requests.append(time.time())
        logger.debug(f"Request recorded. {self.get_remaining_requests()} remaining.")
    
    def reset(self) -> None:
        """Clear all recorded requests."""
        self.requests.clear()
        logger.info("Rate limiter reset")
    
    def get_stats(self) -> dict:
        """
        Get current rate limiter statistics.
        
        Returns:
            Dictionary with stats
        """
        self._clean_old_requests()
        
        return {
            "requests_made": len(self.requests),
            "requests_remaining": self.get_remaining_requests(),
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "wait_time": self.get_wait_time(),
            "utilization_pct": (len(self.requests) / self.max_requests) * 100
        }


# Global rate limiter instance for Tiingo API
# Power Plan: 50 requests per minute
tiingo_limiter = RateLimiter(max_requests=50, window_seconds=60)


def get_tiingo_limiter() -> RateLimiter:
    """Get the global Tiingo rate limiter instance."""
    return tiingo_limiter


def show_rate_limit_status():
    """Display rate limit status in Streamlit sidebar."""
    stats = tiingo_limiter.get_stats()
    
    remaining = stats["requests_remaining"]
    total = stats["max_requests"]
    utilization = stats["utilization_pct"]
    
    # Color code based on utilization
    if utilization < 50:
        color = "🟢"
        status = "Good"
    elif utilization < 80:
        color = "🟡"
        status = "Moderate"
    else:
        color = "🔴"
        status = "High"
    
    st.sidebar.markdown(f"**API Rate Limit:** {color} {status}")
    st.sidebar.caption(f"{remaining}/{total} requests remaining")
    
    if stats["wait_time"] > 0:
        st.sidebar.warning(f"⏳ Cooldown: {stats['wait_time']:.0f}s")

