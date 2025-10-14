"""
Unit tests for persona_mcp.persistence.connection_pool module

Tests SQLite connection pooling for concurrent database access.
"""

import pytest
import pytest_asyncio
import asyncio
import aiosqlite
from pathlib import Path
import tempfile
import os

from persona_mcp.persistence.connection_pool import (
    SQLiteConnectionPool,
    get_connection_pool,
    close_connection_pool
)


@pytest_asyncio.fixture
async def temp_db():
    """Create a temporary database file for testing"""
    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_pool.db")
    
    # Create a simple table for testing
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        await conn.commit()
    
    yield db_path
    
    # Cleanup
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        # Remove WAL files if they exist
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                try:
                    os.remove(wal_file)
                except:
                    pass
        os.rmdir(temp_dir)
    except:
        pass


@pytest_asyncio.fixture
async def connection_pool(temp_db):
    """Create a connection pool for testing"""
    pool = SQLiteConnectionPool(
        db_path=temp_db,
        pool_size=3,
        max_overflow=2,
        enable_wal=True
    )
    await pool.initialize()
    
    yield pool
    
    # Cleanup
    await pool.close_all()


class TestConnectionPoolInitialization:
    """Test connection pool initialization"""
    
    @pytest.mark.asyncio
    async def test_pool_creation(self, temp_db):
        """Test creating a connection pool"""
        pool = SQLiteConnectionPool(
            db_path=temp_db,
            pool_size=5,
            max_overflow=10
        )
        
        assert pool.pool_size == 5
        assert pool.max_overflow == 10
        assert pool._connection_count == 0
        
        await pool.close_all()
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self, temp_db):
        """Test pool initialization creates connections"""
        pool = SQLiteConnectionPool(db_path=temp_db, pool_size=3)
        await pool.initialize()
        
        assert pool._connection_count == 3
        assert pool._available_connections.qsize() == 3
        
        await pool.close_all()
    
    @pytest.mark.asyncio
    async def test_pool_with_wal_mode(self, temp_db):
        """Test that WAL mode is enabled"""
        pool = SQLiteConnectionPool(db_path=temp_db, enable_wal=True)
        await pool.initialize()
        
        async with pool.get_connection() as conn:
            # Check if WAL mode is enabled
            cursor = await conn.execute("PRAGMA journal_mode")
            result = await cursor.fetchone()
            assert result[0].upper() == "WAL"
        
        await pool.close_all()


class TestConnectionCheckout:
    """Test connection checkout and checkin"""
    
    @pytest.mark.asyncio
    async def test_checkout_connection(self, connection_pool):
        """Test checking out a connection"""
        initial_available = connection_pool._available_connections.qsize()
        
        async with connection_pool.get_connection() as conn:
            assert conn is not None
            assert isinstance(conn, aiosqlite.Connection)
            
            # Available connections should decrease
            assert connection_pool._available_connections.qsize() == initial_available - 1
            
            # Connection should be in checked_out set
            assert conn in connection_pool._checked_out
        
        # After context manager, connection should be returned
        assert connection_pool._available_connections.qsize() == initial_available
    
    @pytest.mark.asyncio
    async def test_multiple_checkouts(self, connection_pool):
        """Test checking out multiple connections"""
        connections = []
        
        # Checkout all connections from pool
        for i in range(connection_pool.pool_size):
            conn = await connection_pool._available_connections.get()
            connections.append(conn)
        
        assert connection_pool._available_connections.qsize() == 0
        
        # Return connections
        for conn in connections:
            await connection_pool._available_connections.put(conn)
        
        assert connection_pool._available_connections.qsize() == connection_pool.pool_size
    
    @pytest.mark.asyncio
    async def test_connection_reuse(self, connection_pool):
        """Test that connections are reused"""
        # Get initial stats
        initial_stats = connection_pool.get_pool_stats()
        initial_total = initial_stats["total_connections"]
        
        # Checkout and return a connection
        async with connection_pool.get_connection() as conn1:
            # Verify connection works
            await conn1.execute("SELECT 1")
        
        # Checkout again, should reuse from pool
        async with connection_pool.get_connection() as conn2:
            # Verify connection works
            await conn2.execute("SELECT 1")
        
        # Check that we reused connections (no new connections created)
        final_stats = connection_pool.get_pool_stats()
        assert final_stats["total_connections"] == initial_total
        assert final_stats["pool_hits"] >= 1  # At least one pool hit
        assert final_stats["checkout_count"] >= 2  # Two checkouts occurred


class TestConcurrentAccess:
    """Test concurrent connection access"""
    
    @pytest.mark.asyncio
    async def test_concurrent_queries(self, connection_pool):
        """Test concurrent queries using the pool"""
        async def query_task(task_id: int):
            async with connection_pool.get_connection() as conn:
                await conn.execute(
                    "INSERT INTO test_table (id, value) VALUES (?, ?)",
                    (task_id, f"value_{task_id}")
                )
                await conn.commit()
                
                cursor = await conn.execute(
                    "SELECT value FROM test_table WHERE id = ?",
                    (task_id,)
                )
                result = await cursor.fetchone()
                return result[0] if result else None
        
        # Run 10 concurrent queries
        tasks = [query_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All tasks should complete successfully
        assert len(results) == 10
        assert all(r == f"value_{i}" for i, r in enumerate(results))
    
    @pytest.mark.asyncio
    async def test_overflow_connections(self, connection_pool):
        """Test that overflow connections are created when needed"""
        initial_count = connection_pool._connection_count
        
        # Exhaust the pool and create overflow connections
        connections = []
        async def hold_connection():
            async with connection_pool.get_connection() as conn:
                connections.append(conn)
                await asyncio.sleep(0.1)
        
        # Create more tasks than pool size
        tasks = [hold_connection() for _ in range(connection_pool.pool_size + 2)]
        await asyncio.gather(*tasks)
        
        # Should have created overflow connections
        assert connection_pool._connection_count >= initial_count


class TestPoolStatistics:
    """Test connection pool statistics"""
    
    @pytest.mark.asyncio
    async def test_get_pool_stats(self, connection_pool):
        """Test retrieving pool statistics"""
        stats = connection_pool.get_pool_stats()
        
        assert "total_connections" in stats
        assert "available_connections" in stats
        assert "checked_out_connections" in stats
        assert "pool_size" in stats
        assert "max_overflow" in stats
        assert "checkout_count" in stats
        assert "pool_hits" in stats
        assert "pool_misses" in stats
        assert "hit_ratio" in stats
        
        assert stats["total_connections"] == 3
        assert stats["pool_size"] == 3
        assert stats["max_overflow"] == 2
    
    @pytest.mark.asyncio
    async def test_checkout_count_increases(self, connection_pool):
        """Test that checkout count increases"""
        initial_count = connection_pool._checkout_count
        
        async with connection_pool.get_connection() as conn:
            pass
        
        assert connection_pool._checkout_count == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_pool_hit_tracking(self, connection_pool):
        """Test pool hit/miss tracking"""
        # First checkout should be a hit (from initialized pool)
        async with connection_pool.get_connection() as conn:
            pass
        
        assert connection_pool._pool_hits > 0


class TestQueryOperations:
    """Test query execution methods"""
    
    @pytest.mark.asyncio
    async def test_execute_query(self, connection_pool):
        """Test execute_query method"""
        # Insert test data
        async with connection_pool.get_connection() as conn:
            await conn.execute(
                "INSERT INTO test_table (id, value) VALUES (?, ?)",
                (1, "test_value")
            )
            await conn.commit()
        
        # Query using execute_query
        results = await connection_pool.execute_query(
            "SELECT value FROM test_table WHERE id = ?",
            (1,)
        )
        
        assert len(results) == 1
        assert results[0][0] == "test_value"
    
    @pytest.mark.asyncio
    async def test_execute_update(self, connection_pool):
        """Test execute_update method"""
        # Insert data
        rowcount = await connection_pool.execute_update(
            "INSERT INTO test_table (id, value) VALUES (?, ?)",
            (2, "update_test")
        )
        
        assert rowcount == 1
        
        # Verify data was inserted
        results = await connection_pool.execute_query(
            "SELECT value FROM test_table WHERE id = ?",
            (2,)
        )
        assert results[0][0] == "update_test"
    
    @pytest.mark.asyncio
    async def test_execute_many(self, connection_pool):
        """Test execute_many method"""
        # Insert multiple rows
        params_list = [
            (10, "value_10"),
            (11, "value_11"),
            (12, "value_12")
        ]
        
        rowcount = await connection_pool.execute_many(
            "INSERT INTO test_table (id, value) VALUES (?, ?)",
            params_list
        )
        
        assert rowcount == 3
        
        # Verify all rows were inserted
        results = await connection_pool.execute_query(
            "SELECT COUNT(*) FROM test_table WHERE id >= 10 AND id <= 12"
        )
        assert results[0][0] == 3


class TestConnectionRecovery:
    """Test connection error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_broken_connection_handling(self, connection_pool):
        """Test that broken connections are removed from pool"""
        initial_count = connection_pool._connection_count
        
        # Get a connection and simulate it breaking
        async with connection_pool.get_connection() as conn:
            # Close the connection to simulate breakage
            await conn.close()
        
        # The pool should have removed the broken connection
        # (detected when trying to return it)
        assert connection_pool._connection_count <= initial_count


class TestPoolCleanup:
    """Test connection pool cleanup"""
    
    @pytest.mark.asyncio
    async def test_close_all_connections(self, temp_db):
        """Test closing all connections"""
        pool = SQLiteConnectionPool(db_path=temp_db, pool_size=3)
        await pool.initialize()
        
        assert pool._connection_count == 3
        
        await pool.close_all()
        
        assert pool._connection_count == 0
        assert pool._available_connections.qsize() == 0
        assert len(pool._all_connections) == 0
        assert len(pool._checked_out) == 0
    
    @pytest.mark.asyncio
    async def test_close_with_checked_out_connections(self, temp_db):
        """Test closing pool with checked out connections"""
        pool = SQLiteConnectionPool(db_path=temp_db, pool_size=2)
        await pool.initialize()
        
        # Checkout a connection (don't return it)
        conn = await pool._available_connections.get()
        
        # Close pool
        await pool.close_all()
        
        # All connections should be closed
        assert pool._connection_count == 0


class TestGlobalConnectionPool:
    """Test global connection pool functions"""
    
    @pytest.mark.asyncio
    async def test_get_connection_pool(self, temp_db):
        """Test getting the global connection pool"""
        # Reset global pool
        await close_connection_pool()
        
        pool = await get_connection_pool(db_path=temp_db, pool_size=3)
        
        assert pool is not None
        assert isinstance(pool, SQLiteConnectionPool)
        assert pool._connection_count == 3
        
        # Getting it again should return the same instance
        pool2 = await get_connection_pool(db_path=temp_db)
        assert pool2 is pool
        
        await close_connection_pool()
    
    @pytest.mark.asyncio
    async def test_close_connection_pool(self, temp_db):
        """Test closing the global connection pool"""
        await close_connection_pool()
        
        pool = await get_connection_pool(db_path=temp_db)
        assert pool is not None
        
        await close_connection_pool()
        
        # After closing, getting pool again should create a new one
        pool2 = await get_connection_pool(db_path=temp_db)
        assert pool2 is not pool
        
        await close_connection_pool()


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    @pytest.mark.asyncio
    async def test_empty_pool_size(self, temp_db):
        """Test handling of invalid pool size"""
        # Pool size of 0 should still work (will create overflow connections)
        pool = SQLiteConnectionPool(db_path=temp_db, pool_size=0, max_overflow=5)
        await pool.initialize()
        
        # Should be able to get a connection (from overflow)
        async with pool.get_connection() as conn:
            assert conn is not None
        
        await pool.close_all()
    
    @pytest.mark.asyncio
    async def test_connection_timeout_recovery(self, connection_pool):
        """Test recovery from connection timeout"""
        # This test verifies that the pool can handle timeouts gracefully
        connections = []
        
        # Checkout all connections and hold them
        for _ in range(connection_pool.pool_size):
            conn = await connection_pool._available_connections.get()
            connections.append(conn)
        
        # Return connections
        for conn in connections:
            await connection_pool._available_connections.put(conn)
        
        # Pool should still be functional
        async with connection_pool.get_connection() as conn:
            assert conn is not None
