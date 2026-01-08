#!/usr/bin/env bash
#
# Security Scanning Orchestration Script
# Runs comprehensive security scans including dependency audit, SAST, container scanning
# Includes failure thresholds and result aggregation

set -euo pipefail
IFS=$'\n\t'

# Script metadata
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
readonly SCAN_RESULTS_DIR="${PROJECT_ROOT}/security-scan-results"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
readonly SCAN_REPORT="${SCAN_RESULTS_DIR}/scan-report-${TIMESTAMP}.json"
readonly SCAN_SUMMARY="${SCAN_RESULTS_DIR}/scan-summary-${TIMESTAMP}.txt"

# Severity thresholds (exit with error if exceeded)
readonly MAX_CRITICAL=0
readonly MAX_HIGH=5
readonly MAX_MEDIUM=20

# Scan configuration
readonly ENABLE_DEPENDENCY_SCAN=true
readonly ENABLE_SAST_SCAN=true
readonly ENABLE_CONTAINER_SCAN=true
readonly ENABLE_SECRET_SCAN=true

# Tool versions
readonly SNYK_VERSION="latest"
readonly BANDIT_VERSION="latest"
readonly TRIVY_VERSION="latest"
readonly GITLEAKS_VERSION="latest"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

log_debug() {
    if [[ "${DEBUG:-0}" == "1" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
    fi
}

# Cleanup function
cleanup() {
    local exit_code=$?
    
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "Security scan failed with exit code ${exit_code}"
    fi
    
    exit "${exit_code}"
}

trap cleanup EXIT ERR INT TERM

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check for required tools
    if [[ "${ENABLE_DEPENDENCY_SCAN}" == "true" ]]; then
        if ! command -v snyk &>/dev/null; then
            missing_tools+=("snyk")
        fi
    fi
    
    if [[ "${ENABLE_SAST_SCAN}" == "true" ]]; then
        if ! command -v bandit &>/dev/null && [[ -d "${PROJECT_ROOT}/backend" ]]; then
            missing_tools+=("bandit")
        fi
        if ! command -v eslint &>/dev/null && [[ -d "${PROJECT_ROOT}/frontend" ]]; then
            missing_tools+=("eslint")
        fi
    fi
    
    if [[ "${ENABLE_CONTAINER_SCAN}" == "true" ]]; then
        if ! command -v trivy &>/dev/null; then
            missing_tools+=("trivy")
        fi
        if ! command -v docker &>/dev/null; then
            missing_tools+=("docker")
        fi
    fi
    
    if [[ "${ENABLE_SECRET_SCAN}" == "true" ]]; then
        if ! command -v gitleaks &>/dev/null; then
            missing_tools+=("gitleaks")
        fi
    fi
    
    # Check for jq (required for JSON processing)
    if ! command -v jq &>/dev/null; then
        missing_tools+=("jq")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Install missing tools:"
        for tool in "${missing_tools[@]}"; do
            case "${tool}" in
                snyk)
                    log_info "  npm install -g snyk"
                    ;;
                bandit)
                    log_info "  pip install bandit"
                    ;;
                eslint)
                    log_info "  npm install -g eslint"
                    ;;
                trivy)
                    log_info "  brew install aquasecurity/trivy/trivy (macOS)"
                    log_info "  or download from https://github.com/aquasecurity/trivy/releases"
                    ;;
                gitleaks)
                    log_info "  brew install gitleaks (macOS)"
                    log_info "  or download from https://github.com/gitleaks/gitleaks/releases"
                    ;;
                jq)
                    log_info "  brew install jq (macOS) or apt-get install jq (Ubuntu)"
                    ;;
            esac
        done
        return 1
    fi
    
    log_info "All prerequisites satisfied"
    return 0
}

# Initialize scan results directory
initialize_scan_directory() {
    log_info "Initializing scan results directory..."
    
    mkdir -p "${SCAN_RESULTS_DIR}"
    
    # Initialize scan report
    cat > "${SCAN_REPORT}" <<EOF
{
  "scan_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "project_root": "${PROJECT_ROOT}",
  "scans": {}
}
EOF
    
    log_info "Scan results will be saved to: ${SCAN_RESULTS_DIR}"
}

# Run dependency audit with Snyk
run_dependency_scan() {
    if [[ "${ENABLE_DEPENDENCY_SCAN}" != "true" ]]; then
        log_info "Dependency scan disabled, skipping..."
        return 0
    fi
    
    log_info "Running dependency audit with Snyk..."
    
    local backend_result=0
    local frontend_result=0
    local backend_json="${SCAN_RESULTS_DIR}/snyk-backend-${TIMESTAMP}.json"
    local frontend_json="${SCAN_RESULTS_DIR}/snyk-frontend-${TIMESTAMP}.json"
    
    # Scan backend dependencies
    if [[ -d "${PROJECT_ROOT}/backend" ]]; then
        log_info "Scanning backend dependencies..."
        cd "${PROJECT_ROOT}/backend"
        
        if snyk test --json --severity-threshold=low > "${backend_json}" 2>&1; then
            log_info "Backend dependency scan completed successfully"
        else
            backend_result=$?
            log_warn "Backend dependency scan found vulnerabilities (exit code: ${backend_result})"
        fi
    fi
    
    # Scan frontend dependencies
    if [[ -d "${PROJECT_ROOT}/frontend" ]]; then
        log_info "Scanning frontend dependencies..."
        cd "${PROJECT_ROOT}/frontend"
        
        if snyk test --json --severity-threshold=low > "${frontend_json}" 2>&1; then
            log_info "Frontend dependency scan completed successfully"
        else
            frontend_result=$?
            log_warn "Frontend dependency scan found vulnerabilities (exit code: ${frontend_result})"
        fi
    fi
    
    cd "${PROJECT_ROOT}"
    
    # Aggregate results
    local total_critical=0
    local total_high=0
    local total_medium=0
    local total_low=0
    
    if [[ -f "${backend_json}" ]]; then
        local backend_critical=$(jq -r '.vulnerabilities | map(select(.severity == "critical")) | length' "${backend_json}" 2>/dev/null || echo "0")
        local backend_high=$(jq -r '.vulnerabilities | map(select(.severity == "high")) | length' "${backend_json}" 2>/dev/null || echo "0")
        local backend_medium=$(jq -r '.vulnerabilities | map(select(.severity == "medium")) | length' "${backend_json}" 2>/dev/null || echo "0")
        local backend_low=$(jq -r '.vulnerabilities | map(select(.severity == "low")) | length' "${backend_json}" 2>/dev/null || echo "0")
        
        total_critical=$((total_critical + backend_critical))
        total_high=$((total_high + backend_high))
        total_medium=$((total_medium + backend_medium))
        total_low=$((total_low + backend_low))
    fi
    
    if [[ -f "${frontend_json}" ]]; then
        local frontend_critical=$(jq -r '.vulnerabilities | map(select(.severity == "critical")) | length' "${frontend_json}" 2>/dev/null || echo "0")
        local frontend_high=$(jq -r '.vulnerabilities | map(select(.severity == "high")) | length' "${frontend_json}" 2>/dev/null || echo "0")
        local frontend_medium=$(jq -r '.vulnerabilities | map(select(.severity == "medium")) | length' "${frontend_json}" 2>/dev/null || echo "0")
        local frontend_low=$(jq -r '.vulnerabilities | map(select(.severity == "low")) | length' "${frontend_json}" 2>/dev/null || echo "0")
        
        total_critical=$((total_critical + frontend_critical))
        total_high=$((total_high + frontend_high))
        total_medium=$((total_medium + frontend_medium))
        total_low=$((total_low + frontend_low))
    fi
    
    # Update scan report
    local temp_report=$(mktemp)
    jq --arg critical "${total_critical}" \
       --arg high "${total_high}" \
       --arg medium "${total_medium}" \
       --arg low "${total_low}" \
       '.scans.dependency_audit = {
         "tool": "snyk",
         "status": "completed",
         "vulnerabilities": {
           "critical": ($critical | tonumber),
           "high": ($high | tonumber),
           "medium": ($medium | tonumber),
           "low": ($low | tonumber)
         }
       }' "${SCAN_REPORT}" > "${temp_report}"
    mv "${temp_report}" "${SCAN_REPORT}"
    
    log_info "Dependency scan results: Critical=${total_critical}, High=${total_high}, Medium=${total_medium}, Low=${total_low}"
    
    return 0
}

# Run SAST with Bandit (Python) and ESLint (JavaScript/TypeScript)
run_sast_scan() {
    if [[ "${ENABLE_SAST_SCAN}" != "true" ]]; then
        log_info "SAST scan disabled, skipping..."
        return 0
    fi
    
    log_info "Running SAST scans..."
    
    local bandit_json="${SCAN_RESULTS_DIR}/bandit-${TIMESTAMP}.json"
    local eslint_json="${SCAN_RESULTS_DIR}/eslint-${TIMESTAMP}.json"
    
    local total_critical=0
    local total_high=0
    local total_medium=0
    local total_low=0
    
    # Run Bandit on Python code
    if [[ -d "${PROJECT_ROOT}/backend" ]] && command -v bandit &>/dev/null; then
        log_info "Running Bandit on Python code..."
        
        if bandit -r "${PROJECT_ROOT}/backend/src" -f json -o "${bandit_json}" 2>&1; then
            log_info "Bandit scan completed successfully"
        else
            log_warn "Bandit scan found issues"
        fi
        
        if [[ -f "${bandit_json}" ]]; then
            local bandit_high=$(jq -r '.results | map(select(.issue_severity == "HIGH")) | length' "${bandit_json}" 2>/dev/null || echo "0")
            local bandit_medium=$(jq -r '.results | map(select(.issue_severity == "MEDIUM")) | length' "${bandit_json}" 2>/dev/null || echo "0")
            local bandit_low=$(jq -r '.results | map(select(.issue_severity == "LOW")) | length' "${bandit_json}" 2>/dev/null || echo "0")
            
            total_high=$((total_high + bandit_high))
            total_medium=$((total_medium + bandit_medium))
            total_low=$((total_low + bandit_low))
        fi
    fi
    
    # Run ESLint on JavaScript/TypeScript code
    if [[ -d "${PROJECT_ROOT}/frontend" ]] && command -v eslint &>/dev/null; then
        log_info "Running ESLint on JavaScript/TypeScript code..."
        
        cd "${PROJECT_ROOT}/frontend"
        if npm run lint -- --format json --output-file "${eslint_json}" 2>&1; then
            log_info "ESLint scan completed successfully"
        else
            log_warn "ESLint scan found issues"
        fi
        cd "${PROJECT_ROOT}"
        
        if [[ -f "${eslint_json}" ]]; then
            local eslint_errors=$(jq -r '[.[].errorCount] | add // 0' "${eslint_json}" 2>/dev/null || echo "0")
            local eslint_warnings=$(jq -r '[.[].warningCount] | add // 0' "${eslint_json}" 2>/dev/null || echo "0")
            
            total_high=$((total_high + eslint_errors))
            total_medium=$((total_medium + eslint_warnings))
        fi
    fi
    
    # Update scan report
    local temp_report=$(mktemp)
    jq --arg critical "${total_critical}" \
       --arg high "${total_high}" \
       --arg medium "${total_medium}" \
       --arg low "${total_low}" \
       '.scans.sast = {
         "tools": ["bandit", "eslint"],
         "status": "completed",
         "issues": {
           "critical": ($critical | tonumber),
           "high": ($high | tonumber),
           "medium": ($medium | tonumber),
           "low": ($low | tonumber)
         }
       }' "${SCAN_REPORT}" > "${temp_report}"
    mv "${temp_report}" "${SCAN_REPORT}"
    
    log_info "SAST scan results: Critical=${total_critical}, High=${total_high}, Medium=${total_medium}, Low=${total_low}"
    
    return 0
}

# Run container scanning with Trivy
run_container_scan() {
    if [[ "${ENABLE_CONTAINER_SCAN}" != "true" ]]; then
        log_info "Container scan disabled, skipping..."
        return 0
    fi
    
    log_info "Running container security scans with Trivy..."
    
    local backend_image="autoselect-backend:latest"
    local frontend_image="autoselect-frontend:latest"
    local backend_json="${SCAN_RESULTS_DIR}/trivy-backend-${TIMESTAMP}.json"
    local frontend_json="${SCAN_RESULTS_DIR}/trivy-frontend-${TIMESTAMP}.json"
    
    local total_critical=0
    local total_high=0
    local total_medium=0
    local total_low=0
    
    # Scan backend container
    if docker image inspect "${backend_image}" &>/dev/null; then
        log_info "Scanning backend container image..."
        
        if trivy image --format json --output "${backend_json}" "${backend_image}" 2>&1; then
            log_info "Backend container scan completed"
        else
            log_warn "Backend container scan encountered issues"
        fi
        
        if [[ -f "${backend_json}" ]]; then
            local backend_critical=$(jq -r '[.Results[].Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "${backend_json}" 2>/dev/null || echo "0")
            local backend_high=$(jq -r '[.Results[].Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "${backend_json}" 2>/dev/null || echo "0")
            local backend_medium=$(jq -r '[.Results[].Vulnerabilities[]? | select(.Severity == "MEDIUM")] | length' "${backend_json}" 2>/dev/null || echo "0")
            local backend_low=$(jq -r '[.Results[].Vulnerabilities[]? | select(.Severity == "LOW")] | length' "${backend_json}" 2>/dev/null || echo "0")
            
            total_critical=$((total_critical + backend_critical))
            total_high=$((total_high + backend_high))
            total_medium=$((total_medium + backend_medium))
            total_low=$((total_low + backend_low))
        fi
    else
        log_warn "Backend container image not found: ${backend_image}"
    fi
    
    # Scan frontend container
    if docker image inspect "${frontend_image}" &>/dev/null; then
        log_info "Scanning frontend container image..."
        
        if trivy image --format json --output "${frontend_json}" "${frontend_image}" 2>&1; then
            log_info "Frontend container scan completed"
        else
            log_warn "Frontend container scan encountered issues"
        fi
        
        if [[ -f "${frontend_json}" ]]; then
            local frontend_critical=$(jq -r '[.Results[].Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "${frontend_json}" 2>/dev/null || echo "0")
            local frontend_high=$(jq -r '[.Results[].Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "${frontend_json}" 2>/dev/null || echo "0")
            local frontend_medium=$(jq -r '[.Results[].Vulnerabilities[]? | select(.Severity == "MEDIUM")] | length' "${frontend_json}" 2>/dev/null || echo "0")
            local frontend_low=$(jq -r '[.Results[].Vulnerabilities[]? | select(.Severity == "LOW")] | length' "${frontend_json}" 2>/dev/null || echo "0")
            
            total_critical=$((total_critical + frontend_critical))
            total_high=$((total_high + frontend_high))
            total_medium=$((total_medium + frontend_medium))
            total_low=$((total_low + frontend_low))
        fi
    else
        log_warn "Frontend container image not found: ${frontend_image}"
    fi
    
    # Update scan report
    local temp_report=$(mktemp)
    jq --arg critical "${total_critical}" \
       --arg high "${total_high}" \
       --arg medium "${total_medium}" \
       --arg low "${total_low}" \
       '.scans.container_scan = {
         "tool": "trivy",
         "status": "completed",
         "vulnerabilities": {
           "critical": ($critical | tonumber),
           "high": ($high | tonumber),
           "medium": ($medium | tonumber),
           "low": ($low | tonumber)
         }
       }' "${SCAN_REPORT}" > "${temp_report}"
    mv "${temp_report}" "${SCAN_REPORT}"
    
    log_info "Container scan results: Critical=${total_critical}, High=${total_high}, Medium=${total_medium}, Low=${total_low}"
    
    return 0
}

# Run secret scanning with Gitleaks
run_secret_scan() {
    if [[ "${ENABLE_SECRET_SCAN}" != "true" ]]; then
        log_info "Secret scan disabled, skipping..."
        return 0
    fi
    
    log_info "Running secret scanning with Gitleaks..."
    
    local gitleaks_json="${SCAN_RESULTS_DIR}/gitleaks-${TIMESTAMP}.json"
    
    cd "${PROJECT_ROOT}"
    
    if gitleaks detect --report-format json --report-path "${gitleaks_json}" --no-git 2>&1; then
        log_info "Secret scan completed - no secrets found"
    else
        log_warn "Secret scan found potential secrets"
    fi
    
    local total_secrets=0
    if [[ -f "${gitleaks_json}" ]]; then
        total_secrets=$(jq -r 'length' "${gitleaks_json}" 2>/dev/null || echo "0")
    fi
    
    # Update scan report
    local temp_report=$(mktemp)
    jq --arg count "${total_secrets}" \
       '.scans.secret_scan = {
         "tool": "gitleaks",
         "status": "completed",
         "secrets_found": ($count | tonumber)
       }' "${SCAN_REPORT}" > "${temp_report}"
    mv "${temp_report}" "${SCAN_REPORT}"
    
    log_info "Secret scan results: Secrets found=${total_secrets}"
    
    return 0
}

# Generate scan summary
generate_summary() {
    log_info "Generating scan summary..."
    
    local total_critical=$(jq -r '[.scans[].vulnerabilities.critical // 0, .scans[].issues.critical // 0] | add' "${SCAN_REPORT}")
    local total_high=$(jq -r '[.scans[].vulnerabilities.high // 0, .scans[].issues.high // 0] | add' "${SCAN_REPORT}")
    local total_medium=$(jq -r '[.scans[].vulnerabilities.medium // 0, .scans[].issues.medium // 0] | add' "${SCAN_REPORT}")
    local total_low=$(jq -r '[.scans[].vulnerabilities.low // 0, .scans[].issues.low // 0] | add' "${SCAN_REPORT}")
    local total_secrets=$(jq -r '.scans.secret_scan.secrets_found // 0' "${SCAN_REPORT}")
    
    cat > "${SCAN_SUMMARY}" <<EOF
================================================================================
Security Scan Summary
================================================================================
Scan Date: $(date '+%Y-%m-%d %H:%M:%S')
Project: AutoSelect - Car Ordering Platform

Overall Results:
  Critical: ${total_critical}
  High:     ${total_high}
  Medium:   ${total_medium}
  Low:      ${total_low}
  Secrets:  ${total_secrets}

Thresholds:
  Max Critical: ${MAX_CRITICAL}
  Max High:     ${MAX_HIGH}
  Max Medium:   ${MAX_MEDIUM}

Scan Status:
EOF
    
    # Add individual scan statuses
    if [[ "${ENABLE_DEPENDENCY_SCAN}" == "true" ]]; then
        local dep_critical=$(jq -r '.scans.dependency_audit.vulnerabilities.critical // 0' "${SCAN_REPORT}")
        local dep_high=$(jq -r '.scans.dependency_audit.vulnerabilities.high // 0' "${SCAN_REPORT}")
        local dep_medium=$(jq -r '.scans.dependency_audit.vulnerabilities.medium // 0' "${SCAN_REPORT}")
        echo "  Dependency Audit (Snyk): Critical=${dep_critical}, High=${dep_high}, Medium=${dep_medium}" >> "${SCAN_SUMMARY}"
    fi
    
    if [[ "${ENABLE_SAST_SCAN}" == "true" ]]; then
        local sast_critical=$(jq -r '.scans.sast.issues.critical // 0' "${SCAN_REPORT}")
        local sast_high=$(jq -r '.scans.sast.issues.high // 0' "${SCAN_REPORT}")
        local sast_medium=$(jq -r '.scans.sast.issues.medium // 0' "${SCAN_REPORT}")
        echo "  SAST (Bandit/ESLint): Critical=${sast_critical}, High=${sast_high}, Medium=${sast_medium}" >> "${SCAN_SUMMARY}"
    fi
    
    if [[ "${ENABLE_CONTAINER_SCAN}" == "true" ]]; then
        local container_critical=$(jq -r '.scans.container_scan.vulnerabilities.critical // 0' "${SCAN_REPORT}")
        local container_high=$(jq -r '.scans.container_scan.vulnerabilities.high // 0' "${SCAN_REPORT}")
        local container_medium=$(jq -r '.scans.container_scan.vulnerabilities.medium // 0' "${SCAN_REPORT}")
        echo "  Container Scan (Trivy): Critical=${container_critical}, High=${container_high}, Medium=${container_medium}" >> "${SCAN_SUMMARY}"
    fi
    
    if [[ "${ENABLE_SECRET_SCAN}" == "true" ]]; then
        echo "  Secret Scan (Gitleaks): Secrets=${total_secrets}" >> "${SCAN_SUMMARY}"
    fi
    
    echo "" >> "${SCAN_SUMMARY}"
    echo "Detailed Results: ${SCAN_REPORT}" >> "${SCAN_SUMMARY}"
    echo "================================================================================" >> "${SCAN_SUMMARY}"
    
    cat "${SCAN_SUMMARY}"
    
    log_info "Summary saved to: ${SCAN_SUMMARY}"
}

# Check thresholds and determine exit code
check_thresholds() {
    log_info "Checking security thresholds..."
    
    local total_critical=$(jq -r '[.scans[].vulnerabilities.critical // 0, .scans[].issues.critical // 0] | add' "${SCAN_REPORT}")
    local total_high=$(jq -r '[.scans[].vulnerabilities.high // 0, .scans[].issues.high // 0] | add' "${SCAN_REPORT}")
    local total_medium=$(jq -r '[.scans[].vulnerabilities.medium // 0, .scans[].issues.medium // 0] | add' "${SCAN_REPORT}")
    
    local threshold_exceeded=false
    
    if [[ ${total_critical} -gt ${MAX_CRITICAL} ]]; then
        log_error "Critical vulnerabilities (${total_critical}) exceed threshold (${MAX_CRITICAL})"
        threshold_exceeded=true
    fi
    
    if [[ ${total_high} -gt ${MAX_HIGH} ]]; then
        log_error "High vulnerabilities (${total_high}) exceed threshold (${MAX_HIGH})"
        threshold_exceeded=true
    fi
    
    if [[ ${total_medium} -gt ${MAX_MEDIUM} ]]; then
        log_error "Medium vulnerabilities (${total_medium}) exceed threshold (${MAX_MEDIUM})"
        threshold_exceeded=true
    fi
    
    if [[ "${threshold_exceeded}" == "true" ]]; then
        log_error "Security scan failed - thresholds exceeded"
        return 1
    fi
    
    log_info "All security thresholds passed"
    return 0
}

# Main execution
main() {
    log_info "Starting comprehensive security scan..."
    log_info "Project root: ${PROJECT_ROOT}"
    
    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    
    # Initialize scan directory
    initialize_scan_directory
    
    # Run scans
    run_dependency_scan
    run_sast_scan
    run_container_scan
    run_secret_scan
    
    # Generate summary
    generate_summary
    
    # Check thresholds
    if ! check_thresholds; then
        exit 1
    fi
    
    log_info "Security scan completed successfully"
    log_info "Results available at: ${SCAN_RESULTS_DIR}"
}

main "$@"