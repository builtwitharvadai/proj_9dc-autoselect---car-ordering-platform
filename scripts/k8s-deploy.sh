#!/usr/bin/env bash
#
# AutoSelect - Car Ordering Platform Deployment Script
# Environment: dev
# Stage: mature
#
# Usage: ./deploy.sh [OPTIONS]
#
# Options:
#   -h, --help          Show this help message
#   -v, --verbose       Enable verbose output
#   -d, --dry-run       Run without making changes
#   --skip-tests        Skip test execution
#   --skip-build        Skip build step
#   --rollback          Rollback to previous version

set -euo pipefail
IFS=$'\n\t'

# Script metadata
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# Environment configuration
readonly ENVIRONMENT="dev"
readonly APP_NAME="autoselect"
readonly FRONTEND_DIR="${PROJECT_ROOT}/frontend"
readonly BACKEND_DIR="${PROJECT_ROOT}/backend"
readonly BUILD_DIR="${PROJECT_ROOT}/build"
readonly LOG_DIR="${PROJECT_ROOT}/logs"
readonly LOG_FILE="${LOG_DIR}/deploy_${TIMESTAMP}.log"

# Deployment configuration
readonly FRONTEND_PORT="${FRONTEND_PORT:-3000}"
readonly BACKEND_PORT="${BACKEND_PORT:-8000}"
readonly NODE_VERSION="20"
readonly PYTHON_VERSION="3.11"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Flags
VERBOSE=0
DRY_RUN=0
SKIP_TESTS=0
SKIP_BUILD=0
ROLLBACK=0

# Logging functions
log_info() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*"
    echo -e "${GREEN}${message}${NC}" | tee -a "${LOG_FILE}"
}

log_warn() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*"
    echo -e "${YELLOW}${message}${NC}" | tee -a "${LOG_FILE}"
}

log_error() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*"
    echo -e "${RED}${message}${NC}" | tee -a "${LOG_FILE}"
}

log_debug() {
    if [[ ${VERBOSE} -eq 1 ]]; then
        local message="[$(date '+%Y-%m-%d %H:%M:%S')] [DEBUG] $*"
        echo -e "${BLUE}${message}${NC}" | tee -a "${LOG_FILE}"
    fi
}

# Error handler
error_handler() {
    local line_number=$1
    log_error "Deployment failed at line ${line_number}"
    log_error "Check log file: ${LOG_FILE}"
    cleanup_on_error
    exit 1
}

trap 'error_handler ${LINENO}' ERR

# Cleanup function
cleanup_on_error() {
    log_warn "Performing cleanup..."
    
    if [[ -d "${BUILD_DIR}" ]]; then
        log_debug "Removing build directory"
        rm -rf "${BUILD_DIR}" 2>/dev/null || true
    fi
    
    log_warn "Cleanup completed"
}

cleanup_on_exit() {
    local exit_code=$?
    
    if [[ ${exit_code} -eq 0 ]]; then
        log_info "Deployment completed successfully"
    else
        log_error "Deployment failed with exit code ${exit_code}"
    fi
    
    exit "${exit_code}"
}

trap cleanup_on_exit EXIT

# Help message
show_help() {
    cat << EOF
AutoSelect Deployment Script

Usage: ${SCRIPT_NAME} [OPTIONS]

Options:
    -h, --help          Show this help message
    -v, --verbose       Enable verbose output
    -d, --dry-run       Run without making changes
    --skip-tests        Skip test execution
    --skip-build        Skip build step
    --rollback          Rollback to previous version

Environment: ${ENVIRONMENT}
Frontend Port: ${FRONTEND_PORT}
Backend Port: ${BACKEND_PORT}

Examples:
    ${SCRIPT_NAME}                    # Normal deployment
    ${SCRIPT_NAME} -v                 # Verbose deployment
    ${SCRIPT_NAME} --dry-run          # Test deployment without changes
    ${SCRIPT_NAME} --skip-tests       # Deploy without running tests
    ${SCRIPT_NAME} --rollback         # Rollback to previous version

EOF
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=1
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=1
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=1
                shift
                ;;
            --skip-build)
                SKIP_BUILD=1
                shift
                ;;
            --rollback)
                ROLLBACK=1
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local required_commands=("node" "npm" "python3" "pip3" "docker" "git")
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "${cmd}" &>/dev/null; then
            log_error "Required command not found: ${cmd}"
            return 1
        fi
        log_debug "Found: ${cmd}"
    done
    
    # Check Node.js version
    local node_version
    node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ ${node_version} -lt ${NODE_VERSION} ]]; then
        log_error "Node.js version ${NODE_VERSION} or higher required (found: ${node_version})"
        return 1
    fi
    log_debug "Node.js version: ${node_version}"
    
    # Check Python version
    local python_version
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ "${python_version}" != "${PYTHON_VERSION}" ]]; then
        log_warn "Python version ${PYTHON_VERSION} recommended (found: ${python_version})"
    fi
    log_debug "Python version: ${python_version}"
    
    # Check directories
    if [[ ! -d "${FRONTEND_DIR}" ]]; then
        log_error "Frontend directory not found: ${FRONTEND_DIR}"
        return 1
    fi
    
    if [[ ! -d "${BACKEND_DIR}" ]]; then
        log_error "Backend directory not found: ${BACKEND_DIR}"
        return 1
    fi
    
    log_info "Prerequisites check passed"
    return 0
}

# Initialize environment
initialize_environment() {
    log_info "Initializing deployment environment..."
    
    # Create necessary directories
    mkdir -p "${BUILD_DIR}" "${LOG_DIR}"
    
    # Set environment variables
    export NODE_ENV="${ENVIRONMENT}"
    export PYTHONUNBUFFERED=1
    export PYTHONDONTWRITEBYTECODE=1
    
    log_debug "Build directory: ${BUILD_DIR}"
    log_debug "Log directory: ${LOG_DIR}"
    log_debug "NODE_ENV: ${NODE_ENV}"
    
    log_info "Environment initialized"
}

# Install frontend dependencies
install_frontend_dependencies() {
    log_info "Installing frontend dependencies..."
    
    cd "${FRONTEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "[DRY RUN] Would install frontend dependencies"
        return 0
    fi
    
    if [[ ! -f "package.json" ]]; then
        log_error "package.json not found in ${FRONTEND_DIR}"
        return 1
    fi
    
    log_debug "Running npm install..."
    npm install --loglevel=error
    
    log_info "Frontend dependencies installed"
}

# Install backend dependencies
install_backend_dependencies() {
    log_info "Installing backend dependencies..."
    
    cd "${BACKEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "[DRY RUN] Would install backend dependencies"
        return 0
    fi
    
    if [[ ! -f "requirements.txt" ]]; then
        log_error "requirements.txt not found in ${BACKEND_DIR}"
        return 1
    fi
    
    log_debug "Creating virtual environment..."
    python3 -m venv venv
    
    log_debug "Activating virtual environment..."
    source venv/bin/activate
    
    log_debug "Installing dependencies..."
    pip3 install --quiet --upgrade pip
    pip3 install --quiet -r requirements.txt
    
    log_info "Backend dependencies installed"
}

# Run frontend tests
run_frontend_tests() {
    if [[ ${SKIP_TESTS} -eq 1 ]]; then
        log_warn "Skipping frontend tests"
        return 0
    fi
    
    log_info "Running frontend tests..."
    
    cd "${FRONTEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "[DRY RUN] Would run frontend tests"
        return 0
    fi
    
    log_debug "Running type check..."
    npm run type-check
    
    log_debug "Running linter..."
    npm run lint
    
    log_debug "Running unit tests..."
    npm run test -- --run
    
    log_info "Frontend tests passed"
}

# Run backend tests
run_backend_tests() {
    if [[ ${SKIP_TESTS} -eq 1 ]]; then
        log_warn "Skipping backend tests"
        return 0
    fi
    
    log_info "Running backend tests..."
    
    cd "${BACKEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "[DRY RUN] Would run backend tests"
        return 0
    fi
    
    source venv/bin/activate
    
    log_debug "Running pytest..."
    pytest --quiet --tb=short
    
    log_info "Backend tests passed"
}

# Build frontend
build_frontend() {
    if [[ ${SKIP_BUILD} -eq 1 ]]; then
        log_warn "Skipping frontend build"
        return 0
    fi
    
    log_info "Building frontend..."
    
    cd "${FRONTEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "[DRY RUN] Would build frontend"
        return 0
    fi
    
    log_debug "Running build..."
    npm run build
    
    if [[ ! -d "dist" ]]; then
        log_error "Frontend build failed - dist directory not created"
        return 1
    fi
    
    log_debug "Copying build artifacts..."
    cp -r dist "${BUILD_DIR}/frontend"
    
    log_info "Frontend build completed"
}

# Build backend
build_backend() {
    if [[ ${SKIP_BUILD} -eq 1 ]]; then
        log_warn "Skipping backend build"
        return 0
    fi
    
    log_info "Building backend..."
    
    cd "${BACKEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "[DRY RUN] Would build backend"
        return 0
    fi
    
    log_debug "Copying backend files..."
    mkdir -p "${BUILD_DIR}/backend"
    cp -r src "${BUILD_DIR}/backend/"
    cp requirements.txt "${BUILD_DIR}/backend/"
    
    log_info "Backend build completed"
}

# Build Docker images
build_docker_images() {
    log_info "Building Docker images..."
    
    cd "${PROJECT_ROOT}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "[DRY RUN] Would build Docker images"
        return 0
    fi
    
    log_debug "Building backend image..."
    docker build -t "${APP_NAME}-backend:${ENVIRONMENT}" -f backend/Dockerfile .
    
    log_debug "Building frontend image..."
    docker build -t "${APP_NAME}-frontend:${ENVIRONMENT}" -f frontend/Dockerfile .
    
    log_info "Docker images built successfully"
}

# Deploy application
deploy_application() {
    log_info "Deploying application..."
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "[DRY RUN] Would deploy application"
        return 0
    fi
    
    log_debug "Stopping existing containers..."
    docker-compose -f docker-compose.${ENVIRONMENT}.yml down 2>/dev/null || true
    
    log_debug "Starting containers..."
    docker-compose -f docker-compose.${ENVIRONMENT}.yml up -d
    
    log_info "Application deployed"
}

# Health check
health_check() {
    log_info "Performing health checks..."
    
    local max_retries=30
    local retry_count=0
    
    # Check backend health
    log_debug "Checking backend health..."
    while [[ ${retry_count} -lt ${max_retries} ]]; do
        if curl -sf "http://localhost:${BACKEND_PORT}/health" &>/dev/null; then
            log_info "Backend health check passed"
            break
        fi
        
        retry_count=$((retry_count + 1))
        log_debug "Backend not ready, retrying (${retry_count}/${max_retries})..."
        sleep 2
    done
    
    if [[ ${retry_count} -eq ${max_retries} ]]; then
        log_error "Backend health check failed after ${max_retries} attempts"
        return 1
    fi
    
    # Check frontend health
    log_debug "Checking frontend health..."
    retry_count=0
    while [[ ${retry_count} -lt ${max_retries} ]]; do
        if curl -sf "http://localhost:${FRONTEND_PORT}" &>/dev/null; then
            log_info "Frontend health check passed"
            break
        fi
        
        retry_count=$((retry_count + 1))
        log_debug "Frontend not ready, retrying (${retry_count}/${max_retries})..."
        sleep 2
    done
    
    if [[ ${retry_count} -eq ${max_retries} ]]; then
        log_error "Frontend health check failed after ${max_retries} attempts"
        return 1
    fi
    
    log_info "All health checks passed"
    return 0
}

# Rollback deployment
rollback_deployment() {
    log_warn "Rolling back deployment..."
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "[DRY RUN] Would rollback deployment"
        return 0
    fi
    
    log_debug "Stopping current containers..."
    docker-compose -f docker-compose.${ENVIRONMENT}.yml down
    
    log_debug "Starting previous version..."
    docker-compose -f docker-compose.${ENVIRONMENT}.yml up -d --force-recreate
    
    log_warn "Rollback completed"
}

# Main deployment function
main() {
    log_info "=========================================="
    log_info "AutoSelect Deployment Script"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Timestamp: ${TIMESTAMP}"
    log_info "=========================================="
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "DRY RUN MODE - No changes will be made"
    fi
    
    if [[ ${ROLLBACK} -eq 1 ]]; then
        rollback_deployment
        return 0
    fi
    
    check_prerequisites
    initialize_environment
    
    install_frontend_dependencies
    install_backend_dependencies
    
    run_frontend_tests
    run_backend_tests
    
    build_frontend
    build_backend
    build_docker_images
    
    deploy_application
    health_check
    
    log_info "=========================================="
    log_info "Deployment completed successfully!"
    log_info "Frontend: http://localhost:${FRONTEND_PORT}"
    log_info "Backend: http://localhost:${BACKEND_PORT}"
    log_info "Log file: ${LOG_FILE}"
    log_info "=========================================="
}

# Parse arguments and run
parse_args "$@"
main