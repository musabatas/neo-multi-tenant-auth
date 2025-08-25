#!/bin/bash

# ============================================================================
# Organization API Master Test Runner
# ============================================================================
# Runs all organization API tests (basic + admin) in sequence
#
# Usage: ./run_all_tests.sh [options]
# Options:
#   --basic-only    Run only basic organization tests
#   --admin-only    Run only admin organization tests
#   --parallel      Run both test suites in parallel
#   --help          Show this help message
# ============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASIC_TEST="$SCRIPT_DIR/test_organizations_api.sh"
ADMIN_TEST="$SCRIPT_DIR/test_admin_api.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Parse command line arguments
BASIC_ONLY=false
ADMIN_ONLY=false
PARALLEL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --basic-only)
            BASIC_ONLY=true
            shift
            ;;
        --admin-only)
            ADMIN_ONLY=true
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --help|-h)
            echo "Organization API Master Test Runner"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --basic-only    Run only basic organization tests"
            echo "  --admin-only    Run only admin organization tests"  
            echo "  --parallel      Run both test suites in parallel"
            echo "  --help          Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Make scripts executable
chmod +x "$BASIC_TEST" "$ADMIN_TEST"

# Helper functions
log_header() {
    echo -e "${BOLD}${BLUE}================================================================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}================================================================================${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Test runner functions
run_basic_tests() {
    log_header "RUNNING BASIC ORGANIZATION API TESTS"
    echo "Script: $BASIC_TEST"
    echo "Started: $(date)"
    echo ""
    
    if bash "$BASIC_TEST"; then
        log_success "Basic organization tests completed successfully"
        return 0
    else
        log_error "Basic organization tests failed"
        return 1
    fi
}

run_admin_tests() {
    log_header "RUNNING ADMIN ORGANIZATION API TESTS"
    echo "Script: $ADMIN_TEST"
    echo "Started: $(date)"
    echo ""
    
    if bash "$ADMIN_TEST"; then
        log_success "Admin organization tests completed successfully"
        return 0
    else
        log_error "Admin organization tests failed"
        return 1
    fi
}

# Main execution logic
main() {
    local start_time=$(date +%s)
    local basic_result=0
    local admin_result=0
    local overall_result=0
    
    log_header "ORGANIZATION API COMPREHENSIVE TEST SUITE"
    echo "Test suite location: $SCRIPT_DIR"
    echo "Started at: $(date)"
    echo ""
    
    # Pre-flight checks
    log_info "Performing pre-flight checks..."
    
    # Check if API is running
    if curl -s "http://localhost:8001/health" > /dev/null 2>&1; then
        log_success "✓ NeoAdminApi is running (port 8001)"
    else
        log_error "✗ NeoAdminApi is not accessible at http://localhost:8001"
        log_error "Please start the API server before running tests"
        exit 1
    fi
    
    # Check if test scripts exist
    if [[ ! -f "$BASIC_TEST" ]]; then
        log_error "✗ Basic test script not found: $BASIC_TEST"
        exit 1
    fi
    
    if [[ ! -f "$ADMIN_TEST" ]]; then
        log_error "✗ Admin test script not found: $ADMIN_TEST"
        exit 1
    fi
    
    log_success "✓ All pre-flight checks passed"
    echo ""
    
    # Run tests based on options
    if [[ "$BASIC_ONLY" == true ]]; then
        log_info "Running basic tests only..."
        run_basic_tests
        basic_result=$?
        overall_result=$basic_result
        
    elif [[ "$ADMIN_ONLY" == true ]]; then
        log_info "Running admin tests only..."
        run_admin_tests
        admin_result=$?
        overall_result=$admin_result
        
    elif [[ "$PARALLEL" == true ]]; then
        log_info "Running both test suites in parallel..."
        
        # Run tests in parallel and capture results
        run_basic_tests &
        local basic_pid=$!
        
        run_admin_tests &
        local admin_pid=$!
        
        # Wait for both to complete and get exit codes
        wait $basic_pid
        basic_result=$?
        
        wait $admin_pid
        admin_result=$?
        
        # Overall result is 0 only if both passed
        if [[ $basic_result -eq 0 && $admin_result -eq 0 ]]; then
            overall_result=0
        else
            overall_result=1
        fi
        
    else
        log_info "Running both test suites sequentially..."
        
        # Run basic tests first
        run_basic_tests
        basic_result=$?
        
        echo ""
        
        # Run admin tests second
        run_admin_tests  
        admin_result=$?
        
        # Overall result is 0 only if both passed
        if [[ $basic_result -eq 0 && $admin_result -eq 0 ]]; then
            overall_result=0
        else
            overall_result=1
        fi
    fi
    
    # Calculate execution time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    # Final summary
    log_header "TEST SUITE SUMMARY"
    
    if [[ "$BASIC_ONLY" != true ]]; then
        if [[ $basic_result -eq 0 ]]; then
            log_success "✓ Basic organization tests: PASSED"
        else
            log_error "✗ Basic organization tests: FAILED"
        fi
    fi
    
    if [[ "$ADMIN_ONLY" != true ]]; then
        if [[ $admin_result -eq 0 ]]; then
            log_success "✓ Admin organization tests: PASSED"
        else
            log_error "✗ Admin organization tests: FAILED"
        fi
    fi
    
    echo ""
    echo "Total execution time: ${minutes}m ${seconds}s"
    echo "Completed at: $(date)"
    echo ""
    
    if [[ $overall_result -eq 0 ]]; then
        log_success "🎉 ALL TEST SUITES PASSED!"
        echo -e "${GREEN}The organization API is working correctly.${NC}"
    else
        log_error "❌ ONE OR MORE TEST SUITES FAILED"
        echo -e "${RED}Please check the output above for details.${NC}"
    fi
    
    exit $overall_result
}

# Trap to ensure cleanup on exit
trap 'echo ""; log_info "Test execution interrupted"' INT TERM

# Run main function
main "$@"