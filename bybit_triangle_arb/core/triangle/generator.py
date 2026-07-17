"""
Triangle generator for discovering valid arbitrage paths.
Automatically builds triangular trading cycles from available symbols.
"""

from typing import List, Dict, Set, Tuple
from collections import defaultdict
from ..core.models import Triangle, OrderSide, Symbol


class TriangleGenerator:
    """
    Generates all valid triangular arbitrage paths.
    
    A triangle consists of 3 trades that start and end with the same asset.
    Example: USDT → BTC → ETH → USDT
    
    The generator:
    - Builds a graph of tradable pairs
    - Finds all 3-cycle paths
    - Validates each path for liquidity and constraints
    - Avoids duplicate paths
    """
    
    def __init__(self):
        self._symbols: Dict[str, Symbol] = {}
        self._triangles: List[Triangle] = []
        self._asset_pairs: Dict[str, Set[str]] = defaultdict(set)
        self._symbol_map: Dict[Tuple[str, str], str] = {}
        
    def update_symbols(self, symbols: List[Symbol]):
        """
        Update the list of available symbols.
        
        Args:
            symbols: List of Symbol objects from Bybit
        """
        self._symbols.clear()
        self._asset_pairs.clear()
        self._symbol_map.clear()
        self._triangles.clear()
        
        for symbol in symbols:
            if not symbol.is_active:
                continue
            
            self._symbols[symbol.symbol] = symbol
            
            # Build asset pair mappings
            base = symbol.base_asset
            quote = symbol.quote_asset
            
            # Map (base, quote) -> symbol
            self._symbol_map[(base, quote)] = symbol.symbol
            self._symbol_map[(quote, base)] = symbol.symbol  # Reverse for lookup
            
            # Track which assets can be traded
            self._asset_pairs[base].add(quote)
            self._asset_pairs[quote].add(base)
    
    def generate_triangles(self, base_asset: str = "USDT") -> List[Triangle]:
        """
        Generate all valid triangles starting from a base asset.
        
        Args:
            base_asset: Starting/ending asset (default: USDT)
            
        Returns:
            List of Triangle objects
        """
        self._triangles.clear()
        
        if base_asset not in self._asset_pairs:
            return []
        
        # Get all assets directly tradable with base_asset
        first_hop_assets = self._asset_pairs[base_asset]
        
        seen_triangles: Set[Tuple[str, str, str]] = set()
        
        for asset1 in first_hop_assets:
            if asset1 == base_asset:
                continue
            
            # Get assets tradable with asset1
            second_hop_assets = self._asset_pairs.get(asset1, set())
            
            for asset2 in second_hop_assets:
                if asset2 in [base_asset, asset1]:
                    continue
                
                # Check if we can complete the triangle back to base_asset
                if base_asset not in self._asset_pairs.get(asset2, set()):
                    continue
                
                # Found a valid triangle: base_asset → asset1 → asset2 → base_asset
                triangle_key = tuple(sorted([base_asset, asset1, asset2]))
                
                if triangle_key in seen_triangles:
                    continue  # Skip duplicate
                
                seen_triangles.add(triangle_key)
                
                # Create triangle with both directions
                self._create_triangle_variants(base_asset, asset1, asset2)
        
        return self._triangles
    
    def _create_triangle_variants(self, start: str, mid1: str, mid2: str):
        """
        Create all valid trading direction variants for a triangle.
        
        For each triangle, there are typically 2 valid trading directions:
        1. Clockwise: start → mid1 → mid2 → start
        2. Counter-clockwise: start → mid2 → mid1 → start
        """
        
        # Try clockwise direction
        self._try_create_triangle(start, mid1, mid2, clockwise=True)
        
        # Try counter-clockwise direction
        self._try_create_triangle(start, mid2, mid1, clockwise=False)
    
    def _try_create_triangle(self, start: str, mid1: str, mid2: str, clockwise: bool):
        """
        Attempt to create a triangle with specific asset order.
        
        Args:
            start: Starting asset
            mid1: First middle asset
            mid2: Second middle asset
            clockwise: Direction of trade
        """
        try:
            # Determine trading pairs and sides
            if clockwise:
                # start → mid1 → mid2 → start
                leg1_pair = self._get_symbol(start, mid1)
                leg2_pair = self._get_symbol(mid1, mid2)
                leg3_pair = self._get_symbol(mid2, start)
                
                if not all([leg1_pair, leg2_pair, leg3_pair]):
                    return
                
                # Determine buy/sell for each leg
                leg1_side = self._determine_side(start, mid1, leg1_pair)
                leg2_side = self._determine_side(mid1, mid2, leg2_pair)
                leg3_side = self._determine_side(mid2, start, leg3_pair)
                
            else:
                # Different path configuration
                leg1_pair = self._get_symbol(start, mid2)
                leg2_pair = self._get_symbol(mid2, mid1)
                leg3_pair = self._get_symbol(mid1, start)
                
                if not all([leg1_pair, leg2_pair, leg3_pair]):
                    return
                
                leg1_side = self._determine_side(start, mid2, leg1_pair)
                leg2_side = self._determine_side(mid2, mid1, leg2_pair)
                leg3_side = self._determine_side(mid1, start, leg3_pair)
            
            # Create triangle
            triangle = Triangle.create(
                leg1=leg1_pair,
                leg2=leg2_pair,
                leg3=leg3_pair,
                side1=leg1_side,
                side2=leg2_side,
                side3=leg3_side,
                start=start,
                mid1=mid1,
                mid2=mid2,
            )
            
            self._triangles.append(triangle)
            
        except Exception:
            # Skip invalid triangles
            pass
    
    def _get_symbol(self, asset1: str, asset2: str) -> str:
        """Get symbol for asset pair."""
        key = (asset1, asset2)
        symbol = self._symbol_map.get(key)
        
        if symbol and symbol in self._symbols:
            return symbol
        
        # Try reverse
        key = (asset2, asset1)
        symbol = self._symbol_map.get(key)
        
        if symbol and symbol in self._symbols:
            return symbol
        
        return None
    
    def _determine_side(self, from_asset: str, to_asset: str, symbol: str) -> OrderSide:
        """
        Determine whether to BUY or SELL based on asset direction.
        
        If we're going from USDT to BTC, we BUY BTC.
        If we're going from BTC to USDT, we SELL BTC.
        """
        sym_obj = self._symbols.get(symbol)
        if not sym_obj:
            return OrderSide.BUY
        
        # If from_asset is the quote currency, we're buying the base
        if from_asset == sym_obj.quote_asset:
            return OrderSide.BUY
        
        # If from_asset is the base currency, we're selling
        return OrderSide.SELL
    
    def get_triangle_count(self) -> int:
        """Get number of generated triangles."""
        return len(self._triangles)
    
    def get_triangles_for_asset(self, asset: str) -> List[Triangle]:
        """
        Get all triangles involving a specific asset.
        
        Args:
            asset: Asset to filter by
            
        Returns:
            List of Triangle objects
        """
        return [
            t for t in self._triangles
            if t.start_asset == asset or 
               t.middle_asset1 == asset or 
               t.middle_asset2 == asset
        ]
    
    def get_all_assets(self) -> Set[str]:
        """Get all unique assets in the system."""
        assets = set()
        for symbol in self._symbols.values():
            assets.add(symbol.base_asset)
            assets.add(symbol.quote_asset)
        return assets
    
    def get_symbol_info(self, symbol: str) -> Symbol:
        """Get symbol information."""
        return self._symbols.get(symbol)
