"""
Database module for storing portfolio, trades, and analysis history
Uses SQLite for simplicity and portability
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd


class TradingDatabase:
    """Manages all database operations for the trading dashboard"""

    def __init__(self, db_path: str = "dashboard/data/trading.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(str(self.db_path))

    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Analyses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                analysis_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                decision TEXT NOT NULL,
                confidence TEXT,
                market_report TEXT,
                sentiment_report TEXT,
                news_report TEXT,
                fundamentals_report TEXT,
                investment_plan TEXT,
                trader_plan TEXT,
                risk_decision TEXT,
                final_decision TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL,
                price REAL,
                total_value REAL,
                trade_date TEXT NOT NULL,
                execution_type TEXT DEFAULT 'paper',
                order_id TEXT,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (analysis_id) REFERENCES analyses (id)
            )
        """)

        # Portfolio table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                avg_price REAL,
                total_invested REAL DEFAULT 0,
                last_updated TEXT NOT NULL
            )
        """)

        # Watchlist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                added_at TEXT NOT NULL,
                notes TEXT
            )
        """)

        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Secrets table (encrypted API keys)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT NOT NULL,
                encrypted_value BLOB NOT NULL,
                provider TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                user_id INTEGER DEFAULT NULL,
                UNIQUE(key_name, user_id)
            )
        """)

        # LLM Presets table (tier configurations)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tier_name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                backend_url TEXT,
                quick_think_model TEXT NOT NULL,
                deep_think_model TEXT NOT NULL,
                requires_api_key INTEGER DEFAULT 0,
                api_key_name TEXT,
                estimated_cost_month TEXT,
                speed_rating TEXT,
                quality_rating TEXT,
                is_recommended INTEGER DEFAULT 0,
                display_order INTEGER DEFAULT 0
            )
        """)

        # Populate default LLM presets if empty
        cursor.execute("SELECT COUNT(*) FROM llm_presets")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO llm_presets (
                    tier_name, display_name, provider, backend_url,
                    quick_think_model, deep_think_model, requires_api_key, api_key_name,
                    estimated_cost_month, speed_rating, quality_rating,
                    is_recommended, display_order
                ) VALUES
                (
                    'budget', 'Budget (FREE) - Local Models',
                    'ollama', 'http://localhost:11434/v1',
                    'llama3.2', 'qwen2.5:32b', 0, NULL,
                    '$0/month', 'Medium (depends on hardware)', 'Good',
                    0, 1
                ),
                (
                    'best_value', 'Best Value (Recommended)',
                    'openrouter', 'https://openrouter.ai/api/v1',
                    'deepseek/deepseek-chat', 'deepseek/deepseek-r1', 1, 'OPENROUTER_API_KEY',
                    '$15-30/month (50 analyses)', 'Very Fast', 'Excellent',
                    1, 2
                ),
                (
                    'premium', 'Premium - Best Quality',
                    'anthropic', NULL,
                    'claude-3-5-haiku-latest', 'claude-sonnet-4-20250514', 1, 'ANTHROPIC_API_KEY',
                    '$50-100/month (50 analyses)', 'Fast', 'Best',
                    0, 3
                )
            """)

        # Populate default settings if empty
        cursor.execute("SELECT COUNT(*) FROM settings")
        if cursor.fetchone()[0] == 0:
            default_settings = [
                ('llm_tier', 'budget'),
                ('llm_provider', 'ollama'),
                ('backend_url', 'http://localhost:11434/v1'),
                ('quick_think_model', 'llama3.2'),
                ('deep_think_model', 'qwen2.5:32b'),
                ('max_debate_rounds', '1'),
                ('max_risk_discuss_rounds', '1'),
            ]
            for key, value in default_settings:
                cursor.execute("""
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (?, ?, datetime('now'))
                """, (key, value))

        conn.commit()
        conn.close()

    # Analysis operations
    def save_analysis(self, analysis_data: Dict) -> int:
        """Save a new analysis to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO analyses (
                ticker, analysis_date, created_at, decision, confidence,
                market_report, sentiment_report, news_report, fundamentals_report,
                investment_plan, trader_plan, risk_decision, final_decision, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis_data.get('ticker'),
            analysis_data.get('analysis_date'),
            datetime.now().isoformat(),
            analysis_data.get('decision'),
            analysis_data.get('confidence'),
            analysis_data.get('market_report'),
            analysis_data.get('sentiment_report'),
            analysis_data.get('news_report'),
            analysis_data.get('fundamentals_report'),
            analysis_data.get('investment_plan'),
            analysis_data.get('trader_plan'),
            analysis_data.get('risk_decision'),
            analysis_data.get('final_decision'),
            analysis_data.get('status', 'pending')
        ))

        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return analysis_id

    def get_analysis(self, analysis_id: int) -> Optional[Dict]:
        """Get a specific analysis by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

    def get_recent_analyses(self, limit: int = 10) -> List[Dict]:
        """Get recent analyses"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM analyses
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    def update_analysis_status(self, analysis_id: int, status: str):
        """Update analysis status (pending, approved, rejected)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE analyses SET status = ? WHERE id = ?
        """, (status, analysis_id))

        conn.commit()
        conn.close()

    # Trade operations
    def save_trade(self, trade_data: Dict) -> int:
        """Save a new trade"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trades (
                analysis_id, ticker, action, quantity, price, total_value,
                trade_date, execution_type, order_id, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_data.get('analysis_id'),
            trade_data.get('ticker'),
            trade_data.get('action'),
            trade_data.get('quantity'),
            trade_data.get('price'),
            trade_data.get('total_value'),
            trade_data.get('trade_date'),
            trade_data.get('execution_type', 'paper'),
            trade_data.get('order_id'),
            trade_data.get('status', 'pending'),
            trade_data.get('notes'),
            datetime.now().isoformat()
        ))

        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id

    def get_trades(self, ticker: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if ticker:
            cursor.execute("""
                SELECT * FROM trades
                WHERE ticker = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (ticker, limit))
        else:
            cursor.execute("""
                SELECT * FROM trades
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    # Portfolio operations
    def update_portfolio(self, ticker: str, quantity: float, price: float, action: str):
        """Update portfolio after a trade"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get current position
        cursor.execute("SELECT * FROM portfolio WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()

        if row:
            # Update existing position
            current_qty = row[2]  # quantity column
            current_avg = row[3]  # avg_price column
            current_invested = row[4]  # total_invested column

            if action == "BUY":
                new_qty = current_qty + quantity
                new_invested = current_invested + (quantity * price)
                new_avg = new_invested / new_qty if new_qty > 0 else 0
            elif action == "SELL":
                new_qty = current_qty - quantity
                if new_qty <= 0:
                    # Close position
                    cursor.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker,))
                    conn.commit()
                    conn.close()
                    return
                new_invested = current_invested - (quantity * current_avg)
                new_avg = current_avg
            else:
                new_qty = current_qty
                new_avg = current_avg
                new_invested = current_invested

            cursor.execute("""
                UPDATE portfolio
                SET quantity = ?, avg_price = ?, total_invested = ?, last_updated = ?
                WHERE ticker = ?
            """, (new_qty, new_avg, new_invested, datetime.now().isoformat(), ticker))
        else:
            # New position
            if action == "BUY":
                cursor.execute("""
                    INSERT INTO portfolio (ticker, quantity, avg_price, total_invested, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                """, (ticker, quantity, price, quantity * price, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def get_portfolio(self) -> pd.DataFrame:
        """Get current portfolio as DataFrame"""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM portfolio", conn)
        conn.close()
        return df

    # Watchlist operations
    def add_to_watchlist(self, ticker: str, notes: str = ""):
        """Add ticker to watchlist"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO watchlist (ticker, added_at, notes)
                VALUES (?, ?, ?)
            """, (ticker.upper(), datetime.now().isoformat(), notes))
            conn.commit()
        except sqlite3.IntegrityError:
            # Ticker already in watchlist
            pass

        conn.close()

    def remove_from_watchlist(self, ticker: str):
        """Remove ticker from watchlist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
        conn.commit()
        conn.close()

    def get_watchlist(self) -> List[Dict]:
        """Get watchlist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watchlist ORDER BY added_at DESC")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    # Settings operations
    def save_setting(self, key: str, value: str):
        """Save a setting"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()

        return row[0] if row else default
