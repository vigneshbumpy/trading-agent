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

        # Automation runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT DEFAULT 'running',
                symbols_analyzed INTEGER DEFAULT 0,
                trades_executed INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                config_json TEXT,
                notes TEXT
            )
        """)

        # Execution logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                normalized_symbol TEXT,
                action TEXT NOT NULL,
                quantity REAL,
                price REAL,
                order_type TEXT,
                market TEXT,
                broker TEXT,
                order_id TEXT,
                status TEXT,
                execution_time REAL,
                error_message TEXT,
                risk_check_passed INTEGER DEFAULT 1,
                paper_trading INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)
        
        # Add paper_trading column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE execution_logs ADD COLUMN paper_trading INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Market config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT UNIQUE NOT NULL,
                broker_type TEXT,
                enabled INTEGER DEFAULT 1,
                max_position_size REAL DEFAULT 0.1,
                max_daily_trades INTEGER DEFAULT 10,
                max_daily_loss REAL DEFAULT 0.05,
                position_sizing_method TEXT DEFAULT 'percentage',
                position_sizing_config TEXT,
                risk_limits_config TEXT,
                updated_at TEXT NOT NULL
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

    # Automation operations
    def save_automation_run(self, run_data: Dict) -> int:
        """Save automation run"""
        conn = self.get_connection()
        cursor = conn.cursor()

        import json
        config_json = json.dumps(run_data.get('config', {}))

        cursor.execute("""
            INSERT INTO automation_runs (
                run_date, started_at, status, symbols_analyzed,
                trades_executed, errors_count, config_json, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_data.get('run_date', datetime.now().date().isoformat()),
            run_data.get('started_at', datetime.now().isoformat()),
            run_data.get('status', 'running'),
            run_data.get('symbols_analyzed', 0),
            run_data.get('trades_executed', 0),
            run_data.get('errors_count', 0),
            config_json,
            run_data.get('notes')
        ))

        run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return run_id

    def update_automation_run(self, run_id: int, **kwargs):
        """Update automation run"""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates = []
        values = []

        for key, value in kwargs.items():
            if key == 'config':
                import json
                updates.append("config_json = ?")
                values.append(json.dumps(value))
            else:
                updates.append(f"{key} = ?")
                values.append(value)

        if updates:
            values.append(run_id)
            cursor.execute(f"""
                UPDATE automation_runs
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)

        conn.commit()
        conn.close()

    def get_automation_runs(self, limit: int = 50) -> List[Dict]:
        """Get automation runs"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM automation_runs
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    # Execution log operations
    def save_execution_log(self, log_data: Dict) -> int:
        """Save execution log"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO execution_logs (
                timestamp, symbol, normalized_symbol, action, quantity, price,
                order_type, market, broker, order_id, status, execution_time,
                error_message, risk_check_passed, paper_trading, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_data.get('timestamp', datetime.now().isoformat()),
            log_data.get('symbol'),
            log_data.get('normalized_symbol'),
            log_data.get('action'),
            log_data.get('quantity'),
            log_data.get('price'),
            log_data.get('order_type'),
            log_data.get('market'),
            log_data.get('broker'),
            log_data.get('order_id'),
            log_data.get('status'),
            log_data.get('execution_time'),
            log_data.get('error_message'),
            1 if log_data.get('risk_check_passed', True) else 0,
            1 if log_data.get('paper_trading', True) else 0,
            datetime.now().isoformat()
        ))

        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id

    def get_execution_logs(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get execution logs"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT * FROM execution_logs
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol, limit))
        else:
            cursor.execute("""
                SELECT * FROM execution_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    # Market config operations
    def save_market_config(self, market: str, config_data: Dict):
        """Save market configuration"""
        conn = self.get_connection()
        cursor = conn.cursor()

        import json
        position_config = json.dumps(config_data.get('position_sizing_config', {}))
        risk_config = json.dumps(config_data.get('risk_limits_config', {}))

        cursor.execute("""
            INSERT OR REPLACE INTO market_config (
                market, broker_type, enabled, max_position_size, max_daily_trades,
                max_daily_loss, position_sizing_method, position_sizing_config,
                risk_limits_config, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            market,
            config_data.get('broker_type'),
            1 if config_data.get('enabled', True) else 0,
            config_data.get('max_position_size', 0.1),
            config_data.get('max_daily_trades', 10),
            config_data.get('max_daily_loss', 0.05),
            config_data.get('position_sizing_method', 'percentage'),
            position_config,
            risk_config,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_market_config(self, market: str) -> Optional[Dict]:
        """Get market configuration"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM market_config WHERE market = ?", (market,))
        row = cursor.fetchone()
        conn.close()

        if row:
            columns = [desc[0] for desc in cursor.description]
            config = dict(zip(columns, row))

            # Parse JSON fields
            import json
            if config.get('position_sizing_config'):
                config['position_sizing_config'] = json.loads(config['position_sizing_config'])
            if config.get('risk_limits_config'):
                config['risk_limits_config'] = json.loads(config['risk_limits_config'])

            return config
        return None

    def get_all_market_configs(self) -> List[Dict]:
        """Get all market configurations"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM market_config")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        configs = []
        import json
        for row in rows:
            config = dict(zip(columns, row))
            if config.get('position_sizing_config'):
                config['position_sizing_config'] = json.loads(config['position_sizing_config'])
            if config.get('risk_limits_config'):
                config['risk_limits_config'] = json.loads(config['risk_limits_config'])
            configs.append(config)

        return configs
