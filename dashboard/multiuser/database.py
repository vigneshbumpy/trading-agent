"""
Multi-user PostgreSQL database module
Supports both PostgreSQL (production) and SQLite (development)
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import json


# Detect database type from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dashboard/data/multiuser.db")

if DATABASE_URL.startswith("postgres"):
    # PostgreSQL
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import psycopg2.pool
    DB_TYPE = "postgres"
else:
    # SQLite
    import sqlite3
    DB_TYPE = "sqlite"


class MultiUserDatabase:
    """Multi-tenant database with user isolation"""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.db_type = DB_TYPE

        if self.db_type == "postgres":
            # PostgreSQL connection pool
            self.pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,  # min and max connections
                self.database_url
            )
        else:
            # SQLite - extract path
            self.db_path = Path(self.database_url.replace("sqlite:///", ""))
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.init_database()

    def get_connection(self):
        """Get database connection"""
        if self.db_type == "postgres":
            return self.pool.getconn()
        else:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Return dict-like rows
            return conn

    def release_connection(self, conn):
        """Release connection back to pool"""
        if self.db_type == "postgres":
            self.pool.putconn(conn)
        else:
            conn.close()

    def init_database(self):
        """Initialize all tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                subscription_tier VARCHAR(50) DEFAULT 'free',
                subscription_expires_at TIMESTAMP,
                total_analyses INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0
            )
        """ if self.db_type == "postgres" else """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                phone TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT,
                is_active INTEGER DEFAULT 1,
                is_verified INTEGER DEFAULT 0,
                subscription_tier TEXT DEFAULT 'free',
                subscription_expires_at TEXT,
                total_analyses INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0
            )
        """)

        # 2. User broker credentials
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_broker_credentials (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                broker_name VARCHAR(50) NOT NULL,
                api_key TEXT,
                api_secret TEXT,
                access_token TEXT,
                refresh_token TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_synced TIMESTAMP,
                UNIQUE(user_id, broker_name)
            )
        """ if self.db_type == "postgres" else """
            CREATE TABLE IF NOT EXISTS user_broker_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                broker_name TEXT NOT NULL,
                api_key TEXT,
                api_secret TEXT,
                access_token TEXT,
                refresh_token TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_synced TEXT,
                UNIQUE(user_id, broker_name),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 3. User portfolios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_portfolios (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                ticker VARCHAR(50) NOT NULL,
                exchange VARCHAR(20),
                quantity DECIMAL(15,4) NOT NULL,
                avg_price DECIMAL(15,2),
                total_invested DECIMAL(15,2),
                current_value DECIMAL(15,2),
                unrealized_pl DECIMAL(15,2),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, ticker, exchange)
            )
        """ if self.db_type == "postgres" else """
            CREATE TABLE IF NOT EXISTS user_portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ticker TEXT NOT NULL,
                exchange TEXT,
                quantity REAL NOT NULL,
                avg_price REAL,
                total_invested REAL,
                current_value REAL,
                unrealized_pl REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, ticker, exchange),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 4. User analyses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_analyses (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                ticker VARCHAR(50) NOT NULL,
                exchange VARCHAR(20),
                analysis_date DATE NOT NULL,
                decision VARCHAR(10),
                confidence_score DECIMAL(3,2),
                market_report TEXT,
                sentiment_report TEXT,
                news_report TEXT,
                fundamentals_report TEXT,
                investment_plan TEXT,
                trader_plan TEXT,
                risk_decision TEXT,
                final_decision TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                llm_cost DECIMAL(10,4)
            )
        """ if self.db_type == "postgres" else """
            CREATE TABLE IF NOT EXISTS user_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ticker TEXT NOT NULL,
                exchange TEXT,
                analysis_date TEXT NOT NULL,
                decision TEXT,
                confidence_score REAL,
                market_report TEXT,
                sentiment_report TEXT,
                news_report TEXT,
                fundamentals_report TEXT,
                investment_plan TEXT,
                trader_plan TEXT,
                risk_decision TEXT,
                final_decision TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                llm_cost REAL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 5. User trades
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_trades (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                analysis_id INTEGER REFERENCES user_analyses(id),
                ticker VARCHAR(50) NOT NULL,
                exchange VARCHAR(20),
                action VARCHAR(10) NOT NULL,
                quantity DECIMAL(15,4) NOT NULL,
                price DECIMAL(15,2),
                total_value DECIMAL(15,2),
                trade_date DATE NOT NULL,
                execution_type VARCHAR(20),
                broker_order_id VARCHAR(100),
                status VARCHAR(20) DEFAULT 'pending',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """ if self.db_type == "postgres" else """
            CREATE TABLE IF NOT EXISTS user_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                analysis_id INTEGER,
                ticker TEXT NOT NULL,
                exchange TEXT,
                action TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL,
                total_value REAL,
                trade_date TEXT NOT NULL,
                execution_type TEXT,
                broker_order_id TEXT,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (analysis_id) REFERENCES user_analyses(id)
            )
        """)

        # 6. User settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                llm_provider VARCHAR(50) DEFAULT 'openrouter',
                quick_llm_model VARCHAR(100) DEFAULT 'deepseek/deepseek-chat',
                deep_llm_model VARCHAR(100) DEFAULT 'deepseek/deepseek-r1',
                default_analysts JSON,
                default_research_depth INTEGER DEFAULT 1,
                max_position_size DECIMAL(3,2) DEFAULT 0.10,
                max_total_exposure DECIMAL(3,2) DEFAULT 0.80,
                default_stop_loss DECIMAL(3,2) DEFAULT 0.10,
                email_notifications BOOLEAN DEFAULT TRUE,
                sms_notifications BOOLEAN DEFAULT FALSE,
                auto_trade_enabled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """ if self.db_type == "postgres" else """
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                llm_provider TEXT DEFAULT 'openrouter',
                quick_llm_model TEXT DEFAULT 'deepseek/deepseek-chat',
                deep_llm_model TEXT DEFAULT 'deepseek/deepseek-r1',
                default_analysts TEXT,
                default_research_depth INTEGER DEFAULT 1,
                max_position_size REAL DEFAULT 0.10,
                max_total_exposure REAL DEFAULT 0.80,
                default_stop_loss REAL DEFAULT 0.10,
                email_notifications INTEGER DEFAULT 1,
                sms_notifications INTEGER DEFAULT 0,
                auto_trade_enabled INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 7. User watchlist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_watchlist (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                ticker VARCHAR(50) NOT NULL,
                exchange VARCHAR(20),
                notes TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, ticker, exchange)
            )
        """ if self.db_type == "postgres" else """
            CREATE TABLE IF NOT EXISTS user_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ticker TEXT NOT NULL,
                exchange TEXT,
                notes TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, ticker, exchange),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        self.release_connection(conn)

    # User management methods
    def create_user(self, email: str, password_hash: str, full_name: str = None) -> int:
        """Create a new user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (email, password_hash, full_name)
                VALUES (%s, %s, %s) RETURNING id
            """ if self.db_type == "postgres" else """
                INSERT INTO users (email, password_hash, full_name)
                VALUES (?, ?, ?)
            """, (email, password_hash, full_name))

            if self.db_type == "postgres":
                user_id = cursor.fetchone()[0]
            else:
                user_id = cursor.lastrowid

            conn.commit()

            # Create default settings
            cursor.execute("""
                INSERT INTO user_settings (user_id, default_analysts)
                VALUES (%s, %s)
            """ if self.db_type == "postgres" else """
                INSERT INTO user_settings (user_id, default_analysts)
                VALUES (?, ?)
            """, (user_id, json.dumps(["market", "news", "fundamentals"])))

            conn.commit()
            return user_id

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.release_connection(conn)

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s" if self.db_type == "postgres" else "SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()

        self.release_connection(conn)

        if row:
            if self.db_type == "postgres":
                return dict(row)
            else:
                return dict(row)
        return None

    def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
        """ if self.db_type == "postgres" else """
            UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
        """, (user_id,))

        conn.commit()
        self.release_connection(conn)

    # User-scoped data access methods will be added here...
    # (Similar to the existing database.py but with user_id parameter)
