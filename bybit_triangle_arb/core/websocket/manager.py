"""
WebSocket manager for real-time market data from Bybit.
Handles connection management, subscriptions, and message processing.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, Callable, List, Set
import websockets
from ..core.models import OrderBook, OrderBookLevel


class WebSocketManager:
    """
    Asynchronous WebSocket manager for Bybit market data.
    
    Features:
    - Automatic reconnection with exponential backoff
    - Heartbeat/ping-pong monitoring
    - Multiple channel subscriptions
    - Message compression
    - Callback-based message handling
    """
    
    def __init__(self, config):
        self.config = config
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._is_connected = False
        self._subscriptions: Set[str] = set()
        self._callbacks: Dict[str, Callable] = {}
        self._order_books: Dict[str, OrderBook] = {}
        self._last_message_time: float = 0.0
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._base_reconnect_delay = 1.0
        self._running = False
        self._ping_task: Optional[asyncio.Task] = None
        self._message_task: Optional[asyncio.Task] = None
        
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._is_connected and self._ws is not None
    
    @property
    def latency_ms(self) -> float:
        """Get estimated latency in milliseconds."""
        if self._last_message_time == 0:
            return float('inf')
        return (time.time() - self._last_message_time) * 1000
    
    async def connect(self, url: str = "wss://stream.bybit.com/v5/public/spot"):
        """
        Establish WebSocket connection.
        
        Args:
            url: WebSocket endpoint URL
        """
        self._running = True
        
        while self._running and self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                await self._connect(url)
                
                # Resubscribe to channels if reconnecting
                if self._subscriptions and self._reconnect_attempts > 0:
                    await self._resubscribe()
                
                self._reconnect_attempts = 0
                self._is_connected = True
                
                # Start background tasks
                self._ping_task = asyncio.create_task(self._ping_loop())
                self._message_task = asyncio.create_task(self._message_loop())
                
                # Wait for message loop to complete
                if self._message_task:
                    await self._message_task
                    
            except Exception as e:
                self._is_connected = False
                self._reconnect_attempts += 1
                
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    raise ConnectionError(f"Max reconnection attempts reached: {e}")
                
                delay = self._base_reconnect_delay * (2 ** (self._reconnect_attempts - 1))
                await asyncio.sleep(delay)
    
    async def _connect(self, url: str):
        """Create WebSocket connection."""
        self._ws = await websockets.connect(
            url,
            ping_interval=self.config.performance.websocket_ping_interval,
            ping_timeout=10,
            close_timeout=5,
            max_size=10 * 1024 * 1024,  # 10MB max message size
        )
    
    async def disconnect(self):
        """Close WebSocket connection."""
        self._running = False
        self._is_connected = False
        
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        
        if self._message_task:
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass
        
        if self._ws:
            await self._ws.close()
            self._ws = None
    
    async def subscribe(self, channels: List[str]):
        """
        Subscribe to market data channels.
        
        Args:
            channels: List of channel names (e.g., ["orderbook.50.BTCUSDT"])
        """
        if not self.is_connected:
            raise ConnectionError("Not connected")
        
        subscribe_msg = {
            "op": "subscribe",
            "args": channels
        }
        
        await self._ws.send(json.dumps(subscribe_msg))
        self._subscriptions.update(channels)
    
    async def unsubscribe(self, channels: List[str]):
        """
        Unsubscribe from channels.
        
        Args:
            channels: List of channel names to unsubscribe
        """
        if not self.is_connected:
            return
        
        unsubscribe_msg = {
            "op": "unsubscribe",
            "args": channels
        }
        
        await self._ws.send(json.dumps(unsubscribe_msg))
        self._subscriptions.difference_update(channels)
    
    async def _resubscribe(self):
        """Resubscribe to all channels after reconnection."""
        if self._subscriptions:
            await self.subscribe(list(self._subscriptions))
    
    async def _ping_loop(self):
        """Send periodic ping messages."""
        while self._running and self.is_connected:
            try:
                await asyncio.sleep(self.config.performance.websocket_ping_interval)
                
                if self._ws:
                    pong = await asyncio.wait_for(
                        self._ws.ping(),
                        timeout=10.0
                    )
                    await asyncio.wait_for(pong, timeout=10.0)
                    
            except (asyncio.TimeoutError, Exception):
                # Connection lost, will trigger reconnect
                break
    
    async def _message_loop(self):
        """Process incoming messages."""
        while self._running and self.is_connected:
            try:
                message = await self._ws.recv()
                self._last_message_time = time.time()
                
                await self._handle_message(message)
                
            except websockets.ConnectionClosed:
                break
            except Exception as e:
                # Log error but continue
                continue
    
    async def _handle_message(self, message: str):
        """
        Process incoming WebSocket message.
        
        Args:
            message: Raw WebSocket message string
        """
        try:
            data = json.loads(message)
            
            # Handle different message types
            if "topic" in data:
                topic = data["topic"]
                
                # Call registered callback if exists
                if topic in self._callbacks:
                    await self._callbacks[topic](data)
                
                # Handle order book updates
                if topic.startswith("orderbook"):
                    await self._update_order_book(data)
            
            # Handle subscription responses
            elif data.get("op") == "subscribe":
                pass  # Subscription confirmed
            
            elif data.get("op") == "pong":
                pass  # Ping response
            
        except json.JSONDecodeError:
            pass
        except Exception as e:
            # Log error
            pass
    
    async def _update_order_book(self, data: Dict[str, Any]):
        """
        Update local order book cache.
        
        Args:
            data: Order book update data
        """
        topic = data.get("topic", "")
        
        # Extract symbol from topic (e.g., "orderbook.50.BTCUSDT" -> "BTCUSDT")
        parts = topic.split(".")
        if len(parts) < 3:
            return
        
        symbol = parts[-1]
        ts = data.get("ts", 0)
        
        bids_data = data.get("data", {}).get("b", [])
        asks_data = data.get("data", {}).get("a", [])
        
        # Create or update order book
        if symbol not in self._order_books:
            self._order_books[symbol] = OrderBook(symbol=symbol)
        
        order_book = self._order_books[symbol]
        
        # Update bids
        if bids_data:
            order_book.bids = [
                OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
                for b in bids_data
            ]
        
        # Update asks
        if asks_data:
            order_book.asks = [
                OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
                for a in asks_data
            ]
        
        order_book.timestamp = datetime.fromtimestamp(ts / 1000)
        order_book.sequence = data.get("data", {}).get("seq", 0)
    
    def register_callback(self, topic: str, callback: Callable):
        """
        Register callback for a specific topic.
        
        Args:
            topic: Channel topic to listen to
            callback: Async function to call when message received
        """
        self._callbacks[topic] = callback
    
    def get_order_book(self, symbol: str) -> Optional[OrderBook]:
        """
        Get cached order book for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            OrderBook object or None if not available
        """
        return self._order_books.get(symbol)
    
    def get_best_bid(self, symbol: str) -> Optional[float]:
        """Get best bid price for symbol."""
        ob = self.get_order_book(symbol)
        return ob.best_bid if ob else None
    
    def get_best_ask(self, symbol: str) -> Optional[float]:
        """Get best ask price for symbol."""
        ob = self.get_order_book(symbol)
        return ob.best_ask if ob else None
    
    def get_mid_price(self, symbol: str) -> Optional[float]:
        """Get mid price for symbol."""
        ob = self.get_order_book(symbol)
        return ob.mid_price if ob else None
