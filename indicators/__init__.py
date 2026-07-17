"""
Technical Indicators Module
Common technical indicators for trading strategies.
"""

from typing import List, Dict, Any, Optional
import numpy as np


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """
    Calculate Exponential Moving Average.
    
    Args:
        prices: List of prices (close prices typically)
        period: EMA period
        
    Returns:
        List of EMA values
    """
    if len(prices) < period or period <= 0:
        return []
    
    ema = []
    multiplier = 2 / (period + 1)
    
    # Start with SMA for first EMA value
    sma = sum(prices[:period]) / period
    ema.append(sma)
    
    # Calculate EMA for remaining prices
    for i in range(period, len(prices)):
        ema_value = (prices[i] - ema[-1]) * multiplier + ema[-1]
        ema.append(ema_value)
    
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """
    Calculate Relative Strength Index.
    
    Args:
        prices: List of prices
        period: RSI period (default 14)
        
    Returns:
        List of RSI values (0-100)
    """
    if len(prices) < period + 1:
        return []
    
    rsi_values = []
    gains = []
    losses = []
    
    # Calculate price changes
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
    
    # First average gain/loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Calculate RSI for remaining periods
    for i in range(period, len(gains)):
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rsi_values.append(rsi)
        
        # Update averages (Wilder's smoothing)
        if i < len(gains) - 1:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    return rsi_values


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, 
                   signal: int = 9) -> Dict[str, List[float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: List of prices
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line EMA period (default 9)
        
    Returns:
        Dictionary with 'macd', 'signal', and 'histogram' lists
    """
    if len(prices) < slow + signal:
        return {'macd': [], 'signal': [], 'histogram': []}
    
    # Calculate EMAs
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    # Align EMAs (slow EMA starts later)
    offset = slow - fast
    macd_line = []
    for i in range(len(ema_slow)):
        macd_line.append(ema_fast[i + offset] - ema_slow[i])
    
    # Calculate signal line (EMA of MACD)
    signal_line = calculate_ema(macd_line, signal)
    
    # Calculate histogram
    histogram = []
    for i in range(len(signal_line)):
        histogram.append(macd_line[i + len(macd_line) - len(signal_line)] - signal_line[i])
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }


def calculate_bollinger_bands(prices: List[float], period: int = 20, 
                              std_dev: float = 2.0) -> Dict[str, List[float]]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: List of prices
        period: SMA period (default 20)
        std_dev: Standard deviation multiplier (default 2)
        
    Returns:
        Dictionary with 'upper', 'middle', 'lower' lists
    """
    if len(prices) < period:
        return {'upper': [], 'middle': [], 'lower': []}
    
    middle = []
    upper = []
    lower = []
    
    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1:i + 1]
        sma = sum(window) / period
        
        # Calculate standard deviation
        variance = sum((x - sma) ** 2 for x in window) / period
        std = np.sqrt(variance)
        
        middle.append(sma)
        upper.append(sma + (std_dev * std))
        lower.append(sma - (std_dev * std))
    
    return {
        'upper': upper,
        'middle': middle,
        'lower': lower
    }


def calculate_atr(candles: List[Dict[str, float]], period: int = 14) -> List[float]:
    """
    Calculate Average True Range.
    
    Args:
        candles: List of candle dictionaries with 'high', 'low', 'close'
        period: ATR period (default 14)
        
    Returns:
        List of ATR values
    """
    if len(candles) < period + 1:
        return []
    
    true_ranges = []
    
    # Calculate True Range for each candle
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i-1]['close']
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        true_range = max(tr1, tr2, tr3)
        true_ranges.append(true_range)
    
    # Calculate ATR using Wilder's smoothing
    atr_values = []
    atr = sum(true_ranges[:period]) / period
    atr_values.append(atr)
    
    for i in range(period, len(true_ranges)):
        atr = (atr * (period - 1) + true_ranges[i]) / period
        atr_values.append(atr)
    
    return atr_values


def calculate_adx(candles: List[Dict[str, float]], period: int = 14) -> List[float]:
    """
    Calculate Average Directional Index (simplified).
    
    Args:
        candles: List of candle dictionaries
        period: ADX period (default 14)
        
    Returns:
        List of ADX values
    """
    if len(candles) < period * 2:
        return []
    
    # This is a simplified implementation
    # Full ADX requires +DI and -DI calculations
    adx_values = []
    
    for i in range(period * 2 - 1, len(candles)):
        # Simplified: use price movement strength as proxy
        window = candles[i - period + 1:i + 1]
        moves = []
        
        for j in range(1, len(window)):
            move = abs(window[j]['high'] - window[j-1]['high']) + \
                   abs(window[j]['low'] - window[j-1]['low'])
            moves.append(move)
        
        avg_move = sum(moves) / len(moves) if moves else 0
        adx = min(100, avg_move * 10)  # Normalize to 0-100
        adx_values.append(adx)
    
    return adx_values


def calculate_volume_profile(candles: List[Dict[str, float]], 
                            levels: int = 10) -> Dict[str, Any]:
    """
    Calculate volume profile (price levels with highest volume).
    
    Args:
        candles: List of candle dictionaries
        levels: Number of volume levels to identify
        
    Returns:
        Dictionary with volume profile data
    """
    if not candles:
        return {'levels': [], 'poc': 0, 'vah': 0, 'val': 0}
    
    # Find price range
    min_price = min(c['low'] for c in candles)
    max_price = max(c['high'] for c in candles)
    
    if min_price == max_price:
        return {'levels': [], 'poc': min_price, 'vah': min_price, 'val': min_price}
    
    # Create price buckets
    bucket_size = (max_price - min_price) / levels
    volume_by_level = {}
    
    for candle in candles:
        avg_price = (candle['high'] + candle['low']) / 2
        bucket = int((avg_price - min_price) / bucket_size)
        bucket = max(0, min(levels - 1, bucket))
        
        if bucket not in volume_by_level:
            volume_by_level[bucket] = 0
        volume_by_level[bucket] += candle['volume']
    
    # Find Point of Control (POC) - price level with highest volume
    poc_bucket = max(volume_by_level.keys(), key=lambda k: volume_by_level[k])
    poc_price = min_price + (poc_bucket * bucket_size) + (bucket_size / 2)
    
    # Sort levels by volume
    sorted_levels = sorted(volume_by_level.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'levels': [min_price + (k * bucket_size) for k, v in sorted_levels],
        'volumes': [v for k, v in sorted_levels],
        'poc': poc_price,
    }


def calculate_vwap(candles: List[Dict[str, float]]) -> List[float]:
    """
    Calculate Volume Weighted Average Price.
    
    Args:
        candles: List of candle dictionaries
        
    Returns:
        List of VWAP values
    """
    if not candles:
        return []
    
    vwap_values = []
    cumulative_volume = 0
    cumulative_pv = 0  # Price * Volume
    
    for candle in candles:
        typical_price = (candle['high'] + candle['low'] + candle['close']) / 3
        volume = candle['volume']
        
        cumulative_volume += volume
        cumulative_pv += typical_price * volume
        
        if cumulative_volume > 0:
            vwap = cumulative_pv / cumulative_volume
            vwap_values.append(vwap)
        else:
            vwap_values.append(typical_price)
    
    return vwap_values


def get_all_indicators(candles: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Calculate all common indicators for a list of candles.
    
    Args:
        candles: List of candle dictionaries
        
    Returns:
        Dictionary with all indicator values
    """
    if len(candles) < 30:
        return {}
    
    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    volumes = [c['volume'] for c in candles]
    
    return {
        'ema_9': calculate_ema(closes, 9),
        'ema_21': calculate_ema(closes, 21),
        'ema_50': calculate_ema(closes, 50),
        'rsi_14': calculate_rsi(closes, 14),
        'macd': calculate_macd(closes),
        'bollinger': calculate_bollinger_bands(closes),
        'atr_14': calculate_atr(candles, 14),
        'adx_14': calculate_adx(candles, 14),
        'vwap': calculate_vwap(candles),
        'avg_volume': sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes),
        'volume': volumes,
    }
