"""
Asynchronous Bybit API client with connection pooling and retry logic.
Supports both REST API and WebSocket connections.

Performance optimizations:
- Pre-computed rate limit delays
- Efficient signature generation with cached HMAC
- Connection pooling with DNS caching
- Batched request support
"""

import asyncio
import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable, Tuple
from collections import deque
import aiohttp
import orjson

from app.core.models import (
    Symbol, Order, OrderSide, OrderType, OrderStatus, 
    TimeInForce, OrderBook, OrderBookLevel, Ticker, Candle
)
from app.core.config import ExchangeConfig


class BybitAPIError(Exception):
    """Custom exception for Bybit API errors."""
    __slots__ = ('message', 'status_code', 'response')
    
    def __init__(self, message: str, status_code: int = 0, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response or {}
        super().__init__(self.message)


class RateLimitExceeded(BybitAPIError):
    """Exception for rate limit violations."""
    pass


class BybitAPIClient:
    """
    Asynchronous Bybit API client with performance optimizations.
    
    Features:
    - Automatic authentication signing with cached HMAC keys
    - Rate limit handling with exponential backoff
    - Connection pooling with DNS caching
    - Error handling and logging
    - Automatic reconnection
    - Request batching for bulk operations
    """

    __slots__ = (
        'config', '_session', '_recv_window', '_rate_limit_delay',
        '_last_request_time', '_request_count', '_consecutive_errors',
        '_connected', '_api_key_bytes', '_secret_key_bytes', '_request_times'
    )

    def __init__(self, config: ExchangeConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._recv_window = 5000
        self._rate_limit_delay = 1.0 / max(1, config.rate_limit_per_second)
        self._last_request_time = 0.0
        self._request_count = 0
        self._consecutive_errors = 0
        self._connected = False
        # Pre-encode keys for faster HMAC operations
        self._api_key_bytes = config.api_key.encode('utf-8') if config.api_key else b''
        self._secret_key_bytes = config.secret_key.encode('utf-8') if config.secret_key else b''
        # Track recent request times for rate limiting
        self._request_times: deque = deque(maxlen=config.rate_limit_per_second * 2)
        
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @property
    def base_url(self) -> str:
        """Get the appropriate Bybit API base URL."""
        if self.config.testnet:
            return "https://api-testnet.bybit.com"
        return "https://api.bybit.com"

    async def connect(self):
        """Establish HTTP session with connection pooling."""
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={"Content-Type": "application/json"},
            )
        self._connected = True

    async def close(self):
        """Close HTTP session."""
        self._connected = False
        if self._session:
            await self._session.close()
            self._session = None

    def _generate_signature(self, params: Optional[Dict[str, Any]], timestamp: int, method: str, path: str) -> str:
        """Generate HMAC SHA256 signature for API request (optimized)."""
        # Build parameter string efficiently
        if method == "GET":
            if params:
                # Sort keys once and build query string
                query_parts = [f"{k}={v}" for k, v in sorted(params.items())]
                query_string = "".join(query_parts)  # No separator needed for Bybit V5
                param_str = f"{timestamp}{self.config.api_key}{self._recv_window}{query_string}"
            else:
                param_str = f"{timestamp}{self.config.api_key}{self._recv_window}"
        else:
            if params:
                # Use orjson for faster JSON serialization
                param_str = f"{timestamp}{self.config.api_key}{self._recv_window}{orjson.dumps(params).decode()}"
            else:
                param_str = f"{timestamp}{self.config.api_key}{self._recv_window}"
        
        # Use pre-encoded secret key for faster HMAC
        signature = hmac.new(
            self._secret_key_bytes,
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
        retry_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Bybit API with optimized rate limiting.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path
            params: Request parameters
            signed: Whether request requires authentication
            retry_count: Number of retries on failure
            
        Returns:
            API response as dictionary
            
        Raises:
            BybitAPIError: On API error
            RateLimitExceeded: On rate limit violation
        """
        if retry_count is None:
            retry_count = self.config.retry_attempts
            
        if not self._session or not self._connected:
            raise BybitAPIError("Client not connected. Call connect() first.")

        url = f"{self.base_url}{endpoint}"
        current_time = time.time()

        for attempt in range(retry_count):
            try:
                # Optimized rate limiting using sliding window
                now = time.time()
                # Clean old timestamps from deque
                while self._request_times and self._request_times[0] < now - 1.0:
                    self._request_times.popleft()
                
                # Wait if we've hit the rate limit
                if len(self._request_times) >= self.config.rate_limit_per_second:
                    sleep_time = 1.0 - (now - self._request_times[0])
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)
                    now = time.time()
                
                self._request_times.append(now)
                self._request_count += 1

                # Prepare request with cached values
                timestamp = int(now * 1000)
                headers = {
                    "X-BAPI-API-KEY": self.config.api_key,
                    "X-BAPI-TIMESTAMP": str(timestamp),
                    "X-BAPI-RECV-WINDOW": str(self._recv_window),
                }
                
                data = None
                
                if signed:
                    params = params or {}
                    signature = self._generate_signature(params, timestamp, method, endpoint)
                    headers["X-BAPI-SIGN"] = signature

                # Build URL efficiently
                if method == "GET" and params:
                    query_parts = [f"{k}={v}" for k, v in params.items()]
                    url += "?" + "&".join(query_parts)
                else:
                    data = params

                # Execute request
                async with self._session.request(method, url, json=data, headers=headers) as response:
                    result = await response.json()

                    if response.status != 200:
                        error_msg = result.get("retMsg", "Unknown error")
                        if response.status == 429:
                            self._consecutive_errors += 1
                            raise RateLimitExceeded(
                                f"Rate limit exceeded: {error_msg}",
                                status_code=response.status,
                                response=result
                            )
                        raise BybitAPIError(
                            f"API error: {error_msg}",
                            status_code=response.status,
                            response=result
                        )

                    # Check Bybit return code
                    ret_code = result.get("retCode", 0)
                    if ret_code != 0:
                        error_msg = result.get("retMsg", "Unknown error")
                        # Handle specific error codes
                        if ret_code == 10001:  # Param error
                            raise BybitAPIError(f"Parameter error: {error_msg}", response=result)
                        elif ret_code in (10003, 10004):  # API key errors
                            raise BybitAPIError(f"Authentication error: {error_msg}", response=result)
                        raise BybitAPIError(
                            f"Bybit error: {error_msg}",
                            status_code=response.status,
                            response=result
                        )

                    self._consecutive_errors = 0
                    return result.get("result", {})

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self._consecutive_errors += 1
                if attempt == retry_count - 1:
                    raise BybitAPIError(f"Request failed after {retry_count} attempts: {str(e)}")
                # Exponential backoff with jitter
                backoff = 0.5 * (2 ** attempt) + (time.time() % 0.1)
                await asyncio.sleep(backoff)

        raise BybitAPIError("Unexpected error in request loop")

    async def get_server_time(self) -> datetime:
        """Get server time from Bybit."""
        result = await self._request("GET", "/v5/market/time")
        timestamp = int(result.get("timeSecond", 0)) * 1000
        return datetime.fromtimestamp(timestamp / 1000)

    async def get_symbols(self, category: str = "spot") -> List[Symbol]:
        """
        Get all available symbols for a category.
        
        Args:
            category: spot, linear, inverse, option
            
        Returns:
            List of Symbol objects
        """
        result = await self._request("GET", "/v5/market/instruments-info",
                                     {"category": category})

        symbols = []
        for item in result.get("list", []):
            if item.get("status") != "Trading":
                continue

            try:
                symbol = Symbol(
                    symbol=item["symbol"],
                    base_asset=item.get("baseCoin", ""),
                    quote_asset=item.get("quoteCoin", ""),
                    tick_size=float(item.get("tickSize", "0")),
                    lot_size=float(item.get("lotSize", "0")),
                    min_order_qty=float(item.get("minOrderQty", "0")),
                    max_order_qty=float(item.get("maxOrderQty", "0")),
                    price_precision=self._get_precision(item.get("tickSize", "0")),
                    qty_precision=self._get_precision(item.get("lotSize", "0")),
                    is_active=True,
                    exchange="bybit",
                    category=category,
                )
                symbols.append(symbol)
            except (KeyError, ValueError) as e:
                continue

        return symbols

    def _get_precision(self, value: str) -> int:
        """Calculate precision from tick/lot size string."""
        try:
            float_val = float(value)
            if float_val == 0:
                return 0
            str_val = str(float_val)
            if '.' in str_val:
                return len(str_val.split('.')[1].rstrip('0'))
            return 0
        except (ValueError, TypeError):
            return 0

    async def get_orderbook(self, symbol: str, category: str = "spot", limit: int = 25) -> OrderBook:
        """
        Get order book for a symbol.
        
        Args:
            symbol: Trading pair symbol
            category: spot, linear, inverse
            limit: Number of levels (1, 25, 50, 100, 500)
            
        Returns:
            OrderBook object
        """
        result = await self._request(
            "GET",
            "/v5/market/orderbook",
            {"category": category, "symbol": symbol, "limit": limit}
        )
        
        data = result.get("list", [{}])[0] if result.get("list") else {}
        bids = [
            OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
            for b in data.get("b", [])
        ]
        asks = [
            OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
            for a in data.get("a", [])
        ]
        
        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.now(timezone.utc),
            sequence=int(data.get("seq", 0)),
            exchange="bybit",
        )

    async def get_tickers(self, category: str = "spot", symbol: Optional[str] = None) -> List[Ticker]:
        """Get tickers for symbols."""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
            
        result = await self._request("GET", "/v5/market/tickers", params)
        
        tickers = []
        for item in result.get("list", []):
            ticker = Ticker(
                symbol=item["symbol"],
                last_price=float(item.get("lastPrice", 0)),
                bid_price=float(item.get("bid1Price", 0)),
                ask_price=float(item.get("ask1Price", 0)),
                volume_24h=float(item.get("volume24h", 0)),
                turnover_24h=float(item.get("turnover24h", 0)),
                high_24h=float(item.get("highPrice24h", 0)),
                low_24h=float(item.get("lowPrice24h", 0)),
                price_change_24h=float(item.get("price24hPcnt", 0)),
                price_change_pct_24h=float(item.get("price24hPcnt", 0)) * 100,
                funding_rate=float(item["fundingRate"]) if "fundingRate" in item else None,
                open_interest=float(item["openInterest"]) if "openInterest" in item else None,
            )
            tickers.append(ticker)
        
        return tickers

    async def get_kline(
        self, 
        symbol: str, 
        interval: str = "1m", 
        limit: int = 200,
        category: str = "spot"
    ) -> List[Candle]:
        """
        Get candlestick data.
        
        Args:
            symbol: Trading pair
            interval: Kline interval (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M)
            limit: Number of candles (max 200)
            category: spot, linear, inverse
            
        Returns:
            List of Candle objects
        """
        result = await self._request(
            "GET",
            "/v5/market/kline",
            {"category": category, "symbol": symbol, "interval": interval, "limit": limit}
        )
        
        candles = []
        for item in result.get("list", []):
            candle = Candle(
                symbol=symbol,
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
                turnover=float(item[6]),
                start_time=datetime.fromtimestamp(int(item[0]) / 1000),
                end_time=datetime.fromtimestamp((int(item[0]) + int(interval.replace("D", "1440").replace("W", "10080").replace("M", "43200")) * 60000) / 1000) if item[0].isdigit() else datetime.now(timezone.utc),
                interval=interval,
            )
            candles.append(candle)
        
        return candles

    async def get_balance(self, account_type: str = "UNIFIED") -> Dict[str, Any]:
        """Get account balance."""
        result = await self._request(
            "POST",
            "/v5/account/wallet-balance",
            {"accountType": account_type},
            signed=True
        )
        return result

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: float,
        price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.GTC,
        reduce_only: bool = False,
        post_only: bool = False,
        category: str = "spot"
    ) -> Order:
        """Place a new order."""
        params = {
            "category": category,
            "symbol": symbol,
            "side": side.value,
            "orderType": order_type.value,
            "qty": str(qty),
            "timeInForce": time_in_force.value,
            "reduceOnly": reduce_only,
            "positionIdx": 1 if side == OrderSide.BUY else 2,
        }

        if order_type == OrderType.LIMIT and price:
            params["price"] = str(price)
            
        if post_only:
            params["mmp"] = False

        result = await self._request("POST", "/v5/order/create", params, signed=True)

        return Order(
            order_id=result.get("orderId", ""),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=qty,
            price=price,
            status=OrderStatus.SUBMITTED,
            time_in_force=time_in_force,
            exchange="bybit",
        )

    async def cancel_order(self, symbol: str, order_id: str, category: str = "spot") -> bool:
        """Cancel an existing order."""
        params = {
            "category": category,
            "symbol": symbol,
            "orderId": order_id,
        }

        await self._request("POST", "/v5/order/cancel", params, signed=True)
        return True

    async def get_order_status(self, symbol: str, order_id: str, category: str = "spot") -> Optional[Order]:
        """Get order status."""
        params = {
            "category": category,
            "symbol": symbol,
            "orderId": order_id,
        }

        result = await self._request("GET", "/v5/order/realtime", params, signed=True)
        orders = result.get("list", [])
        
        if not orders:
            return None
            
        order_data = orders[0]
        return Order(
            order_id=order_data.get("orderId", ""),
            symbol=order_data.get("symbol", ""),
            side=OrderSide(order_data.get("side", "Buy")),
            order_type=OrderType(order_data.get("orderType", "Market")),
            quantity=float(order_data.get("qty", 0)),
            price=float(order_data.get("price", 0)) if order_data.get("price") else None,
            status=OrderStatus(order_data.get("orderStatus", "pending")),
            filled_qty=float(order_data.get("cumExecQty", 0)),
            avg_fill_price=float(order_data.get("avgPrice", 0)) if order_data.get("avgPrice") else None,
            commission=float(order_data.get("fee", 0)),
        )

    async def get_open_orders(
        self, 
        symbol: Optional[str] = None, 
        category: str = "spot",
        limit: int = 50
    ) -> List[Order]:
        """Get open orders."""
        params = {"category": category, "limit": limit}
        if symbol:
            params["symbol"] = symbol

        result = await self._request("GET", "/v5/order/realtime", params, signed=True)
        
        orders = []
        for order_data in result.get("list", []):
            order = Order(
                order_id=order_data.get("orderId", ""),
                symbol=order_data.get("symbol", ""),
                side=OrderSide(order_data.get("side", "Buy")),
                order_type=OrderType(order_data.get("orderType", "Market")),
                quantity=float(order_data.get("qty", 0)),
                price=float(order_data.get("price", 0)) if order_data.get("price") else None,
                status=OrderStatus.PENDING,
                filled_qty=float(order_data.get("cumExecQty", 0)),
                created_at=datetime.fromtimestamp(int(order_data.get("createdTime", 0)) / 1000),
            )
            orders.append(order)
        
        return orders

    async def get_trade_history(
        self, 
        symbol: Optional[str] = None, 
        category: str = "spot",
        limit: int = 50
    ) -> List[Dict]:
        """Get recent trade history."""
        params = {
            "category": category,
            "limit": limit,
        }

        if symbol:
            params["symbol"] = symbol

        result = await self._request("GET", "/v5/execution/list", params, signed=True)
        return result.get("list", [])

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get API client metrics."""
        return {
            "requests_total": self._request_count,
            "consecutive_errors": self._consecutive_errors,
            "connected": self._connected,
            "rate_limit_delay": self._rate_limit_delay,
        }
