"""
Test pagination functionality in neo-commons.
"""

import base64
import json
from datetime import datetime
from neo_commons.repositories.pagination import (
    CursorInfo,
    PaginationParams,
    PaginationType,
    PaginationHelper
)


def test_cursor_encoding_decoding():
    """Test cursor encoding and decoding."""
    # Create cursor info
    cursor = CursorInfo(
        last_id="123e4567-e89b-12d3-a456-426614174000",
        last_value="2024-01-01T00:00:00",
        direction="next",
        limit=20
    )
    
    # Encode cursor
    encoded = cursor.encode()
    print(f"✅ Encoded cursor: {encoded}")
    
    # Decode cursor
    decoded = CursorInfo.decode(encoded)
    assert decoded.last_id == cursor.last_id
    assert decoded.direction == cursor.direction
    assert decoded.limit == cursor.limit
    print("✅ Cursor encoding/decoding works correctly")


def test_pagination_type_detection():
    """Test pagination type detection."""
    # Test offset pagination
    params1 = PaginationParams(page=2, limit=20)
    assert params1.pagination_type == PaginationType.OFFSET
    print("✅ Offset pagination detected correctly")
    
    # Test cursor pagination
    params2 = PaginationParams(cursor="some_cursor", limit=20)
    assert params2.pagination_type == PaginationType.CURSOR
    print("✅ Cursor pagination detected correctly")
    
    # Test keyset pagination
    params3 = PaginationParams(last_id="123", last_value="value", limit=20)
    assert params3.pagination_type == PaginationType.KEYSET
    print("✅ Keyset pagination detected correctly")


def test_offset_calculation():
    """Test offset calculation for pagination."""
    # Test with page
    params = PaginationParams(page=3, limit=20)
    assert params.calculated_offset == 40  # (3-1) * 20
    print("✅ Offset calculation from page works correctly")
    
    # Test with direct offset
    params2 = PaginationParams(offset=50, limit=20)
    assert params2.calculated_offset == 50
    print("✅ Direct offset works correctly")


def test_cursor_pagination_query_building():
    """Test cursor pagination query building."""
    base_query = "SELECT * FROM users"
    params = []
    pagination = PaginationParams(
        cursor=None,
        limit=10,
        order_by="created_at",
        order_direction="DESC"
    )
    
    # Create a cursor info for testing
    cursor_info = CursorInfo(
        last_id="123",
        last_value="2024-01-01",
        direction="next"
    )
    pagination.cursor = cursor_info.encode()
    
    query, params, decoded_cursor = PaginationHelper.build_cursor_pagination_query(
        base_query, params, pagination
    )
    
    assert "LIMIT 11" in query  # limit + 1 for has_more detection
    assert "ORDER BY" in query
    print("✅ Cursor pagination query building works correctly")


def test_keyset_pagination_query_building():
    """Test keyset pagination query building."""
    base_query = "SELECT * FROM users"
    params = []
    pagination = PaginationParams(
        last_id="123",
        last_value="2024-01-01",
        limit=10,
        order_by="created_at",
        order_direction="DESC"
    )
    
    query, params = PaginationHelper.build_keyset_pagination_query(
        base_query, params, pagination
    )
    
    assert "LIMIT 10" in query
    assert "ORDER BY" in query
    assert len(params) == 2  # last_value and last_id
    print("✅ Keyset pagination query building works correctly")


def test_pagination_features():
    """Test various pagination features."""
    print("\n🧪 Testing pagination features in neo-commons...\n")
    
    # Run all tests
    test_cursor_encoding_decoding()
    test_pagination_type_detection()
    test_offset_calculation()
    test_cursor_pagination_query_building()
    test_keyset_pagination_query_building()
    
    print("\n✅ All pagination tests passed successfully!")


if __name__ == "__main__":
    test_pagination_features()