#!/bin/bash

# ============================================================================
# Organization Admin API Comprehensive Test Suite  
# ============================================================================
# Tests all admin organization endpoints using curl commands
# Base URL: http://localhost:8001/api/v1/admin/organizations
#
# Usage: ./test_admin_api.sh
# ============================================================================

set -e

# Configuration
BASE_URL="http://localhost:8001/api/v1/admin/organizations"
TEMP_DIR="/tmp/org_admin_tests"
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
echo "ORGANIZATION ADMIN API COMPREHENSIVE TEST SUITE"
echo "============================================================================"
echo "Testing against: $BASE_URL"
echo "Started at: $(date)"
echo ""

# Known organization ID for testing
KNOWN_ORG_ID="0198be94-d49a-70d2-8660-3f7e8de47e25"

# ============================================================================
# 1. STATISTICS & REPORTING
# ============================================================================

log_info "=== STATISTICS TESTS ==="

run_test "get_stats_default" \
    "curl '$BASE_URL/stats'" \
    "200" \
    "Get organization statistics with default parameters"

run_test "get_stats_with_trends" \
    "curl '$BASE_URL/stats?include_trends=true&days_back=30'" \
    "200" \
    "Get organization statistics with trends over 30 days"

run_test "get_stats_no_trends" \
    "curl '$BASE_URL/stats?include_trends=false'" \
    "200" \
    "Get organization statistics without trends"

run_test "get_stats_custom_period" \
    "curl '$BASE_URL/stats?include_trends=true&days_back=7'" \
    "200" \
    "Get organization statistics with trends over 7 days"

run_test "get_stats_max_period" \
    "curl '$BASE_URL/stats?days_back=365'" \
    "200" \
    "Get organization statistics with maximum time period"

run_test "get_stats_invalid_period" \
    "curl '$BASE_URL/stats?days_back=500'" \
    "422" \
    "Get statistics with invalid time period (should fail validation)"

# ============================================================================
# 2. HEALTH MONITORING
# ============================================================================

log_info "=== HEALTH MONITORING TESTS ==="

run_test "system_health_check" \
    "curl '$BASE_URL/health'" \
    "200" \
    "Perform organization system health check"

run_test "org_health_score" \
    "curl '$BASE_URL/$KNOWN_ORG_ID/health'" \
    "200" \
    "Get health score for specific organization"

run_test "health_score_not_found" \
    "curl '$BASE_URL/0198be94-d49a-70d2-8660-000000000000/health'" \
    "404" \
    "Get health score for non-existent organization"

run_test "health_score_invalid_id" \
    "curl '$BASE_URL/invalid-uuid/health'" \
    "422" \
    "Get health score with invalid UUID"

# ============================================================================
# 3. DATA INTEGRITY & VALIDATION
# ============================================================================

log_info "=== DATA INTEGRITY TESTS ==="

run_test "validate_integrity_dry_run" \
    "curl -X POST '$BASE_URL/integrity/validate'" \
    "200" \
    "Validate organization data integrity (dry run)"

run_test "validate_integrity_with_fix" \
    "curl -X POST '$BASE_URL/integrity/validate?fix_issues=true'" \
    "200" \
    "Validate organization data integrity with auto-fix enabled"

run_test "validate_integrity_no_fix" \
    "curl -X POST '$BASE_URL/integrity/validate?fix_issues=false'" \
    "200" \
    "Validate organization data integrity without auto-fix"

# ============================================================================
# 4. CLEANUP OPERATIONS
# ============================================================================

log_info "=== CLEANUP TESTS ==="

run_test "cleanup_dry_run_default" \
    "curl -X POST '$BASE_URL/cleanup'" \
    "200" \
    "Cleanup inactive organizations (dry run with default retention)"

run_test "cleanup_dry_run_custom" \
    "curl -X POST '$BASE_URL/cleanup?retention_days=30&dry_run=true'" \
    "200" \
    "Cleanup inactive organizations (dry run with custom retention)"

run_test "cleanup_min_retention" \
    "curl -X POST '$BASE_URL/cleanup?retention_days=30&dry_run=true'" \
    "200" \
    "Cleanup with minimum retention period (30 days)"

run_test "cleanup_max_retention" \
    "curl -X POST '$BASE_URL/cleanup?retention_days=3650&dry_run=true'" \
    "200" \
    "Cleanup with maximum retention period (10 years)"

run_test "cleanup_invalid_retention" \
    "curl -X POST '$BASE_URL/cleanup?retention_days=10&dry_run=true'" \
    "422" \
    "Cleanup with invalid retention period (should fail validation)"

# NOTE: Not testing actual cleanup (dry_run=false) to avoid data loss

# ============================================================================
# 5. DATA EXPORT
# ============================================================================

log_info "=== EXPORT TESTS ==="

run_test "export_default" \
    "curl '$BASE_URL/export'" \
    "200" \
    "Export organization data with default settings"

run_test "export_dict_format" \
    "curl '$BASE_URL/export?format=dict&include_metadata=true&active_only=true'" \
    "200" \
    "Export organizations in dict format with metadata"

run_test "export_minimal_format" \
    "curl '$BASE_URL/export?format=minimal&include_metadata=false'" \
    "200" \
    "Export organizations in minimal format without metadata"

run_test "export_admin_format" \
    "curl '$BASE_URL/export?format=admin&include_metadata=true'" \
    "200" \
    "Export organizations in admin format with metadata"

run_test "export_all_orgs" \
    "curl '$BASE_URL/export?active_only=false'" \
    "200" \
    "Export all organizations (active and inactive)"

run_test "export_invalid_format" \
    "curl '$BASE_URL/export?format=invalid'" \
    "422" \
    "Export with invalid format (should fail validation)"

# ============================================================================
# 6. ADVANCED SEARCH
# ============================================================================

log_info "=== ADVANCED SEARCH TESTS ==="

run_test "admin_search_basic" \
    "curl '$BASE_URL/search/advanced'" \
    "200" \
    "Advanced search with default parameters"

run_test "admin_search_with_query" \
    "curl '$BASE_URL/search/advanced?query=Test'" \
    "200" \
    "Advanced search with query parameter"

run_test "admin_search_include_inactive" \
    "curl '$BASE_URL/search/advanced?include_inactive=true'" \
    "200" \
    "Advanced search including inactive organizations"

run_test "admin_search_exclude_unverified" \
    "curl '$BASE_URL/search/advanced?include_unverified=false'" \
    "200" \
    "Advanced search excluding unverified organizations"

run_test "admin_search_by_industry" \
    "curl '$BASE_URL/search/advanced?industry=Technology'" \
    "200" \
    "Advanced search filtered by industry"

run_test "admin_search_by_country" \
    "curl '$BASE_URL/search/advanced?country_code=US'" \
    "200" \
    "Advanced search filtered by country"

run_test "admin_search_created_after" \
    "curl '$BASE_URL/search/advanced?created_after=2024-01-01T00:00:00Z'" \
    "200" \
    "Advanced search with creation date filter"

run_test "admin_search_min_health_score" \
    "curl '$BASE_URL/search/advanced?min_health_score=80'" \
    "200" \
    "Advanced search with minimum health score filter"

run_test "admin_search_combined_filters" \
    "curl '$BASE_URL/search/advanced?query=Corp&industry=Technology&country_code=US&include_inactive=false&limit=10'" \
    "200" \
    "Advanced search with multiple combined filters"

run_test "admin_search_custom_limit" \
    "curl '$BASE_URL/search/advanced?limit=5'" \
    "200" \
    "Advanced search with custom result limit"

run_test "admin_search_max_limit" \
    "curl '$BASE_URL/search/advanced?limit=1000'" \
    "200" \
    "Advanced search with maximum result limit"

run_test "admin_search_invalid_limit" \
    "curl '$BASE_URL/search/advanced?limit=2000'" \
    "422" \
    "Advanced search with invalid limit (should fail validation)"

# ============================================================================
# 7. FORCE VERIFICATION (Admin Override)
# ============================================================================

log_info "=== FORCE VERIFICATION TESTS ==="

run_test "force_verify_valid" \
    "curl -X POST '$BASE_URL/$KNOWN_ORG_ID/force-verify?reason=admin-testing'" \
    "200" \
    "Force verify organization with admin override"

run_test "force_verify_detailed_reason" \
    "curl -X POST '$BASE_URL/$KNOWN_ORG_ID/force-verify?reason=Admin%20approved%20after%20manual%20review'" \
    "200" \
    "Force verify organization with detailed reason"

run_test "force_verify_not_found" \
    "curl -X POST '$BASE_URL/0198be94-d49a-70d2-8660-000000000000/force-verify?reason=testing'" \
    "404" \
    "Force verify non-existent organization"

run_test "force_verify_invalid_id" \
    "curl -X POST '$BASE_URL/invalid-uuid/force-verify?reason=testing'" \
    "422" \
    "Force verify with invalid UUID"

run_test "force_verify_missing_reason" \
    "curl -X POST '$BASE_URL/$KNOWN_ORG_ID/force-verify'" \
    "422" \
    "Force verify without required reason parameter"

# ============================================================================
# 8. DASHBOARD DATA
# ============================================================================

log_info "=== DASHBOARD DATA TESTS ==="

run_test "admin_dashboard_data" \
    "curl '$BASE_URL/reports/dashboard'" \
    "200" \
    "Get comprehensive admin dashboard data"

# ============================================================================
# 9. ERROR HANDLING TESTS
# ============================================================================

log_info "=== ERROR HANDLING TESTS ==="

run_test "invalid_endpoint" \
    "curl '$BASE_URL/invalid-endpoint'" \
    "404" \
    "Access non-existent admin endpoint"

run_test "malformed_request" \
    "curl -X POST '$BASE_URL/stats' -H 'Content-Type: application/json' -d 'invalid-json'" \
    "400" \
    "Send malformed request body"

# ============================================================================
# 10. PERFORMANCE TESTS (Basic)
# ============================================================================

log_info "=== PERFORMANCE TESTS ==="

log_info "Testing response times for key endpoints..."

# Test response time for statistics endpoint
start_time=$(date +%s.%3N)
curl -s "$BASE_URL/stats" > /dev/null
end_time=$(date +%s.%3N)
stats_time=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "N/A")
log_info "Statistics endpoint response time: ${stats_time}s"

# Test response time for health check
start_time=$(date +%s.%3N)
curl -s "$BASE_URL/health" > /dev/null
end_time=$(date +%s.%3N)
health_time=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "N/A")
log_info "Health check response time: ${health_time}s"

# Test response time for advanced search
start_time=$(date +%s.%3N)
curl -s "$BASE_URL/search/advanced?limit=10" > /dev/null
end_time=$(date +%s.%3N)
search_time=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "N/A")
log_info "Advanced search response time: ${search_time}s"

# ============================================================================
# TEST SUITE SUMMARY
# ============================================================================

echo ""
echo "============================================================================"
echo "ADMIN TEST SUITE COMPLETED"
echo "============================================================================"
echo "Total tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo "Success rate: $(( TESTS_PASSED * 100 / TESTS_RUN ))%"
echo ""
echo "Performance Summary:"
echo "  - Statistics endpoint: ${stats_time}s"
echo "  - Health check: ${health_time}s"  
echo "  - Advanced search: ${search_time}s"
echo ""
echo "Completed at: $(date)"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}🎉 ALL ADMIN TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}❌ $TESTS_FAILED ADMIN TEST(S) FAILED${NC}"
    echo "Check the output above for details"
    exit 1
fi

# Cleanup
rm -rf "$TEMP_DIR"