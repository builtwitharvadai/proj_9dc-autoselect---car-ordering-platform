#!/usr/bin/env bash

# =============================================================================
# AutoSelect - Docker Setup Script
# =============================================================================
# Description: Initial Docker environment setup and service orchestration
# Usage: ./scripts/docker-setup.sh [OPTIONS]
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# -----------------------------------------------------------------------------
# Script Metadata
# -----------------------------------------------------------------------------
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly SCRIPT_VERSION="1.0.0"

# -----------------------------------------------------------------------------
# Color Codes
# -----------------------------------------------------------------------------
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
readonly ENV_EXAMPLE="${PROJECT_ROOT}/.env.example"
readonly ENV_FILE="${PROJECT_ROOT}/.env"
readonly DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
readonly MAX_RETRIES=3
readonly RETRY_DELAY=5
readonly HEALTH_CHECK_TIMEOUT=60
readonly HEALTH_CHECK_INTERVAL=5

# Service ports
readonly BACKEND_PORT=8000
readonly FRONTEND_PORT=3000
readonly POSTGRES_PORT=5432
readonly REDIS_PORT=6379

# -----------------------------------------------------------------------------
# Logging Functions
# -----------------------------------------------------------------------------
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_debug() {
    if [[ "${DEBUG:-0}" == "1" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*" >&2
    fi
}

log_step() {
    echo -e "\n${BLUE}==>${NC} $*" >&2
}

# -----------------------------------------------------------------------------
# Error Handling
# -----------------------------------------------------------------------------
cleanup() {
    local exit_code=$?
    
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "Docker setup failed with exit code ${exit_code}"
        log_info "Run 'docker-compose logs' to view service logs"
        log_info "Run 'docker-compose down' to clean up containers"
    fi
    
    exit "${exit_code}"
}

trap cleanup EXIT ERR INT TERM

# -----------------------------------------------------------------------------
# Validation Functions
# -----------------------------------------------------------------------------
check_prerequisites() {
    log_step "Checking prerequisites"
    
    local required_commands=("docker" "docker-compose")
    local missing_commands=()
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "${cmd}" &>/dev/null; then
            missing_commands+=("${cmd}")
        fi
    done
    
    if [[ ${#missing_commands[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing_commands[*]}"
        log_error "Please install Docker and Docker Compose"
        log_error "Visit: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    log_info "Docker version: $(docker --version)"
    log_info "Docker Compose version: $(docker-compose --version)"
    
    # Check Docker daemon
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"
        log_error "Please start Docker and try again"
        return 1
    fi
    
    log_info "Prerequisites check passed"
    return 0
}

validate_project_structure() {
    log_step "Validating project structure"
    
    local required_files=(
        "${ENV_EXAMPLE}"
        "${DOCKER_COMPOSE_FILE}"
        "${PROJECT_ROOT}/backend/Dockerfile"
        "${PROJECT_ROOT}/frontend/Dockerfile"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "${file}" ]]; then
            log_error "Required file not found: ${file}"
            return 1
        fi
    done
    
    log_info "Project structure validation passed"
    return 0
}

# -----------------------------------------------------------------------------
# Environment Setup
# -----------------------------------------------------------------------------
setup_environment() {
    log_step "Setting up environment configuration"
    
    if [[ -f "${ENV_FILE}" ]]; then
        log_warn "Environment file already exists: ${ENV_FILE}"
        read -p "Overwrite existing .env file? (y/N) " -n 1 -r
        echo
        if [[ ! ${REPLY} =~ ^[Yy]$ ]]; then
            log_info "Keeping existing .env file"
            return 0
        fi
        
        # Backup existing file
        local backup="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "${ENV_FILE}" "${backup}"
        log_info "Backed up existing .env to ${backup}"
    fi
    
    # Copy example to .env
    if ! cp "${ENV_EXAMPLE}" "${ENV_FILE}"; then
        log_error "Failed to copy .env.example to .env"
        return 1
    fi
    
    log_info "Created .env file from .env.example"
    log_warn "Please review and update ${ENV_FILE} with your configuration"
    
    # Generate secure JWT secret if needed
    if command -v openssl &>/dev/null; then
        local jwt_secret
        jwt_secret=$(openssl rand -hex 32)
        
        if [[ -n "${jwt_secret}" ]]; then
            # Update JWT_SECRET_KEY in .env
            if grep -q "^JWT_SECRET_KEY=" "${ENV_FILE}"; then
                sed -i.bak "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${jwt_secret}|" "${ENV_FILE}"
                rm -f "${ENV_FILE}.bak"
                log_info "Generated secure JWT secret key"
            fi
        fi
    fi
    
    return 0
}

# -----------------------------------------------------------------------------
# Docker Operations
# -----------------------------------------------------------------------------
build_images() {
    log_step "Building Docker images"
    
    local build_args=()
    
    if [[ "${DEBUG:-0}" == "1" ]]; then
        build_args+=("--progress=plain")
    fi
    
    log_info "Building backend image..."
    if ! docker-compose build "${build_args[@]}" backend; then
        log_error "Failed to build backend image"
        return 1
    fi
    
    log_info "Building frontend image..."
    if ! docker-compose build "${build_args[@]}" frontend; then
        log_error "Failed to build frontend image"
        return 1
    fi
    
    log_info "Docker images built successfully"
    return 0
}

start_services() {
    log_step "Starting Docker services"
    
    # Start services in detached mode
    if ! docker-compose up -d; then
        log_error "Failed to start Docker services"
        return 1
    fi
    
    log_info "Docker services started"
    return 0
}

# -----------------------------------------------------------------------------
# Database Operations
# -----------------------------------------------------------------------------
wait_for_postgres() {
    log_step "Waiting for PostgreSQL to be ready"
    
    local attempt=1
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))
    
    while [[ ${attempt} -le ${max_attempts} ]]; do
        if docker-compose exec -T postgres pg_isready -U postgres &>/dev/null; then
            log_info "PostgreSQL is ready"
            return 0
        fi
        
        log_debug "PostgreSQL not ready (attempt ${attempt}/${max_attempts})"
        sleep "${HEALTH_CHECK_INTERVAL}"
        ((attempt++))
    done
    
    log_error "PostgreSQL failed to become ready within ${HEALTH_CHECK_TIMEOUT}s"
    return 1
}

run_migrations() {
    log_step "Running database migrations"
    
    # Wait for PostgreSQL
    if ! wait_for_postgres; then
        return 1
    fi
    
    # Run Alembic migrations
    log_info "Applying database migrations..."
    if ! docker-compose exec -T backend alembic upgrade head; then
        log_error "Database migration failed"
        log_info "Check logs: docker-compose logs backend"
        return 1
    fi
    
    log_info "Database migrations completed successfully"
    return 0
}

# -----------------------------------------------------------------------------
# Health Checks
# -----------------------------------------------------------------------------
check_service_health() {
    local service="$1"
    local url="$2"
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))
    local attempt=1
    
    log_info "Checking ${service} health..."
    
    while [[ ${attempt} -le ${max_attempts} ]]; do
        if curl -sf "${url}" &>/dev/null; then
            log_info "${service} is healthy"
            return 0
        fi
        
        log_debug "${service} not ready (attempt ${attempt}/${max_attempts})"
        sleep "${HEALTH_CHECK_INTERVAL}"
        ((attempt++))
    done
    
    log_error "${service} health check failed"
    return 1
}

verify_services() {
    log_step "Verifying service health"
    
    local failed_services=()
    
    # Check backend
    if ! check_service_health "Backend" "http://localhost:${BACKEND_PORT}/health"; then
        failed_services+=("backend")
    fi
    
    # Check frontend
    if ! check_service_health "Frontend" "http://localhost:${FRONTEND_PORT}"; then
        failed_services+=("frontend")
    fi
    
    # Check Redis
    if ! docker-compose exec -T redis redis-cli ping &>/dev/null; then
        log_error "Redis health check failed"
        failed_services+=("redis")
    else
        log_info "Redis is healthy"
    fi
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        log_error "Health checks failed for: ${failed_services[*]}"
        log_info "View logs with: docker-compose logs <service>"
        return 1
    fi
    
    log_info "All services are healthy"
    return 0
}

# -----------------------------------------------------------------------------
# Status Display
# -----------------------------------------------------------------------------
display_status() {
    log_step "Docker Setup Complete"
    
    echo ""
    echo "Services are running:"
    echo "  Backend:   http://localhost:${BACKEND_PORT}"
    echo "  Frontend:  http://localhost:${FRONTEND_PORT}"
    echo "  API Docs:  http://localhost:${BACKEND_PORT}/docs"
    echo "  PostgreSQL: localhost:${POSTGRES_PORT}"
    echo "  Redis:     localhost:${REDIS_PORT}"
    echo ""
    echo "Useful commands:"
    echo "  View logs:        docker-compose logs -f [service]"
    echo "  Stop services:    docker-compose stop"
    echo "  Restart services: docker-compose restart"
    echo "  Shutdown:         docker-compose down"
    echo "  Rebuild:          docker-compose build --no-cache"
    echo ""
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
main() {
    log_info "AutoSelect Docker Setup v${SCRIPT_VERSION}"
    log_info "Project root: ${PROJECT_ROOT}"
    
    # Change to project root
    cd "${PROJECT_ROOT}"
    
    # Run setup steps
    check_prerequisites || exit 1
    validate_project_structure || exit 1
    setup_environment || exit 1
    build_images || exit 1
    start_services || exit 1
    run_migrations || exit 1
    verify_services || exit 1
    
    # Display status
    display_status
    
    log_info "Docker setup completed successfully"
    return 0
}

# Execute main function
main "$@"