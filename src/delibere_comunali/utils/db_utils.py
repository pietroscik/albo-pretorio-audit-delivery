"""
Database Utilities Module.

This module provides utilities for database operations:

- Connection pooling
- Query optimization
- Batch operations
- Index management
- Caching layer

Key Features:
- Connection pooling with SQLAlchemy
- Batch insert/update operations
- Query optimization helpers
- Index creation and management
- Redis caching integration
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import time
from functools import wraps

from .logger import get_logger
from .cache import LRUCache
from .logger import get_logger
from .config import get_config

logger = get_logger(__name__)


class DatabaseConfig:
    """
    Configuration for database connections.
    """
    
    def __init__(self):
        """Initialize database configuration from config."""
        config = get_config()
        
        self.host = config.get('DB_HOST', 'localhost')
        self.port = config.get_int('DB_PORT', 5432)
        self.name = config.get('DB_NAME', 'albo_pretorio')
        self.user = config.get('DB_USER', 'postgres')
        self.password = config.get('DB_PASSWORD', '')
        self.pool_size = config.get_int('DB_POOL_SIZE', 10)
        self.max_overflow = config.get_int('DB_MAX_OVERFLOW', 20)
        self.pool_timeout = config.get_int('DB_POOL_TIMEOUT', 30)
        self.pool_recycle = config.get_int('DB_POOL_RECYCLE', 3600)
    
    def get_connection_string(self) -> str:
        """Get the database connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without password)."""
        return {
            'host': self.host,
            'port': self.port,
            'name': self.name,
            'user': self.user,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'pool_recycle': self.pool_recycle
        }


class ConnectionPool:
    """
    Connection pool for PostgreSQL database.
    
    Uses SQLAlchemy for connection pooling.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize the connection pool.
        
        Args:
            config: Database configuration
        """
        self.config = config or DatabaseConfig()
        self._engine = None
        self._session_factory = None
    
    def get_engine(self):
        """
        Get the SQLAlchemy engine.
        
        Returns:
            SQLAlchemy engine
        """
        if self._engine is None:
            try:
                from sqlalchemy import create_engine
                from sqlalchemy.pool import QueuePool
                
                connection_string = self.config.get_connection_string()
                
                self._engine = create_engine(
                    connection_string,
                    poolclass=QueuePool,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    pool_timeout=self.config.pool_timeout,
                    pool_recycle=self.config.pool_recycle,
                    pool_pre_ping=True,
                    echo=False
                )
                
                logger.info(f"Database connection pool created: {connection_string}")
                
            except ImportError:
                logger.error("SQLAlchemy not available for connection pooling")
                raise
        
        return self._engine
    
    def get_session(self):
        """
        Get a database session.
        
        Returns:
            SQLAlchemy session
        """
        if self._session_factory is None:
            try:
                from sqlalchemy.orm import sessionmaker
                engine = self.get_engine()
                self._session_factory = sessionmaker(bind=engine)
            except ImportError:
                logger.error("SQLAlchemy not available for session creation")
                raise
        
        return self._session_factory()
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a SQL query and return results as dictionaries.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result dictionaries
        """
        try:
            session = self.get_session()
            result = session.execute(query, params or {})
            
            # Convert to list of dictionaries
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            
            session.close()
            return rows
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def execute_batch_insert(
        self, 
        table: str, 
        data: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """
        Execute batch insert operation.
        
        Args:
            table: Table name
            data: List of dictionaries with data to insert
            batch_size: Number of records per batch
            
        Returns:
            Number of records inserted
        """
        if not data:
            return 0
        
        try:
            session = self.get_session()
            
            # Get table metadata
            from sqlalchemy import Table, MetaData
            metadata = MetaData()
            table_obj = Table(table, metadata, autoload_with=self.get_engine())
            
            # Insert in batches
            inserted_count = 0
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                stmt = table_obj.insert().values(batch)
                result = session.execute(stmt)
                inserted_count += result.rowcount
                session.commit()
            
            session.close()
            logger.info(f"Batch inserted {inserted_count} records into {table}")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error in batch insert: {e}")
            raise
    
    def execute_batch_update(
        self, 
        table: str, 
        updates: Dict[str, Any],
        where_clause: Optional[str] = None,
        where_params: Optional[Dict] = None
    ) -> int:
        """
        Execute batch update operation.
        
        Args:
            table: Table name
            updates: Dictionary of column: value to update
            where_clause: WHERE clause (optional)
            where_params: Parameters for WHERE clause (optional)
            
        Returns:
            Number of records updated
        """
        try:
            session = self.get_session()
            
            # Get table metadata
            from sqlalchemy import Table, MetaData, update
            metadata = MetaData()
            table_obj = Table(table, metadata, autoload_with=self.get_engine())
            
            # Build update statement
            stmt = update(table_obj).values(**updates)
            
            if where_clause:
                stmt = stmt.where(where_clause)
            
            result = session.execute(stmt, where_params or {})
            session.commit()
            
            updated_count = result.rowcount
            session.close()
            
            logger.info(f"Batch updated {updated_count} records in {table}")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in batch update: {e}")
            raise
    
    def close(self):
        """Close the connection pool."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connection pool closed")


class QueryOptimizer:
    """
    Query optimizer for PostgreSQL.
    
    Provides helpers for:
    - Adding indexes
    - Analyzing query performance
    - Optimizing slow queries
    - Caching query results
    """
    
    def __init__(self, pool: Optional[ConnectionPool] = None):
        """
        Initialize the query optimizer.
        
        Args:
            pool: Connection pool
        """
        self.pool = pool or ConnectionPool()
        self._query_cache = LRUCache(max_size=1000, default_ttl=300)  # 5 minutes
    
    def create_index(
        self, 
        table: str, 
        columns: List[str],
        index_name: Optional[str] = None,
        unique: bool = False
    ) -> bool:
        """
        Create an index on a table.
        
        Args:
            table: Table name
            columns: List of columns to index
            index_name: Name for the index (generated if None)
            unique: Whether to create a unique index
            
        Returns:
            True if index created successfully
        """
        try:
            if not index_name:
                index_name = f"idx_{table}_{'_'.join(columns)}"
            
            columns_str = ', '.join(columns)
            unique_str = "UNIQUE" if unique else ""
            
            query = f"""
                CREATE {unique_str} INDEX IF NOT EXISTS {index_name} 
                ON {table} ({columns_str})
            """
            
            self.pool.execute_query(query)
            logger.info(f"Created index {index_name} on {table}({columns_str})")
            return True
            
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return False
    
    def analyze_table(self, table: str) -> Dict[str, Any]:
        """
        Analyze a table and return statistics.
        
        Args:
            table: Table name
            
        Returns:
            Dictionary with table statistics
        """
        try:
            # Get table info
            query = f"""
                SELECT 
                    table_name,
                    pg_size_pretty(pg_total_relation_size(table_name)) as size,
                    pg_total_relation_size(table_name) as size_bytes,
                    (SELECT reltuples FROM pg_class WHERE relname = table_name) as row_count
                FROM information_schema.tables 
                WHERE table_name = '{table}'
            """
            
            result = self.pool.execute_query(query)
            if not result:
                return {}
            
            stats = result[0]
            
            # Get column info
            query = f"""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    (SELECT n_distinct FROM pg_stats 
                     WHERE tablename = '{table}' AND attname = column_name) as distinct_count
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """
            
            columns = self.pool.execute_query(query)
            stats['columns'] = columns
            
            return stats
            
        except Exception as e:
            logger.error(f"Error analyzing table: {e}")
            return {}
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the slowest queries from PostgreSQL log.
        
        Note: Requires pg_stat_statements extension to be enabled.
        
        Args:
            limit: Number of queries to return
            
        Returns:
            List of slow queries with statistics
        """
        try:
            query = f"""
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    stddev_time,
                    rows
                FROM pg_stat_statements 
                ORDER BY mean_time DESC 
                LIMIT {limit}
            """
            
            return self.pool.execute_query(query)
            
        except Exception as e:
            logger.error(f"Error getting slow queries: {e}")
            return []
    
    def explain_query(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Get the execution plan for a query.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of execution plan steps
        """
        try:
            explain_query = f"EXPLAIN ANALYZE {query}"
            return self.pool.execute_query(explain_query, params)
            
        except Exception as e:
            logger.error(f"Error explaining query: {e}")
            return []
    
    def cache_query(
        self, 
        query: str, 
        params: Optional[Dict] = None,
        ttl: int = 300
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a query with caching.
        
        Args:
            query: SQL query
            params: Query parameters
            ttl: Cache time-to-live in seconds
            
        Returns:
            Query results (from cache if available)
        """
        # Generate cache key
        params_str = json.dumps(params or {}, sort_keys=True)
        cache_key = hashlib.md5(f"{query}|{params_str}".encode()).hexdigest()
        
        # Check cache
        cached_result = self._query_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {cache_key[:8]}...")
            return cached_result
        
        # Execute query
        result = self.pool.execute_query(query, params)
        
        # Cache result
        self._query_cache.set(cache_key, result, ttl=ttl)
        logger.debug(f"Cached query result: {cache_key[:8]}...")
        
        return result
    
    def clear_query_cache(self):
        """Clear the query cache."""
        self._query_cache = LRUCache(max_size=1000, default_ttl=300)
        logger.info("Query cache cleared")


class RedisCache:
    """
    Redis caching layer for database queries.
    
    Provides:
    - Key-value caching
    - Time-to-live support
    - Serialization/deserialization
    - Connection pooling
    """
    
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
        """
        config = get_config()
        self.host = host or config.get('REDIS_HOST', 'localhost')
        self.port = port or config.get_int('REDIS_PORT', 6379)
        self.password = config.get('REDIS_PASSWORD', '')
        self.db = config.get_int('REDIS_DB', 0)
        
        self._client = None
    
    def get_client(self):
        """Get Redis client."""
        if self._client is None:
            try:
                import redis
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    db=self.db,
                    decode_responses=True
                )
                # Test connection
                self._client.ping()
                logger.info(f"Connected to Redis at {self.host}:{self.port}")
            except ImportError:
                logger.error("redis package not available")
                raise
            except Exception as e:
                logger.error(f"Error connecting to Redis: {e}")
                raise
        
        return self._client
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be serialized to JSON)
            ttl: Time-to-live in seconds (None = no expiry)
            
        Returns:
            True if successful
        """
        try:
            client = self.get_client()
            
            # Serialize value to JSON
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            
            # Set with optional TTL
            if ttl:
                client.setex(key, ttl, value_str)
            else:
                client.set(key, value_str)
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            client = self.get_client()
            value_str = client.get(key)
            
            if value_str is None:
                return None
            
            # Try to deserialize as JSON
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                return value_str
                
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful
        """
        try:
            client = self.get_client()
            return bool(client.delete(key))
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        try:
            client = self.get_client()
            return client.exists(key)
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache keys.
        
        Args:
            pattern: Optional pattern to match keys (None = clear all)
            
        Returns:
            Number of keys deleted
        """
        try:
            client = self.get_client()
            
            if pattern:
                # Find and delete keys matching pattern
                keys = client.keys(pattern)
                deleted = client.delete(*keys)
                return deleted
            else:
                # Clear entire database
                return client.flushdb()
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis statistics.
        
        Returns:
            Dictionary with Redis stats
        """
        try:
            client = self.get_client()
            info = client.info()
            return {
                'connected': True,
                'used_memory': info.get('used_memory_human', 'unknown'),
                'keys': info.get('db0', {}).get('keys', 0),
                'uptime': info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            return {'connected': False, 'error': str(e)}


# Global instances
_db_pool: Optional[ConnectionPool] = None
_query_optimizer: Optional[QueryOptimizer] = None
_redis_cache: Optional[RedisCache] = None


def get_db_pool() -> ConnectionPool:
    """Get the global database connection pool."""
    global _db_pool
    if _db_pool is None:
        _db_pool = ConnectionPool()
    return _db_pool


def get_query_optimizer() -> QueryOptimizer:
    """Get the global query optimizer."""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    return _query_optimizer


def get_redis_cache() -> RedisCache:
    """Get the global Redis cache."""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache


def with_db_session(func):
    """
    Decorator for functions that need a database session.
    
    Automatically creates and closes a session.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        pool = get_db_pool()
        session = pool.get_session()
        try:
            result = func(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    return wrapper


def cached_query(ttl: int = 300):
    """
    Decorator for caching query results.
    
    Args:
        ttl: Cache time-to-live in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            optimizer = get_query_optimizer()
            
            # Generate cache key from function name and arguments
            key = f"{func.__name__}:{hash(frozenset(kwargs.items()))}"
            
            # Check cache
            cached = optimizer._query_cache.get(key)
            if cached is not None:
                return cached
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            optimizer._query_cache.set(key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator
