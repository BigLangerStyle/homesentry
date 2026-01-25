#!/usr/bin/env python3
"""
Test script to verify database operations

This script tests the database initialization and basic operations
without needing to run the full FastAPI application.

Usage:
    python test_database.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set test database path
os.environ["DATABASE_PATH"] = "data/homesentry_test.db"

from app.storage import (
    init_database,
    insert_metric_sample,
    insert_service_status,
    insert_event,
    get_latest_metrics,
    get_latest_events,
    get_latest_service_status,
)


async def test_database():
    """Run database tests"""
    print("=" * 60)
    print("Testing HomeSentry Database Operations")
    print("=" * 60)
    
    # Test 1: Initialize database
    print("\n[TEST 1] Initializing database...")
    success = await init_database()
    if success:
        print("✓ Database initialized successfully")
    else:
        print("✗ Database initialization failed")
        return False
    
    # Test 2: Insert metric sample
    print("\n[TEST 2] Inserting metric sample...")
    success = await insert_metric_sample(
        category="system",
        name="cpu_percent",
        value_num=45.2,
        status="OK"
    )
    if success:
        print("✓ Metric sample inserted")
    else:
        print("✗ Failed to insert metric sample")
        return False
    
    # Test 3: Insert service status
    print("\n[TEST 3] Inserting service status...")
    success = await insert_service_status(
        service="plex",
        status="OK",
        response_ms=42.5,
        http_code=200
    )
    if success:
        print("✓ Service status inserted")
    else:
        print("✗ Failed to insert service status")
        return False
    
    # Test 4: Insert event
    print("\n[TEST 4] Inserting event...")
    success = await insert_event(
        event_key="test_event",
        new_status="WARN",
        message="This is a test event",
        prev_status="OK"
    )
    if success:
        print("✓ Event inserted")
    else:
        print("✗ Failed to insert event")
        return False
    
    # Test 5: Query metrics
    print("\n[TEST 5] Querying metrics...")
    metrics = await get_latest_metrics(category="system", limit=5)
    print(f"✓ Retrieved {len(metrics)} metric(s)")
    if metrics:
        print(f"  Sample: {metrics[0]['name']} = {metrics[0]['value_num']}")
    
    # Test 6: Query service status
    print("\n[TEST 6] Querying service status...")
    statuses = await get_latest_service_status(service="plex", limit=5)
    print(f"✓ Retrieved {len(statuses)} status check(s)")
    if statuses:
        print(f"  Sample: {statuses[0]['service']} = {statuses[0]['status']} (HTTP {statuses[0]['http_code']})")
    
    # Test 7: Query events
    print("\n[TEST 7] Querying events...")
    events = await get_latest_events(limit=5)
    print(f"✓ Retrieved {len(events)} event(s)")
    if events:
        print(f"  Sample: {events[0]['event_key']} ({events[0]['prev_status']} -> {events[0]['new_status']})")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    print(f"\nTest database created at: {os.getenv('DATABASE_PATH')}")
    print("You can inspect it with: sqlite3 data/homesentry_test.db")
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_database())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
