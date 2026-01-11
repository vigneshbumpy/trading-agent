"""
Trading Database Service - SQLite persistence for trading state

Stores:
- Positions: Current holdings
- Trades: Execution history
- Bracket Orders: Active stop-loss/take-profit orders
- Settings: Configuration and preferences
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TradingDatabase:
    """SQLite database for trading state persistence"""
    
    def __init__(self, db_path: str = "trading_state.db"):
        """
        Initialize the trading database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        logger.info(f"Trading database initialized at {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Positions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    market TEXT,
                    broker TEXT,
                    bracket_id TEXT,
                    stop_loss_price REAL,
                    take_profit_price REAL,
                    trailing_stop_pct REAL,
                    status TEXT DEFAULT 'open',
                    exit_price REAL,
                    exit_time TEXT,
                    pnl REAL,
                    pnl_pct REAL,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, status) ON CONFLICT REPLACE
                )
            """)
            
            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL,
                    order_type TEXT DEFAULT 'MARKET',
                    market TEXT,
                    broker TEXT,
                    order_id TEXT,
                    status TEXT DEFAULT 'pending',
                    fill_price REAL,
                    fill_time TEXT,
                    commission REAL DEFAULT 0,
                    paper_trading INTEGER DEFAULT 1,
                    decision_text TEXT,
                    confidence REAL,
                    bracket_id TEXT,
                    error TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Bracket orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bracket_orders (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss_pct REAL,
                    stop_loss_price REAL,
                    take_profit_pct REAL,
                    take_profit_price REAL,
                    trailing_stop_pct REAL,
                    trailing_activation_pct REAL,
                    highest_price REAL,
                    lowest_price REAL,
                    status TEXT DEFAULT 'active',
                    trigger_reason TEXT,
                    triggered_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Daily statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    trades_count INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    largest_win REAL DEFAULT 0,
                    largest_loss REAL DEFAULT 0,
                    volume_traded REAL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bracket_status ON bracket_orders(status)")
    
    # ==================== POSITIONS ====================
    
    def save_position(
        self,
        symbol: str,
        action: str,
        quantity: float,
        entry_price: float,
        market: str = None,
        broker: str = None,
        bracket_id: str = None,
        stop_loss_price: float = None,
        take_profit_price: float = None,
        trailing_stop_pct: float = None,
        metadata: Dict = None
    ) -> int:
        """Save or update a position"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO positions 
                (symbol, action, quantity, entry_price, entry_time, market, broker,
                 bracket_id, stop_loss_price, take_profit_price, trailing_stop_pct,
                 status, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, CURRENT_TIMESTAMP)
            """, (
                symbol, action, quantity, entry_price, datetime.now().isoformat(),
                market, broker, bracket_id, stop_loss_price, take_profit_price,
                trailing_stop_pct, json.dumps(metadata) if metadata else None
            ))
            return cursor.lastrowid
    
    def close_position(
        self,
        symbol: str,
        exit_price: float,
        pnl: float = None,
        pnl_pct: float = None
    ) -> bool:
        """Close a position"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE positions 
                SET status = 'closed', exit_price = ?, exit_time = ?,
                    pnl = ?, pnl_pct = ?, updated_at = CURRENT_TIMESTAMP
                WHERE symbol = ? AND status = 'open'
            """, (exit_price, datetime.now().isoformat(), pnl, pnl_pct, symbol))
            return cursor.rowcount > 0
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions WHERE status = 'open'")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a symbol"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions WHERE symbol = ? AND status = 'open'", (symbol,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_closed_positions(self, limit: int = 100) -> List[Dict]:
        """Get closed positions"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM positions WHERE status = 'closed' ORDER BY exit_time DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ==================== TRADES ====================
    
    def save_trade(
        self,
        symbol: str,
        action: str,
        quantity: float,
        price: float = None,
        order_type: str = "MARKET",
        market: str = None,
        broker: str = None,
        order_id: str = None,
        status: str = "pending",
        paper_trading: bool = True,
        decision_text: str = None,
        confidence: float = None,
        bracket_id: str = None,
        metadata: Dict = None
    ) -> int:
        """Save a trade record"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades 
                (symbol, action, quantity, price, order_type, market, broker,
                 order_id, status, paper_trading, decision_text, confidence,
                 bracket_id, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                symbol, action, quantity, price, order_type, market, broker,
                order_id, status, 1 if paper_trading else 0, decision_text,
                confidence, bracket_id, json.dumps(metadata) if metadata else None
            ))
            return cursor.lastrowid
    
    def update_trade(
        self,
        trade_id: int,
        status: str = None,
        fill_price: float = None,
        error: str = None
    ) -> bool:
        """Update trade status"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if status:
                updates.append("status = ?")
                params.append(status)
            if fill_price:
                updates.append("fill_price = ?, fill_time = ?")
                params.extend([fill_price, datetime.now().isoformat()])
            if error:
                updates.append("error = ?")
                params.append(error)
            
            if not updates:
                return False
            
            params.append(trade_id)
            cursor.execute(f"UPDATE trades SET {', '.join(updates)} WHERE id = ?", params)
            return cursor.rowcount > 0
    
    def get_trades(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """Get trade history"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if symbol:
                cursor.execute(
                    "SELECT * FROM trades WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
                    (symbol, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM trades ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_today_trades(self) -> List[Dict]:
        """Get today's trades"""
        today = datetime.now().strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM trades WHERE DATE(created_at) = ? ORDER BY created_at DESC",
                (today,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ==================== BRACKET ORDERS ====================
    
    def save_bracket_order(
        self,
        bracket_id: str,
        symbol: str,
        action: str,
        quantity: float,
        entry_price: float,
        stop_loss_pct: float = None,
        stop_loss_price: float = None,
        take_profit_pct: float = None,
        take_profit_price: float = None,
        trailing_stop_pct: float = None,
        trailing_activation_pct: float = None
    ) -> str:
        """Save a bracket order"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO bracket_orders 
                (id, symbol, action, quantity, entry_price, stop_loss_pct, stop_loss_price,
                 take_profit_pct, take_profit_price, trailing_stop_pct, trailing_activation_pct,
                 highest_price, lowest_price, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
            """, (
                bracket_id, symbol, action, quantity, entry_price,
                stop_loss_pct, stop_loss_price, take_profit_pct, take_profit_price,
                trailing_stop_pct, trailing_activation_pct,
                entry_price if action == "BUY" else None,
                entry_price if action == "SELL" else None
            ))
            return bracket_id
    
    def update_bracket_order(
        self,
        bracket_id: str,
        status: str = None,
        stop_loss_price: float = None,
        highest_price: float = None,
        lowest_price: float = None,
        trigger_reason: str = None
    ) -> bool:
        """Update bracket order"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if status:
                updates.append("status = ?")
                params.append(status)
            if stop_loss_price:
                updates.append("stop_loss_price = ?")
                params.append(stop_loss_price)
            if highest_price:
                updates.append("highest_price = ?")
                params.append(highest_price)
            if lowest_price:
                updates.append("lowest_price = ?")
                params.append(lowest_price)
            if trigger_reason:
                updates.append("trigger_reason = ?, triggered_at = ?")
                params.extend([trigger_reason, datetime.now().isoformat()])
            
            if not updates:
                return False
            
            params.append(bracket_id)
            cursor.execute(f"UPDATE bracket_orders SET {', '.join(updates)} WHERE id = ?", params)
            return cursor.rowcount > 0
    
    def get_active_bracket_orders(self) -> List[Dict]:
        """Get all active bracket orders"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bracket_orders WHERE status = 'active'")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ==================== DAILY STATS ====================
    
    def update_daily_stats(
        self,
        trades_count: int = 0,
        winning_trades: int = 0,
        losing_trades: int = 0,
        pnl: float = 0,
        volume: float = 0
    ):
        """Update today's statistics"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get existing stats
            cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (today,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE daily_stats SET
                        trades_count = trades_count + ?,
                        winning_trades = winning_trades + ?,
                        losing_trades = losing_trades + ?,
                        total_pnl = total_pnl + ?,
                        volume_traded = volume_traded + ?,
                        largest_win = MAX(largest_win, ?),
                        largest_loss = MIN(largest_loss, ?)
                    WHERE date = ?
                """, (
                    trades_count, winning_trades, losing_trades, pnl, volume,
                    pnl if pnl > 0 else 0, pnl if pnl < 0 else 0, today
                ))
            else:
                cursor.execute("""
                    INSERT INTO daily_stats 
                    (date, trades_count, winning_trades, losing_trades, total_pnl,
                     volume_traded, largest_win, largest_loss)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    today, trades_count, winning_trades, losing_trades, pnl, volume,
                    pnl if pnl > 0 else 0, pnl if pnl < 0 else 0
                ))
    
    def get_daily_stats(self, date: str = None) -> Optional[Dict]:
        """Get daily statistics"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (date,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ==================== SETTINGS ====================
    
    def save_setting(self, key: str, value: Any):
        """Save a setting"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, json.dumps(value)))
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["value"])
            return default
    
    # ==================== RECOVERY ====================
    
    def export_state(self) -> Dict:
        """Export full state for backup"""
        return {
            "positions": self.get_open_positions(),
            "bracket_orders": self.get_active_bracket_orders(),
            "today_trades": self.get_today_trades(),
            "daily_stats": self.get_daily_stats(),
            "exported_at": datetime.now().isoformat()
        }
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        positions = self.get_open_positions()
        today_stats = self.get_daily_stats() or {}
        
        return {
            "open_positions": len(positions),
            "total_value": sum(p["quantity"] * p["entry_price"] for p in positions),
            "today_trades": today_stats.get("trades_count", 0),
            "today_pnl": today_stats.get("total_pnl", 0),
            "win_rate": (
                today_stats.get("winning_trades", 0) / 
                max(today_stats.get("trades_count", 1), 1) * 100
            )
        }


def create_trading_database(db_path: str = None) -> TradingDatabase:
    """Factory function to create trading database"""
    if db_path is None:
        db_path = "data/trading_state.db"
    return TradingDatabase(db_path)
