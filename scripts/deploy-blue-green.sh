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
#   -s, --skip-tests    Skip test execution
#   -f, --force         Force deployment without confirmation
#
# Requirements:
#   - Docker and Docker Compose
#   - Node.js 20.x
#   - Python 3.11
#   - PostgreSQL client
#   - Redis client

set -euo pipefail
IFS=$'\n\t'

# Script metadata
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
readonly SCRIPT_VERSION="1.0.0"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
readonly ENVIRONMENT="dev"
readonly FRONTEND_DIR="${PROJECT_ROOT}/frontend"
readonly BACKEND_DIR="${PROJECT_ROOT}/backend"
readonly LOG_DIR="${PROJECT_ROOT}/logs"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
readonly LOG_FILE="${LOG_DIR}/deploy_${TIMESTAMP}.log"

# Deployment settings
VERBOSE=0
DRY_RUN=0
SKIP_TESTS=0
FORCE=0

# Logging functions
log_info() {
    local message="$*"
    echo -e "${GREEN}[INFO]${NC} ${message}" | tee -a "${LOG_FILE}"
}

log_warn() {
    local message="$*"
    echo -e "${YELLOW}[WARN]${NC} ${message}" | tee -a "${LOG_FILE}"
}

log_error() {
    local message="$*"
    echo -e "${RED}[ERROR]${NC} ${message}" | tee -a "${LOG_FILE}"
}

log_debug() {
    if [[ ${VERBOSE} -eq 1 ]]; then
        local message="$*"
        echo -e "${BLUE}[DEBUG]${NC} ${message}" | tee -a "${LOG_FILE}"
    fi
}

log_step() {
    local message="$*"
    echo -e "\n${BLUE}==>${NC} ${message}" | tee -a "${LOG_FILE}"
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

# Cleanup on error
cleanup_on_error() {
    log_warn "Performing cleanup..."
    
    if [[ -f "${FRONTEND_DIR}/.env.local" ]]; then
        rm -f "${FRONTEND_DIR}/.env.local"
    fi
    
    if [[ -f "${BACKEND_DIR}/.env.local" ]]; then
        rm -f "${BACKEND_DIR}/.env.local"
    fi
}

# Cleanup on exit
cleanup() {
    local exit_code=$?
    
    if [[ ${exit_code} -eq 0 ]]; then
        log_info "Deployment completed successfully"
    fi
    
    exit "${exit_code}"
}

trap cleanup EXIT

# Show help
show_help() {
    cat << EOF
AutoSelect Deployment Script v${SCRIPT_VERSION}

Usage: ${SCRIPT_NAME} [OPTIONS]

Options:
    -h, --help          Show this help message
    -v, --verbose       Enable verbose output
    -d, --dry-run       Run without making changes
    -s, --skip-tests    Skip test execution
    -f, --force         Force deployment without confirmation

Environment: ${ENVIRONMENT}

Examples:
    ${SCRIPT_NAME}                    # Standard deployment
    ${SCRIPT_NAME} -v                 # Verbose deployment
    ${SCRIPT_NAME} -d                 # Dry run
    ${SCRIPT_NAME} -s -f              # Skip tests and force

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
            -s|--skip-tests)
                SKIP_TESTS=1
                shift
                ;;
            -f|--force)
                FORCE=1
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
    log_step "Checking prerequisites"
    
    local required_commands=("docker" "docker-compose" "node" "npm" "python3" "pip3" "psql" "redis-cli")
    local missing_commands=()
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "${cmd}" &>/dev/null; then
            missing_commands+=("${cmd}")
        fi
    done
    
    if [[ ${#missing_commands[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing_commands[*]}"
        return 1
    fi
    
    # Check Node.js version
    local node_version
    node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ ${node_version} -lt 20 ]]; then
        log_error "Node.js 20.x or higher required (found: ${node_version})"
        return 1
    fi
    
    # Check Python version
    local python_version
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ "${python_version}" != "3.11" ]]; then
        log_warn "Python 3.11 recommended (found: ${python_version})"
    fi
    
    # Check Docker daemon
    if ! docker info &>/dev/null; then
        log_error "Docker daemon not running"
        return 1
    fi
    
    log_info "All prerequisites satisfied"
}

# Validate environment
validate_environment() {
    log_step "Validating environment"
    
    # Check project structure
    local required_dirs=("${FRONTEND_DIR}" "${BACKEND_DIR}")
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "${dir}" ]]; then
            log_error "Required directory not found: ${dir}"
            return 1
        fi
    done
    
    # Check required files
    if [[ ! -f "${FRONTEND_DIR}/package.json" ]]; then
        log_error "Frontend package.json not found"
        return 1
    fi
    
    if [[ ! -f "${BACKEND_DIR}/requirements.txt" ]]; then
        log_error "Backend requirements.txt not found"
        return 1
    fi
    
    # Create log directory
    mkdir -p "${LOG_DIR}"
    
    log_info "Environment validation passed"
}

# Setup environment variables
setup_environment_variables() {
    log_step "Setting up environment variables"
    
    # Backend environment
    cat > "${BACKEND_DIR}/.env.local" << EOF
# AutoSelect Backend - Development Environment
# Generated: ${TIMESTAMP}

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=debug

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database
DATABASE_URL=postgresql://autoselect:autoselect@localhost:5432/autoselect_dev
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# Security
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET=dev-jwt-secret-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# File Upload
MAX_UPLOAD_SIZE=10485760
UPLOAD_DIR=/tmp/autoselect/uploads

# Email (Development)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=noreply@autoselect.local

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
EOF
    
    # Frontend environment
    cat > "${FRONTEND_DIR}/.env.local" << EOF
# AutoSelect Frontend - Development Environment
# Generated: ${TIMESTAMP}

# API Configuration
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# Application
VITE_APP_NAME=AutoSelect
VITE_APP_VERSION=1.0.0
VITE_ENVIRONMENT=development

# Features
VITE_ENABLE_ANALYTICS=false
VITE_ENABLE_DEBUG=true

# Build
VITE_BUILD_TARGET=es2020
VITE_SOURCEMAP=true
EOF
    
    log_info "Environment variables configured"
}

# Install backend dependencies
install_backend_dependencies() {
    log_step "Installing backend dependencies"
    
    cd "${BACKEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_info "[DRY RUN] Would install Python dependencies"
        return 0
    fi
    
    # Create virtual environment if not exists
    if [[ ! -d "venv" ]]; then
        log_debug "Creating Python virtual environment"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    log_debug "Upgrading pip"
    pip install --upgrade pip --quiet
    
    # Install dependencies
    log_debug "Installing Python packages"
    pip install -r requirements.txt --quiet
    
    log_info "Backend dependencies installed"
}

# Install frontend dependencies
install_frontend_dependencies() {
    log_step "Installing frontend dependencies"
    
    cd "${FRONTEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_info "[DRY RUN] Would install Node.js dependencies"
        return 0
    fi
    
    # Clean install
    log_debug "Running npm install"
    npm install --loglevel=error
    
    log_info "Frontend dependencies installed"
}

# Run database migrations
run_database_migrations() {
    log_step "Running database migrations"
    
    cd "${BACKEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_info "[DRY RUN] Would run database migrations"
        return 0
    fi
    
    # Check database connectivity
    if ! psql "${DATABASE_URL:-postgresql://autoselect:autoselect@localhost:5432/autoselect_dev}" -c "SELECT 1" &>/dev/null; then
        log_error "Cannot connect to database"
        return 1
    fi
    
    # Run migrations
    source venv/bin/activate
    log_debug "Applying database migrations"
    alembic upgrade head
    
    log_info "Database migrations completed"
}

# Run tests
run_tests() {
    if [[ ${SKIP_TESTS} -eq 1 ]]; then
        log_warn "Skipping tests (--skip-tests flag)"
        return 0
    fi
    
    log_step "Running tests"
    
    # Backend tests
    log_debug "Running backend tests"
    cd "${BACKEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_info "[DRY RUN] Would run backend tests"
    else
        source venv/bin/activate
        pytest --quiet --tb=short || {
            log_error "Backend tests failed"
            return 1
        }
    fi
    
    # Frontend tests
    log_debug "Running frontend tests"
    cd "${FRONTEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_info "[DRY RUN] Would run frontend tests"
    else
        npm run test -- --run --reporter=basic || {
            log_error "Frontend tests failed"
            return 1
        }
    fi
    
    log_info "All tests passed"
}

# Build frontend
build_frontend() {
    log_step "Building frontend"
    
    cd "${FRONTEND_DIR}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_info "[DRY RUN] Would build frontend"
        return 0
    fi
    
    # Type check
    log_debug "Running TypeScript type check"
    npm run type-check
    
    # Lint
    log_debug "Running ESLint"
    npm run lint
    
    # Build
    log_debug "Building production bundle"
    npm run build
    
    log_info "Frontend build completed"
}

# Start services
start_services() {
    log_step "Starting services"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_info "[DRY RUN] Would start services"
        return 0
    fi
    
    # Start backend
    log_debug "Starting backend server"
    cd "${BACKEND_DIR}"
    source venv/bin/activate
    
    nohup uvicorn src.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 4 \
        --log-level info \
        > "${LOG_DIR}/backend_${TIMESTAMP}.log" 2>&1 &
    
    local backend_pid=$!
    echo "${backend_pid}" > "${LOG_DIR}/backend.pid"
    
    # Wait for backend to be ready
    log_debug "Waiting for backend to be ready"
    local max_attempts=30
    local attempt=1
    
    while [[ ${attempt} -le ${max_attempts} ]]; do
        if curl -sf http://localhost:8000/health &>/dev/null; then
            log_info "Backend server started (PID: ${backend_pid})"
            break
        fi
        
        if [[ ${attempt} -eq ${max_attempts} ]]; then
            log_error "Backend failed to start"
            return 1
        fi
        
        sleep 2
        ((attempt++))
    done
    
    # Start frontend
    log_debug "Starting frontend server"
    cd "${FRONTEND_DIR}"
    
    nohup npm run preview \
        > "${LOG_DIR}/frontend_${TIMESTAMP}.log" 2>&1 &
    
    local frontend_pid=$!
    echo "${frontend_pid}" > "${LOG_DIR}/frontend.pid"
    
    # Wait for frontend to be ready
    log_debug "Waiting for frontend to be ready"
    attempt=1
    
    while [[ ${attempt} -le ${max_attempts} ]]; do
        if curl -sf http://localhost:4173 &>/dev/null; then
            log_info "Frontend server started (PID: ${frontend_pid})"
            break
        fi
        
        if [[ ${attempt} -eq ${max_attempts} ]]; then
            log_error "Frontend failed to start"
            return 1
        fi
        
        sleep 2
        ((attempt++))
    done
    
    log_info "All services started successfully"
}

# Health check
health_check() {
    log_step "Running health checks"
    
    # Backend health
    if ! curl -sf http://localhost:8000/health &>/dev/null; then
        log_error "Backend health check failed"
        return 1
    fi
    log_info "Backend health check passed"
    
    # Frontend health
    if ! curl -sf http://localhost:4173 &>/dev/null; then
        log_error "Frontend health check failed"
        return 1
    fi
    log_info "Frontend health check passed"
    
    # Database connectivity
    if ! psql "${DATABASE_URL:-postgresql://autoselect:autoselect@localhost:5432/autoselect_dev}" -c "SELECT 1" &>/dev/null; then
        log_error "Database connectivity check failed"
        return 1
    fi
    log_info "Database connectivity check passed"
    
    # Redis connectivity
    if ! redis-cli -u "${REDIS_URL:-redis://localhost:6379/0}" ping &>/dev/null; then
        log_error "Redis connectivity check failed"
        return 1
    fi
    log_info "Redis connectivity check passed"
    
    log_info "All health checks passed"
}

# Display deployment summary
display_summary() {
    log_step "Deployment Summary"
    
    cat << EOF

${GREEN}✓${NC} Deployment completed successfully!

Environment:     ${ENVIRONMENT}
Timestamp:       ${TIMESTAMP}
Log File:        ${LOG_FILE}

Services:
  Backend:       http://localhost:8000
  Frontend:      http://localhost:4173
  API Docs:      http://localhost:8000/docs
  Metrics:       http://localhost:9090/metrics

Process IDs:
  Backend:       $(cat "${LOG_DIR}/backend.pid" 2>/dev/null || echo "N/A")
  Frontend:      $(cat "${LOG_DIR}/frontend.pid" 2>/dev/null || echo "N/A")

To stop services:
  kill \$(cat ${LOG_DIR}/backend.pid)
  kill \$(cat ${LOG_DIR}/frontend.pid)

EOF
}

# Main deployment function
main() {
    log_info "AutoSelect Deployment Script v${SCRIPT_VERSION}"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Timestamp: ${TIMESTAMP}"
    
    if [[ ${DRY_RUN} -eq 1 ]]; then
        log_warn "DRY RUN MODE - No changes will be made"
    fi
    
    # Confirmation prompt
    if [[ ${FORCE} -eq 0 ]] && [[ ${DRY_RUN} -eq 0 ]]; then
        read -p "Deploy to ${ENVIRONMENT}? (y/N) " -n 1 -r
        echo
        if [[ ! ${REPLY} =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi
    
    # Execute deployment pipeline
    check_prerequisites
    validate_environment
    setup_environment_variables
    install_backend_dependencies
    install_frontend_dependencies
    run_database_migrations
    run_tests
    build_frontend
    start_services
    health_check
    display_summary
}

# Parse arguments and run
parse_args "$@"
main