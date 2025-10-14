"""
Database connection pooling for improved performance
"""

import aiosqlite
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
import logging
from contextlib import asynccontextmanager


logger = logging.getLogger(__name__)


class SQLiteConnectionPool:
    """
    Connection pool for SQLite database operations.
    
    Provides connection reuse and performance optimizations for concurrent access.
    """
    
    def __init__(
        self, 
        db_path: str, 
        pool_size: int = 5, 
        max_overflow: int = 10,
        enable_wal: bool = True
    ):
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.enable_wal = enable_wal
        
        # Connection management
        self._available_connections = asyncio.Queue(maxsize=pool_size)
        self._all_connections = set()
        self._checked_out = set()
        self._lock = asyncio.Lock()
        
        # Performance metrics
        self._connection_count = 0
        self._checkout_count = 0
        self._pool_hits = 0
        self._pool_misses = 0
        
        logger.info(f"Created SQLite connection pool: size={pool_size}, overflow={max_overflow}")
    
    async def initialize(self):
        """Initialize the connection pool"""
        async with self._lock:
            # Create initial connections
            for _ in range(self.pool_size):
                conn = await self._create_connection()
                await self._available_connections.put(conn)
                self._all_connections.add(conn)
                self._connection_count += 1
            
            logger.info(f"Initialized SQLite connection pool with {self._connection_count} connections")
    
    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a new optimized database connection"""
        conn = await aiosqlite.connect(self.db_path)
        
        if self.enable_wal:
            # Enable performance optimizations
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=10000")
            await conn.execute("PRAGMA temp_store=MEMORY")
            await conn.execute("PRAGMA mmap_size=268435456")
            
            # Enable foreign keys for data integrity
            await conn.execute("PRAGMA foreign_keys=ON")
            
        return conn
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool (context manager)"""
        conn = None
        try:
            # Try to get from pool
            try:
                conn = await asyncio.wait_for(
                    self._available_connections.get(), 
                    timeout=1.0
                )
                self._pool_hits += 1
                logger.debug("Retrieved connection from pool")
                
            except asyncio.TimeoutError:
                # Pool exhausted, create overflow connection if allowed
                async with self._lock:
                    if len(self._all_connections) < (self.pool_size + self.max_overflow):
                        conn = await self._create_connection()
                        self._all_connections.add(conn)
                        self._connection_count += 1
                        self._pool_misses += 1
                        logger.debug("Created overflow connection")
                    else:
                        # Wait for available connection
                        conn = await self._available_connections.get()
                        self._pool_hits += 1
                        logger.debug("Retrieved connection after wait")
            
            self._checked_out.add(conn)
            self._checkout_count += 1
            
            yield conn
            
        finally:
            # Return connection to pool
            if conn and conn in self._checked_out:
                self._checked_out.remove(conn)
                
                # Check if connection is still valid
                try:
                    await conn.execute("SELECT 1")
                    await self._available_connections.put(conn)
                    logger.debug("Returned connection to pool")
                except Exception as e:
                    # Connection is broken, remove it
                    logger.warning(f"Removing broken connection: {e}")
                    async with self._lock:
                        self._all_connections.discard(conn)
                        self._connection_count -= 1
                    
                    try:
                        await conn.close()
                    except Exception as e:
                        logger.warning(f"Error closing connection during cleanup: {e}")
    
    async def execute_query(self, query: str, params: tuple = ()) -> Any:
        """Execute a query using a pooled connection"""
        async with self.get_connection() as conn:
            async with conn.execute(query, params) as cursor:
                return await cursor.fetchall()
    
    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an update/insert/delete using a pooled connection"""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params)
            await conn.commit()
            return cursor.rowcount
    
    async def execute_many(self, query: str, params_list: list) -> int:
        """Execute many operations in a single transaction"""
        async with self.get_connection() as conn:
            cursor = await conn.executemany(query, params_list)
            await conn.commit()
            return cursor.rowcount
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        available_count = self._available_connections.qsize()
        checked_out_count = len(self._checked_out)
        
        return {
            "total_connections": self._connection_count,
            "available_connections": available_count,
            "checked_out_connections": checked_out_count,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "checkout_count": self._checkout_count,
            "pool_hits": self._pool_hits,
            "pool_misses": self._pool_misses,
            "hit_ratio": self._pool_hits / max(self._checkout_count, 1),
        }
    
    async def close_all(self):
        """Close all connections in the pool"""
        async with self._lock:
            # Close all available connections
            while not self._available_connections.empty():
                try:
                    conn = await self._available_connections.get()
                    await conn.close()
                except Exception as e:
                    logger.warning(f"Error closing available connection: {e}")
            
            # Close any remaining connections
            for conn in list(self._all_connections):
                try:
                    await conn.close()
                except Exception as e:
                    logger.warning(f"Error closing checked-out connection: {e}")
            
            self._all_connections.clear()
            self._checked_out.clear()
            self._connection_count = 0
            
        logger.info("Closed all connections in SQLite pool")


# Global connection pool instance (lazy initialization)
_connection_pool: Optional[SQLiteConnectionPool] = None


async def get_connection_pool(
    db_path: str = "data/personas.db",
    pool_size: int = 5,
    max_overflow: int = 10
) -> SQLiteConnectionPool:
    """Get or create the global connection pool"""
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = SQLiteConnectionPool(
            db_path=db_path,
            pool_size=pool_size,
            max_overflow=max_overflow
        )
        await _connection_pool.initialize()
    
    return _connection_pool


async def close_connection_pool():
    """Close the global connection pool"""
    global _connection_pool
    
    if _connection_pool:
        await _connection_pool.close_all()
        _connection_pool = None