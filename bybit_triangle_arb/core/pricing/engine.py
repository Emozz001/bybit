"""
Pricing engine for calculating arbitrage profitability.
Analyzes fees, slippage, spread, and liquidity to determine net profit.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from ..core.models import (
    Triangle, Opportunity, OrderBook, OrderSide, 
    Symbol, LatencyMetrics
)


class PricingEngine:
    """
    Calculates profitability of triangular arbitrage opportunities.
    
    Features:
    - Fee calculation (maker/taker)
    - Slippage estimation
    - Spread analysis
    - Liquidity scoring
    - Confidence scoring
    - Dynamic position sizing
    """
    
    # Bybit spot fee structure (can be updated for VIP tiers)
    MAKER_FEE_RATE = 0.001  # 0.1%
    TAKER_FEE_RATE = 0.001  # 0.1%
    
    def __init__(self, config):
        self.config = config
        self._symbol_info: Dict[str, Symbol] = {}
        
    def update_symbols(self, symbols: List[Symbol]):
        """Update symbol information."""
        self._symbol_info = {s.symbol: s for s in symbols}
    
    def calculate_opportunity(
        self,
        triangle: Triangle,
        order_books: Dict[str, OrderBook],
        trade_amount_usdt: Optional[float] = None
    ) -> Optional[Opportunity]:
        """
        Calculate profitability of a triangle.
        
        Args:
            triangle: Triangle to analyze
            order_books: Current order books for all legs
            trade_amount_usdt: Trade amount in USDT (optional)
            
        Returns:
            Opportunity object or None if not viable
        """
        # Get order books for all legs
        ob1 = order_books.get(triangle.leg1_symbol)
        ob2 = order_books.get(triangle.leg2_symbol)
        ob3 = order_books.get(triangle.leg3_symbol)
        
        if not all([ob1, ob2, ob3]):
            return None
        
        # Check if order books are fresh (< 5 seconds old)
        now = datetime.utcnow()
        max_age_seconds = 5
        
        for ob in [ob1, ob2, ob3]:
            age = (now - ob.timestamp).total_seconds()
            if age > max_age_seconds:
                return None
        
        # Determine trade amounts for each leg
        if trade_amount_usdt is None:
            trade_amount_usdt = self._calculate_optimal_amount(
                triangle, [ob1, ob2, ob3]
            )
        
        # Calculate each leg
        leg1_result = self._calculate_leg(
            triangle.leg1_symbol,
            triangle.leg1_side,
            ob1,
            trade_amount_usdt
        )
        
        if not leg1_result:
            return None
        
        # Leg 2 uses output from leg 1
        leg2_input = leg1_result["output_amount"]
        leg2_result = self._calculate_leg(
            triangle.leg2_symbol,
            triangle.leg2_side,
            ob2,
            leg2_input,
            is_intermediate=True
        )
        
        if not leg2_result:
            return None
        
        # Leg 3 should return to starting asset
        leg3_input = leg2_result["output_amount"]
        leg3_result = self._calculate_leg(
            triangle.leg3_symbol,
            triangle.leg3_side,
            ob3,
            leg3_input,
            is_final=True
        )
        
        if not leg3_result:
            return None
        
        # Calculate totals
        final_amount = leg3_result["output_amount"]
        total_fees = (
            leg1_result["fee"] + 
            leg2_result["fee"] + 
            leg3_result["fee"]
        )
        
        gross_profit = final_amount - trade_amount_usdt
        net_profit = gross_profit - total_fees
        
        gross_profit_pct = (gross_profit / trade_amount_usdt) * 100
        net_profit_pct = (net_profit / trade_amount_usdt) * 100
        
        # Calculate slippage and spread estimates
        total_slippage = (
            leg1_result["slippage"] +
            leg2_result["slippage"] +
            leg3_result["slippage"]
        )
        
        avg_spread = (
            (ob1.spread_pct or 0) +
            (ob2.spread_pct or 0) +
            (ob3.spread_pct or 0)
        ) / 3
        
        # Calculate liquidity score
        liquidity_score = self._calculate_liquidity_score(
            [ob1, ob2, ob3],
            [leg1_result, leg2_result, leg3_result]
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            net_profit_pct,
            liquidity_score,
            total_slippage,
            avg_spread,
            total_fees
        )
        
        # Create opportunity
        opportunity = Opportunity(
            triangle=triangle,
            gross_profit_pct=gross_profit_pct,
            net_profit_pct=net_profit_pct,
            trade_amount_usdt=trade_amount_usdt,
            expected_profit_usdt=net_profit,
            confidence_score=confidence_score,
            liquidity_score=liquidity_score,
            slippage_estimate=total_slippage,
            spread_estimate=avg_spread,
            fees_estimate=total_fees,
            legs_data=[leg1_result, leg2_result, leg3_result]
        )
        
        return opportunity
    
    def _calculate_leg(
        self,
        symbol: str,
        side: OrderSide,
        order_book: OrderBook,
        amount: float,
        is_intermediate: bool = False,
        is_final: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate execution details for one leg of the triangle.
        
        Args:
            symbol: Trading pair
            side: Buy or Sell
            order_book: Current order book
            amount: Amount to trade
            is_intermediate: Is this an intermediate leg?
            is_final: Is this the final leg?
            
        Returns:
            Dictionary with execution details or None if invalid
        """
        sym_info = self._symbol_info.get(symbol)
        if not sym_info:
            return None
        
        # Get prices based on side
        if side == OrderSide.BUY:
            price = order_book.best_ask
            levels = order_book.asks
        else:
            price = order_book.best_bid
            levels = order_book.bids
        
        if not price or not levels:
            return None
        
        # Estimate slippage
        slippage = order_book.estimate_slippage(side, amount / price if price > 0 else 0)
        
        # Check slippage limit
        if slippage > self.config.trading.max_slippage_pct:
            return None
        
        # Check spread limit
        if order_book.spread_pct and order_book.spread_pct > self.config.trading.max_spread_pct:
            return None
        
        # Calculate output amount
        # For BUY: we spend USDT, get base asset
        # For SELL: we spend base asset, get USDT
        if side == OrderSide.BUY:
            input_amount = amount  # USDT
            output_amount = amount / price  # Base asset
        else:
            input_amount = amount  # Base asset
            output_amount = amount * price  # USDT
        
        # Calculate fee
        fee = output_amount * self.TAKER_FEE_RATE
        
        # Adjust output for fee
        output_amount -= fee
        
        return {
            "symbol": symbol,
            "side": side.value,
            "input_amount": input_amount,
            "output_amount": output_amount,
            "price": price,
            "slippage": slippage,
            "fee": fee,
            "spread_pct": order_book.spread_pct or 0,
        }
    
    def _calculate_optimal_amount(
        self,
        triangle: Triangle,
        order_books: List[OrderBook]
    ) -> float:
        """
        Calculate optimal trade amount based on liquidity.
        
        Uses the minimum liquidity across all legs to determine
        the maximum safe trade size.
        """
        min_liquidity = float('inf')
        
        for ob in order_books:
            if not ob or not ob.bids or not ob.asks:
                continue
            
            # Estimate available liquidity at top 5 levels
            bid_liquidity = sum(level.quantity for level in ob.bids[:5])
            ask_liquidity = sum(level.quantity for level in ob.asks[:5])
            
            # Use mid-price to convert to USDT equivalent
            mid_price = ob.mid_price or 1.0
            
            if mid_price > 0:
                liquidity_usdt = min(bid_liquidity, ask_liquidity) * mid_price
                min_liquidity = min(min_liquidity, liquidity_usdt)
        
        # Use 10% of available liquidity or configured limits
        if min_liquidity == float('inf'):
            return self.config.trading.min_trade_size_usdt
        
        optimal = min_liquidity * 0.1
        
        # Apply configured limits
        optimal = max(optimal, self.config.trading.min_trade_size_usdt)
        optimal = min(optimal, self.config.trading.max_trade_size_usdt)
        
        return optimal
    
    def _calculate_liquidity_score(
        self,
        order_books: List[OrderBook],
        leg_results: List[Dict[str, Any]]
    ) -> int:
        """
        Calculate liquidity score (0-100) for the opportunity.
        
        Higher score = better liquidity = lower execution risk
        """
        scores = []
        
        for ob, leg in zip(order_books, leg_results):
            if not ob:
                scores.append(0)
                continue
            
            # Factor 1: Order book depth
            depth_score = min(100, len(ob.bids) + len(ob.asks)) * 2
            
            # Factor 2: Spread
            spread = ob.spread_pct or 1.0
            spread_score = max(0, 100 - (spread * 100))
            
            # Factor 3: Slippage
            slippage = leg.get("slippage", 1.0)
            slippage_score = max(0, 100 - (slippage * 50))
            
            # Combined score for this leg
            leg_score = (depth_score + spread_score + slippage_score) / 3
            scores.append(leg_score)
        
        if not scores:
            return 0
        
        return int(sum(scores) / len(scores))
    
    def _calculate_confidence_score(
        self,
        net_profit_pct: float,
        liquidity_score: int,
        slippage: float,
        spread: float,
        fees: float
    ) -> int:
        """
        Calculate overall confidence score (0-100).
        
        Factors:
        - Profitability
        - Liquidity
        - Slippage
        - Spread
        - Market conditions
        """
        # Profit component (40% weight)
        profit_target = self.config.trading.min_net_profit_pct
        if net_profit_pct >= profit_target * 3:
            profit_score = 100
        elif net_profit_pct >= profit_target:
            profit_score = int((net_profit_pct / profit_target) * 50 + 50)
        else:
            profit_score = int((net_profit_pct / profit_target) * 50)
        
        # Liquidity component (25% weight)
        liquidity_component = liquidity_score * 0.25
        
        # Slippage component (15% weight)
        max_slippage = self.config.trading.max_slippage_pct
        if slippage <= max_slippage * 0.5:
            slippage_score = 100
        elif slippage <= max_slippage:
            slippage_score = int(100 - ((slippage - max_slippage * 0.5) / (max_slippage * 0.5)) * 50)
        else:
            slippage_score = 0
        slippage_component = slippage_score * 0.15
        
        # Spread component (10% weight)
        max_spread = self.config.trading.max_spread_pct
        if spread <= max_spread * 0.5:
            spread_score = 100
        elif spread <= max_spread:
            spread_score = int(100 - ((spread - max_spread * 0.5) / (max_spread * 0.5)) * 50)
        else:
            spread_score = 0
        spread_component = spread_score * 0.10
        
        # Fee impact component (10% weight)
        fee_ratio = fees / (net_profit_pct + fees) if (net_profit_pct + fees) > 0 else 1
        fee_score = int((1 - fee_ratio) * 100)
        fee_component = fee_score * 0.10
        
        # Total confidence score
        total_score = (
            profit_score * 0.40 +
            liquidity_component +
            slippage_component +
            spread_component +
            fee_component
        )
        
        return min(100, max(0, int(total_score)))
    
    def should_execute(self, opportunity: Opportunity) -> Tuple[bool, str]:
        """
        Determine if an opportunity should be executed.
        
        Returns:
            Tuple of (should_execute, reason)
        """
        cfg = self.config.trading
        
        if opportunity.net_profit_pct < cfg.min_net_profit_pct:
            return False, f"Profit too low: {opportunity.net_profit_pct:.3f}%"
        
        if opportunity.confidence_score < cfg.confidence_threshold:
            return False, f"Confidence too low: {opportunity.confidence_score}"
        
        if opportunity.liquidity_score < cfg.min_liquidity_score:
            return False, f"Liquidity too low: {opportunity.liquidity_score}"
        
        if opportunity.slippage_estimate > cfg.max_slippage_pct:
            return False, f"Slippage too high: {opportunity.slippage_estimate:.3f}%"
        
        if opportunity.spread_estimate > cfg.max_spread_pct:
            return False, f"Spread too high: {opportunity.spread_estimate:.3f}%"
        
        return True, "All checks passed"
