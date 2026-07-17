"""
Bybit REST API client for market data and trading operations.
Handles authentication, rate limiting, and error recovery.
"""

import asyncio
import hashlib
import hmac
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
import aiohttp
from ..config.settings import APIConfig
from ..core.models import Symbol, Order, OrderSide, OrderType, OrderStatus


class BybitAPIError(Exception):
    """Custom exception for Bybit API errors."""
    
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
    Asynchronous Bybit API client.
    
    Features:
    - Automatic authentication signing
    - Rate limit handling with retry logic
    - Connection pooling
    - Error handling and logging
    """
    
    def __init__(self, config: APIConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._recv_window = 5000
        self._rate_limit_delay = 0.1  # 100ms between requests
        self._last_request_time = 0.0
        
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self):
        """Establish HTTP session with connection pooling."""
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=30)
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
    
    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    def _generate_signature(self, params: Dict[str, Any], timestamp: int) -> str:
        """Generate HMAC SHA256 signature for API request."""
        param_str = f"{timestamp}{self.config.api_key}{self._recv_window}"
        
        # Sort parameters and append to signature string
        for key in sorted(params.keys()):
            param_str += f"{key}={params[key]}"
        
        signature = hmac.new(
            self.config.secret_key.encode('utf-8'),
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
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Bybit API.
        
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
        if not self._session:
            raise BybitAPIError("Client not connected. Call connect() first.")
        
        url = f"{self.config.base_url}{endpoint}"
        
        for attempt in range(retry_count):
            try:
                # Rate limiting
                current_time = time.time()
                elapsed = current_time - self._last_request_time
                if elapsed < self._rate_limit_delay:
                    await asyncio.sleep(self._rate_limit_delay - elapsed)
                
                self._last_request_time = time.time()
                
                # Prepare request
                headers = {}
                data = None
                
                if signed:
                    timestamp = int(time.time() * 1000)
                    params = params or {}
                    params["api_key"] = self.config.api_key
                    params["recv_window"] = self._recv_window
                    params["timestamp"] = timestamp
                    params["sign"] = self._generate_signature(params, timestamp)
                
                if method == "GET":
                    if params:
                        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
                else:
                    data = params
                
                # Execute request
                async with self._session.request(method, url, json=data) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        error_msg = result.get("retMsg", "Unknown error")
                        if response.status == 429:
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
                    if result.get("retCode", 0) != 0:
                        error_msg = result.get("retMsg", "Unknown error")
                        raise BybitAPIError(
                            f"Bybit error: {error_msg}",
                            status_code=response.status,
                            response=result
                        )
                    
                    return result.get("result", {})
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == retry_count - 1:
                    raise BybitAPIError(f"Request failed after {retry_count} attempts: {str(e)}")
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
        
        raise BybitAPIError("Unexpected error in request loop")
    
    async def get_server_time(self) -> datetime:
        """Get server time from Bybit."""
        result = await self._request("GET", "/v5/market/time")
        timestamp = int(result.get("timeSecond", 0)) * 1000
        return datetime.fromtimestamp(timestamp / 1000)
    
    async def get_symbols(self) -> List[Symbol]:
        """
        Get all available spot symbols.
        
        Returns:
            List of Symbol objects
        """
        result = await self._request("GET", "/v5/market/instruments-info", 
                                     {"category": "spot"})
        
        symbols = []
        for item in result.get("list", []):
            if item.get("status") != "Trading":
                continue
            
            try:
                symbol = Symbol(
                    symbol=item["symbol"],
                    base_asset=item["baseCoin"],
                    quote_asset=item["quoteCoin"],
                    tick_size=float(item["tickSize"]),
                    lot_size=float(item["lotSize"]),
                    min_order_qty=float(item["minOrderQty"]),
                    max_order_qty=float(item["maxOrderQty"]),
                    price_precision=self._get_precision(item["tickSize"]),
                    qty_precision=self._get_precision(item["lotSize"]),
                    is_active=True,
                )
                symbols.append(symbol)
            except (KeyError, ValueError) as e:
                # Skip malformed symbols
                continue
        
        return symbols
    
    def _get_precision(self, value: str) -> int:
        """Calculate precision from tick/lot size string."""
        try:
            float_val = float(value)
            if float_val == 0:
                return 0
            # Count decimal places
            str_val = str(float_val)
            if '.' in str_val:
                return len(str_val.split('.')[1].rstrip('0'))
            return 0
        except (ValueError, TypeError):
            return 0
    
    async def get_orderbook(self, symbol: str, limit: int = 25) -> Dict[str, Any]:
        """
        Get order book for a symbol.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of levels (1, 25, 50, 100, 500)
            
        Returns:
            Order book data with bids and asks
        """
        result = await self._request(
            "GET", 
            "/v5/market/orderbook",
            {"category": "spot", "symbol": symbol, "limit": limit}
        )
        return result
    
    async def get_tickers(self, category: str = "spot") -> List[Dict[str, Any]]:
        """Get tickers for all symbols."""
        result = await self._request("GET", "/v5/market/tickers", {"category": category})
        return result.get("list", [])
    
    async def get_balance(self, account_type: str = "UNIFIED") -> Dict[str, Any]:
        """
        Get account balance.
        
        Args:
            account_type: Account type (UNIFIED, CONTRACT, SPOT)
            
        Returns:
            Balance information
        """
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
        time_in_force: str = "GTC"
    ) -> Order:
        """
        Place a new order.
        
        Args:
            symbol: Trading pair
            side: Buy or Sell
            order_type: Market or Limit
            qty: Order quantity
            price: Limit price (required for limit orders)
            time_in_force: Time in force (GTC, IOC, FOK)
            
        Returns:
            Order object with order ID
        """
        params = {
            "category": "spot",
            "symbol": symbol,
            "side": side.value,
            "orderType": order_type.value,
            "qty": str(qty),
            "timeInForce": time_in_force,
        }
        
        if order_type == OrderType.LIMIT and price:
            params["price"] = str(price)
        
        result = await self._request("POST", "/v5/order/create", params, signed=True)
        
        return Order(
            order_id=result.get("orderId", ""),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=qty,
            price=price,
            status=OrderStatus.SUBMITTED,
        )
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an existing order.
        
        Args:
            symbol: Trading pair
            order_id: Order ID to cancel
            
        Returns:
            True if successful
        """
        params = {
            "category": "spot",
            "symbol": symbol,
            "orderId": order_id,
        }
        
        await self._request("POST", "/v5/order/cancel", params, signed=True)
        return True
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Get order status.
        
        Args:
            symbol: Trading pair
            order_id: Order ID
            
        Returns:
            Order status information
        """
        params = {
            "category": "spot",
            "symbol": symbol,
            "orderId": order_id,
        }
        
        result = await self._request("GET", "/v5/order/realtime", params, signed=True)
        orders = result.get("list", [])
        return orders[0] if orders else {}
    
    async def get_trade_history(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Get recent trade history.
        
        Args:
            symbol: Filter by symbol (optional)
            limit: Number of records
            
        Returns:
            List of trade records
        """
        params = {
            "category": "spot",
            "limit": limit,
        }
        
        if symbol:
            params["symbol"] = symbol
        
        result = await self._request("GET", "/v5/execution/list", params, signed=True)
        return result.get("list", [])
