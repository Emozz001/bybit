"""
Table Components for the Bybit Trading TUI
Data tables for markets, positions, orders, and more.
"""

from textual.widgets import Static, DataTable
from textual.app import ComposeResult
from rich.table import Table as RichTable
from rich.text import Text


class DataTableWidget(Static):
    """
    A rich data table widget using Rich's Table.
    
    Usage:
        columns = ["Pair", "Price", "Change", "Volume"]
        rows = [
            ["BTCUSDT", "119210", "+1.21%", "High"],
            ["ETHUSDT", "3562", "+0.82%", "High"],
        ]
        table = DataTableWidget(columns, rows)
    """
    
    def __init__(self, columns: list, rows: list = None, id: str = None):
        super().__init__(id=id)
        self.columns = columns
        self.rows = rows or []
        self.sort_column = 0
        self.sort_reverse = False
    
    def compose(self) -> ComposeResult:
        yield Static(self._render_table(), id="table-content")
    
    def _render_table(self) -> str:
        rich_table = RichTable(show_header=True, header_style="bold cyan", expand=True)
        
        # Add columns
        for col in self.columns:
            rich_table.add_column(col, style="white")
        
        # Add rows with color coding
        for row in self.rows:
            formatted_row = []
            for i, cell in enumerate(row):
                cell_str = str(cell)
                
                # Color code percentage changes
                if i > 0 and "%" in cell_str:
                    if cell_str.startswith("+"):
                        formatted_row.append(f"[green]{cell_str}[/green]")
                    elif cell_str.startswith("-"):
                        formatted_row.append(f"[red]{cell_str}[/red]")
                    else:
                        formatted_row.append(cell_str)
                # Color code status indicators
                elif cell_str.lower() in ["high", "running", "open", "active"]:
                    formatted_row.append(f"[green]{cell_str}[/green]")
                elif cell_str.lower() in ["low", "stopped", "closed", "inactive"]:
                    formatted_row.append(f"[yellow]{cell_str}[/yellow]")
                elif cell_str.lower() in ["error", "failed", "offline"]:
                    formatted_row.append(f"[red]{cell_str}[/red]")
                else:
                    formatted_row.append(cell_str)
            
            rich_table.add_row(*formatted_row)
        
        return f"{rich_table}"
    
    def set_rows(self, rows: list):
        """Update table rows and refresh."""
        self.rows = rows
        self.refresh()
    
    def add_row(self, row: list):
        """Add a single row to the table."""
        self.rows.append(row)
        self.refresh()
    
    def sort_by(self, column_index: int, reverse: bool = False):
        """Sort table by column index."""
        if column_index == self.sort_column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column_index
            self.sort_reverse = reverse
        
        self.rows.sort(key=lambda x: x[self.sort_column], reverse=self.sort_reverse)
        self.refresh()


class MarketTable(DataTableWidget):
    """
    Specialized table for displaying market data.
    
    Columns: Pair, Price, 24h Change, Volume, Action
    """
    
    def __init__(self, market_data: list = None, id: str = "market-table"):
        columns = ["Pair", "Price", "24h Change", "Volume", "Action"]
        rows = []
        
        if market_data:
            for item in market_data:
                change_color = "[green]" if item.get("change_24h", 0) >= 0 else "[red]"
                volume_level = "High" if item.get("volume_24h", 0) > 1000000 else "Medium"
                
                rows.append([
                    item.get("symbol", "N/A"),
                    f"{item.get('price', 0):.2f}",
                    f"{change_color}{item.get('change_24h', 0):+.2f}%[/]",
                    volume_level,
                    "[blue]Trade[/blue]"
                ])
        
        super().__init__(columns, rows, id=id)
    
    def update_market_data(self, market_data: list):
        """Update with new market data."""
        rows = []
        for item in market_data:
            change_color = "[green]" if item.get("change_24h", 0) >= 0 else "[red]"
            volume_level = "High" if item.get("volume_24h", 0) > 1000000 else "Medium"
            
            rows.append([
                item.get("symbol", "N/A"),
                f"{item.get('price', 0):.2f}",
                f"{change_color}{item.get('change_24h', 0):+.2f}%[/]",
                volume_level,
                "[blue]Trade[/blue]"
            ])
        
        self.set_rows(rows)


class PositionsTable(DataTableWidget):
    """
    Specialized table for displaying open positions.
    
    Columns: Symbol, Side, Size, Entry Price, Mark Price, PNL, Status
    """
    
    def __init__(self, positions: list = None, id: str = "positions-table"):
        columns = ["Symbol", "Side", "Size", "Entry", "Mark", "PNL", "Status"]
        rows = []
        
        if positions:
            for pos in positions:
                side = "[green]Long[/green]" if pos.get("side", "").lower() == "long" else "[red]Short[/red]"
                pnl = pos.get("pnl", 0)
                pnl_str = f"[green]+{pnl:.2f}[/green]" if pnl > 0 else f"[red]{pnl:.2f}[/red]" if pnl < 0 else "[dim]0.00[/dim]"
                status = "[green]● Open[/green]" if pos.get("is_open", True) else "[dim]Closed[/dim]"
                
                rows.append([
                    pos.get("symbol", "N/A"),
                    side,
                    f"{pos.get('size', 0):.4f}",
                    f"{pos.get('entry_price', 0):.2f}",
                    f"{pos.get('mark_price', 0):.2f}",
                    pnl_str,
                    status
                ])
        
        super().__init__(columns, rows, id=id)
    
    def update_positions(self, positions: list):
        """Update with new position data."""
        rows = []
        for pos in positions:
            side = "[green]Long[/green]" if pos.get("side", "").lower() == "long" else "[red]Short[/red]"
            pnl = pos.get("pnl", 0)
            pnl_str = f"[green]+{pnl:.2f}[/green]" if pnl > 0 else f"[red]{pnl:.2f}[/red]" if pnl < 0 else "[dim]0.00[/dim]"
            status = "[green]● Open[/green]" if pos.get("is_open", True) else "[dim]Closed[/dim]"
            
            rows.append([
                pos.get("symbol", "N/A"),
                side,
                f"{pos.get('size', 0):.4f}",
                f"{pos.get('entry_price', 0):.2f}",
                f"{pos.get('mark_price', 0):.2f}",
                pnl_str,
                status
            ])
        
        self.set_rows(rows)


class OrdersTable(DataTableWidget):
    """
    Specialized table for displaying orders.
    
    Columns: ID, Symbol, Side, Type, Price, Size, Filled, Status
    """
    
    def __init__(self, orders: list = None, id: str = "orders-table"):
        columns = ["ID", "Symbol", "Side", "Type", "Price", "Size", "Filled", "Status"]
        rows = []
        
        if orders:
            for order in orders:
                side = "[green]Buy[/green]" if order.get("side", "").lower() == "buy" else "[red]Sell[/red]"
                status_map = {
                    "new": "[blue]New[/blue]",
                    "partially_filled": "[yellow]Partial[/yellow]",
                    "filled": "[green]Filled[/green]",
                    "cancelled": "[dim]Cancelled[/dim]",
                    "rejected": "[red]Rejected[/red]",
                }
                status = status_map.get(order.get("status", "").lower(), order.get("status", "N/A"))
                
                filled_pct = (order.get("filled_size", 0) / order.get("size", 1) * 100) if order.get("size", 0) > 0 else 0
                
                rows.append([
                    str(order.get("order_id", "N/A"))[:8],
                    order.get("symbol", "N/A"),
                    side,
                    order.get("type", "N/A").capitalize(),
                    f"{order.get('price', 0):.2f}",
                    f"{order.get('size', 0):.4f}",
                    f"{filled_pct:.0f}%",
                    status
                ])
        
        super().__init__(columns, rows, id=id)
    
    def update_orders(self, orders: list):
        """Update with new order data."""
        rows = []
        for order in orders:
            side = "[green]Buy[/green]" if order.get("side", "").lower() == "buy" else "[red]Sell[/red]"
            status_map = {
                "new": "[blue]New[/blue]",
                "partially_filled": "[yellow]Partial[/yellow]",
                "filled": "[green]Filled[/green]",
                "cancelled": "[dim]Cancelled[/dim]",
                "rejected": "[red]Rejected[/red]",
            }
            status = status_map.get(order.get("status", "").lower(), order.get("status", "N/A"))
            
            filled_pct = (order.get("filled_size", 0) / order.get("size", 1) * 100) if order.get("size", 0) > 0 else 0
            
            rows.append([
                str(order.get("order_id", "N/A"))[:8],
                order.get("symbol", "N/A"),
                side,
                order.get("type", "N/A").capitalize(),
                f"{order.get('price', 0):.2f}",
                f"{order.get('size', 0):.4f}",
                f"{filled_pct:.0f}%",
                status
            ])
        
        self.set_rows(rows)
