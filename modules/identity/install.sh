#!/bin/bash

# ITADIAS Identity Microservice Installation Script
# This script sets up the complete microservice environment

set -e

echo "🚀 ITADIAS Identity Microservice Installation"
echo "============================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    success "Docker and Docker Compose are available"
}

# Check if Python is installed (for local development)
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d " " -f 2)
        info "Python $PYTHON_VERSION detected"
    else
        warning "Python 3 not found. Required for local development."
    fi
}

# Install Python dependencies
install_python_deps() {
    if [[ "$1" == "--local" ]]; then
        info "Installing Python dependencies for local development..."
        
        if command -v python3 &> /dev/null; then
            # Create virtual environment if it doesn't exist
            if [ ! -d "venv" ]; then
                info "Creating virtual environment..."
                python3 -m venv venv
            fi
            
            # Activate virtual environment
            source venv/bin/activate
            
            # Upgrade pip
            pip install --upgrade pip
            
            # Install dependencies
            pip install -r requirements.txt
            
            success "Python dependencies installed in virtual environment"
            info "To activate: source venv/bin/activate"
        else
            error "Python 3 is required for local development"
            exit 1
        fi
    fi
}

# Setup environment file
setup_environment() {
    info "Setting up environment configuration..."
    
    if [ ! -f ".env.local" ]; then
        cp .env .env.local
        success "Created .env.local from template"
        
        warning "Please configure your API keys in .env.local:"
        echo "  - SENDGRID_API_KEY for email OTP"
        echo "  - TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN for SMS OTP"
    else
        info ".env.local already exists"
    fi
}

# Start services with Docker Compose
start_services() {
    info "Starting services with Docker Compose..."
    
    # Pull latest images
    docker-compose pull
    
    # Build and start services
    docker-compose up -d --build
    
    # Wait for services to be ready
    info "Waiting for services to start..."
    sleep 10
    
    # Check service health
    check_service_health
}

# Check service health
check_service_health() {
    info "Checking service health..."
    
    # Check PostgreSQL
    if docker-compose exec postgres pg_isready -U identity_user -d identity_db > /dev/null 2>&1; then
        success "PostgreSQL is ready"
    else
        error "PostgreSQL is not ready"
    fi
    
    # Check RabbitMQ
    if docker-compose exec rabbitmq rabbitmq-diagnostics ping > /dev/null 2>&1; then
        success "RabbitMQ is ready"
    else
        error "RabbitMQ is not ready"
    fi
    
    # Check Identity Service
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        success "Identity Service is ready"
    else
        warning "Identity Service health check failed"
    fi
}

# Run tests
run_tests() {
    info "Running unit tests..."
    
    if [[ "$1" == "--local" ]]; then
        # Run tests locally
        if [ -d "venv" ]; then
            source venv/bin/activate
            pytest
        else
            pytest
        fi
    else
        # Run tests in Docker
        docker-compose exec identity-service pytest
    fi
}

# Display service information
display_info() {
    echo ""
    echo "🎉 Installation Complete!"
    echo "========================"
    echo ""
    echo "📋 Service Information:"
    echo "  Identity Service: http://localhost:8001"
    echo "  API Documentation: http://localhost:8001/docs"
    echo "  Health Check: http://localhost:8001/health"
    echo "  RabbitMQ Management: http://localhost:15672 (guest/guest)"
    echo ""
    echo "🔧 Useful Commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop services: docker-compose down"
    echo "  Restart: docker-compose restart"
    echo "  Run tests: docker-compose exec identity-service pytest"
    echo ""
    echo "📖 Documentation:"
    echo "  README.md - Complete documentation"
    echo "  openapi.yaml - API specification"
    echo ""
}

# Main installation function
main() {
    echo ""
    
    # Parse command line arguments
    LOCAL_DEV=false
    RUN_TESTS=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --local)
                LOCAL_DEV=true
                shift
                ;;
            --test)
                RUN_TESTS=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --local    Setup for local development (install Python deps)"
                echo "  --test     Run tests after installation"
                echo "  --help     Show this help message"
                echo ""
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Run installation steps
    check_docker
    check_python
    setup_environment
    
    if [ "$LOCAL_DEV" = true ]; then
        install_python_deps --local
        info "Local development setup complete"
        info "You can now run: python app.py"
    else
        start_services
    fi
    
    if [ "$RUN_TESTS" = true ]; then
        if [ "$LOCAL_DEV" = true ]; then
            run_tests --local
        else
            run_tests
        fi
    fi
    
    display_info
}

# Run main function
main "$@"