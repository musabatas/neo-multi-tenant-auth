#!/bin/bash

# ============================================================================
# Organization API Comprehensive Test Suite
# ============================================================================
# Tests all basic organization endpoints using curl commands
# Base URL: http://localhost:8001/api/v1/organizations
# 
# Usage: ./test_organizations_api.sh
# ============================================================================

set -e

# Configuration
BASE_URL="http://localhost:8001/api/v1/organizations"
TEMP_DIR="/tmp/org_tests"
mkdir -p "$TEMP_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

run_test() {
    local test_name="$1"
    local curl_command="$2"
    local expected_status="$3"
    local description="$4"
    
    ((TESTS_RUN++))
    
    log_info "Running: $test_name"
    log_info "Description: $description"
    log_info "Command: $curl_command"
    
    # Execute curl command and capture response
    local response_file="$TEMP_DIR/response_${TESTS_RUN}.json"
    local status_code
    
    # Run curl command and capture both response body and status code
    status_code=$(eval "$curl_command -w '%{http_code}' -s -o '$response_file'")
    
    # Check status code
    if [[ "$status_code" == "$expected_status" ]]; then
        log_success "✓ Status code: $status_code (expected: $expected_status)"
        
        # Show response if it's JSON
        if [[ -s "$response_file" ]]; then
            echo "Response:"
            cat "$response_file" | python3 -m json.tool 2>/dev/null || cat "$response_file"
        fi
        
        # Store response for later tests if needed
        cp "$response_file" "$TEMP_DIR/${test_name}_response.json" 2>/dev/null || true
        
    else
        log_error "✗ Status code: $status_code (expected: $expected_status)"
        echo "Response:"
        cat "$response_file" 2>/dev/null || echo "(No response body)"
    fi
    
    echo "----------------------------------------"
}

# ============================================================================
# TEST SUITE START
# ============================================================================

echo "============================================================================"
echo "ORGANIZATION API COMPREHENSIVE TEST SUITE"
echo "============================================================================"
echo "Testing against: $BASE_URL"
echo "Started at: $(date)"
echo ""

# ============================================================================
# 1. LIST ORGANIZATIONS (GET /)
# ============================================================================

log_info "=== LISTING TESTS ==="

run_test "list_default" \
    "curl '$BASE_URL/'" \
    "200" \
    "List organizations with default pagination"

run_test "list_paginated" \
    "curl '$BASE_URL/?page=1&per_page=5'" \
    "200" \
    "List organizations with custom pagination"

run_test "list_active_only" \
    "curl '$BASE_URL/?active_only=true'" \
    "200" \
    "List only active organizations"

run_test "list_verified_only" \
    "curl '$BASE_URL/?verified_only=true'" \
    "200" \
    "List only verified organizations"

run_test "list_by_industry" \
    "curl '$BASE_URL/?industry=Technology'" \
    "200" \
    "Filter organizations by industry"

run_test "list_by_country" \
    "curl '$BASE_URL/?country_code=US'" \
    "200" \
    "Filter organizations by country code"

run_test "list_combined_filters" \
    "curl '$BASE_URL/?page=1&per_page=10&active_only=true&industry=Technology'" \
    "200" \
    "List with combined filters and pagination"

# ============================================================================
# 2. GET ORGANIZATION BY ID (GET /{id})
# ============================================================================

log_info "=== GET BY ID TESTS ==="

# Use a known organization ID from the list response
KNOWN_ORG_ID="0198be94-d49a-70d2-8660-3f7e8de47e25"

run_test "get_by_id_valid" \
    "curl '$BASE_URL/$KNOWN_ORG_ID'" \
    "200" \
    "Get organization by valid ID"

run_test "get_by_id_invalid" \
    "curl '$BASE_URL/invalid-uuid'" \
    "422" \
    "Get organization with invalid UUID format"

run_test "get_by_id_not_found" \
    "curl '$BASE_URL/0198be94-d49a-70d2-8660-000000000000'" \
    "404" \
    "Get organization with valid UUID but non-existent ID"

# ============================================================================
# 3. GET ORGANIZATION BY SLUG (GET /slug/{slug})
# ============================================================================

log_info "=== GET BY SLUG TESTS ==="

run_test "get_by_slug_valid" \
    "curl '$BASE_URL/slug/acme-corp'" \
    "200" \
    "Get organization by valid slug"

run_test "get_by_slug_not_found" \
    "curl '$BASE_URL/slug/non-existent-org'" \
    "404" \
    "Get organization by non-existent slug"

# ============================================================================
# 4. CREATE ORGANIZATION (POST /)
# ============================================================================

log_info "=== CREATE TESTS ==="

# Test data for organization creation
CREATE_DATA_MINIMAL='{
    "name": "Test Organization Minimal",
    "slug": "test-org-minimal",
    "industry": "Technology"
}'

CREATE_DATA_COMPLETE='{
    "name": "Test Organization Complete",
    "slug": "test-org-complete", 
    "legal_name": "Test Organization Complete LLC",
    "tax_id": "12-3456789",
    "business_type": "LLC",
    "industry": "Technology",
    "company_size": "51-200",
    "website_url": "https://test-org-complete.com",
    "address_line1": "123 Test Street",
    "city": "San Francisco",
    "state_province": "CA",
    "postal_code": "94105",
    "country_code": "US",
    "default_timezone": "America/Los_Angeles",
    "default_locale": "en-US",
    "default_currency": "USD",
    "brand_colors": {"primary": "#007bff", "secondary": "#6c757d"},
    "metadata": {"source": "api_test", "version": "1.0"}
}'

run_test "create_minimal" \
    "curl -X POST '$BASE_URL/' -H 'Content-Type: application/json' -d '$CREATE_DATA_MINIMAL'" \
    "201" \
    "Create organization with minimal required fields"

run_test "create_complete" \
    "curl -X POST '$BASE_URL/' -H 'Content-Type: application/json' -d '$CREATE_DATA_COMPLETE'" \
    "201" \
    "Create organization with all fields populated"

run_test "create_duplicate_slug" \
    "curl -X POST '$BASE_URL/' -H 'Content-Type: application/json' -d '$CREATE_DATA_MINIMAL'" \
    "409" \
    "Create organization with duplicate slug (should fail)"

run_test "create_invalid_data" \
    "curl -X POST '$BASE_URL/' -H 'Content-Type: application/json' -d '{\"name\": \"\"}'" \
    "422" \
    "Create organization with invalid/empty data"

run_test "create_missing_fields" \
    "curl -X POST '$BASE_URL/' -H 'Content-Type: application/json' -d '{\"name\": \"Incomplete Org\"}'" \
    "422" \
    "Create organization missing required fields"

# ============================================================================
# 5. UPDATE ORGANIZATION (PUT /{id})
# ============================================================================

log_info "=== UPDATE TESTS ==="

# Get organization ID from create response for update tests
if [[ -f "$TEMP_DIR/create_minimal_response.json" ]]; then
    CREATED_ORG_ID=$(python3 -c "import json; print(json.load(open('$TEMP_DIR/create_minimal_response.json'))['id'])" 2>/dev/null || echo "$KNOWN_ORG_ID")
else
    CREATED_ORG_ID="$KNOWN_ORG_ID"
fi

UPDATE_DATA='{
    "name": "Updated Test Organization",
    "website_url": "https://updated-test-org.com",
    "metadata": {"updated": true, "version": "1.1"}
}'

run_test "update_organization" \
    "curl -X PUT '$BASE_URL/$CREATED_ORG_ID' -H 'Content-Type: application/json' -d '$UPDATE_DATA'" \
    "200" \
    "Update existing organization"

run_test "update_not_found" \
    "curl -X PUT '$BASE_URL/0198be94-d49a-70d2-8660-000000000000' -H 'Content-Type: application/json' -d '$UPDATE_DATA'" \
    "404" \
    "Update non-existent organization"

run_test "update_invalid_id" \
    "curl -X PUT '$BASE_URL/invalid-uuid' -H 'Content-Type: application/json' -d '$UPDATE_DATA'" \
    "422" \
    "Update organization with invalid UUID"

# ============================================================================
# 6. SEARCH ORGANIZATIONS (POST /search)
# ============================================================================

log_info "=== SEARCH TESTS ==="

SEARCH_DATA_BASIC='{
    "query": "Test",
    "limit": 10
}'

SEARCH_DATA_FILTERED='{
    "query": "Organization", 
    "filters": {
        "industry": "Technology",
        "is_active": true
    },
    "limit": 5
}'

run_test "search_basic" \
    "curl -X POST '$BASE_URL/search' -H 'Content-Type: application/json' -d '$SEARCH_DATA_BASIC'" \
    "200" \
    "Basic organization search"

run_test "search_with_filters" \
    "curl -X POST '$BASE_URL/search' -H 'Content-Type: application/json' -d '$SEARCH_DATA_FILTERED'" \
    "200" \
    "Search organizations with filters"

run_test "search_empty_query" \
    "curl -X POST '$BASE_URL/search' -H 'Content-Type: application/json' -d '{\"query\": \"\", \"limit\": 5}'" \
    "200" \
    "Search with empty query"

# ============================================================================
# 7. ORGANIZATION LIFECYCLE (verify, activate, deactivate)
# ============================================================================

log_info "=== LIFECYCLE TESTS ==="

run_test "verify_organization" \
    "curl -X POST '$BASE_URL/$CREATED_ORG_ID/verify' -H 'Content-Type: application/json' -d '[\"document1.pdf\", \"document2.pdf\"]'" \
    "200" \
    "Verify organization with documents"

run_test "deactivate_organization" \
    "curl -X POST '$BASE_URL/$CREATED_ORG_ID/deactivate?reason=testing'" \
    "200" \
    "Deactivate organization with reason"

run_test "activate_organization" \
    "curl -X POST '$BASE_URL/$CREATED_ORG_ID/activate'" \
    "200" \
    "Activate previously deactivated organization"

run_test "verify_not_found" \
    "curl -X POST '$BASE_URL/0198be94-d49a-70d2-8660-000000000000/verify' -H 'Content-Type: application/json' -d '[]'" \
    "404" \
    "Verify non-existent organization"

# ============================================================================
# 8. METADATA OPERATIONS
# ============================================================================

log_info "=== METADATA TESTS ==="

run_test "get_metadata" \
    "curl '$BASE_URL/$CREATED_ORG_ID/metadata'" \
    "200" \
    "Get organization metadata"

METADATA_UPDATE='{
    "metadata": {"new_field": "new_value", "updated_at": "2024-01-01"},
    "merge": true
}'

run_test "update_metadata" \
    "curl -X PUT '$BASE_URL/$CREATED_ORG_ID/metadata' -H 'Content-Type: application/json' -d '$METADATA_UPDATE'" \
    "200" \
    "Update organization metadata with merge"

METADATA_REPLACE='{
    "metadata": {"only_field": "only_value"},
    "merge": false
}'

run_test "replace_metadata" \
    "curl -X PUT '$BASE_URL/$CREATED_ORG_ID/metadata' -H 'Content-Type: application/json' -d '$METADATA_REPLACE'" \
    "200" \
    "Replace organization metadata completely"

run_test "get_metadata_not_found" \
    "curl '$BASE_URL/0198be94-d49a-70d2-8660-000000000000/metadata'" \
    "404" \
    "Get metadata for non-existent organization"

# ============================================================================
# 9. DELETE ORGANIZATION (DELETE /{id})  
# ============================================================================

log_info "=== DELETE TESTS ==="

# Create a temporary organization for deletion tests
DELETE_TEST_DATA='{
    "name": "To Be Deleted Organization",
    "slug": "to-be-deleted-org",
    "industry": "Technology"
}'

# Create org for deletion
TEMP_RESPONSE=$(mktemp)
DELETE_ORG_STATUS=$(curl -X POST "$BASE_URL/" -H 'Content-Type: application/json' -d "$DELETE_TEST_DATA" -w '%{http_code}' -s -o "$TEMP_RESPONSE")

if [[ "$DELETE_ORG_STATUS" == "201" ]]; then
    DELETE_ORG_ID=$(python3 -c "import json; print(json.load(open('$TEMP_RESPONSE'))['id'])" 2>/dev/null || echo "")
    
    if [[ -n "$DELETE_ORG_ID" ]]; then
        run_test "delete_soft" \
            "curl -X DELETE '$BASE_URL/$DELETE_ORG_ID'" \
            "204" \
            "Soft delete organization"
            
        run_test "delete_hard" \
            "curl -X DELETE '$BASE_URL/$DELETE_ORG_ID?hard_delete=true'" \
            "204" \
            "Hard delete organization"
    else
        log_warning "Could not extract organization ID for delete tests"
    fi
else
    log_warning "Could not create organization for delete tests (status: $DELETE_ORG_STATUS)"
fi

run_test "delete_not_found" \
    "curl -X DELETE '$BASE_URL/0198be94-d49a-70d2-8660-000000000000'" \
    "404" \
    "Delete non-existent organization"

run_test "delete_invalid_id" \
    "curl -X DELETE '$BASE_URL/invalid-uuid'" \
    "422" \
    "Delete organization with invalid UUID"

# ============================================================================
# TEST SUITE SUMMARY
# ============================================================================

echo ""
echo "============================================================================"
echo "TEST SUITE COMPLETED"
echo "============================================================================"
echo "Total tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo "Success rate: $(( TESTS_PASSED * 100 / TESTS_RUN ))%"
echo "Completed at: $(date)"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}❌ $TESTS_FAILED TEST(S) FAILED${NC}"
    echo "Check the output above for details"
    exit 1
fi

# Cleanup
rm -rf "$TEMP_DIR"