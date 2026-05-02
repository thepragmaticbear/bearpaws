#!/usr/bin/env bash
# Bearpaws installation script
# Sets up platform-specific symlinks for Devin for Terminal and Windsurf Cascade

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BEARPAWS_ROOT="$(cd "$SCRIPT_DIR" && pwd)"

# Verify we're in the bearpaws repository
if [[ ! -f "$BEARPAWS_ROOT/skills/using-bearpaws/SKILL.md" ]]; then
    log_error "This script must be run from the bearpaws repository root"
    exit 1
fi

log_info "Bearpaws installation script"
log_info "Repository root: $BEARPAWS_ROOT"

# Function to create symlinks for a platform
create_symlinks() {
    local platform_dir="$1"
    local target_dir="$2"
    
    if [[ -d "$target_dir" ]]; then
        log_warning "$target_dir already exists, checking existing symlinks..."
        
        # Check if existing symlinks point to the right place
        local broken_symlinks=0
        for skill in "$target_dir"/*; do
            if [[ -L "$skill" ]]; then
                if [[ ! -e "$skill" ]]; then
                    ((broken_symlinks++))
                fi
            fi
        done
        
        if [[ $broken_symlinks -gt 0 ]]; then
            log_warning "Found $broken_symlinks broken symlinks, removing them..."
            find "$target_dir" -type l -delete 2>/dev/null || true
        else
            log_success "$target_dir symlinks already exist and are valid"
            return 0
        fi
    fi
    
    mkdir -p "$target_dir"
    
    local skills_created=0
    for skill_dir in "$platform_dir"/*/; do
        if [[ -d "$skill_dir" ]]; then
            local skill_name="$(basename "$skill_dir")"
            ln -sfn "$skill_dir" "$target_dir/$skill_name"
            ((skills_created++))
        fi
    done
    
    log_success "Created $skills_created symlinks in $target_dir"
}

# Install for Devin for Terminal
install_devin() {
    log_info "Setting up Devin for Terminal support..."
    
    # Project-level installation
    create_symlinks "$BEARPAWS_ROOT/skills" "$BEARPAWS_ROOT/.devin/skills"
    
    # Global installation (optional)
    if [[ "${INSTALL_GLOBAL:-}" == "true" ]]; then
        log_info "Setting up global Devin installation..."
        local global_devin="$HOME/.config/devin/skills"
        create_symlinks "$BEARPAWS_ROOT/skills" "$global_devin"
    fi
}

# Install for Windsurf Cascade
install_windsurf() {
    log_info "Setting up Windsurf Cascade support..."
    
    # Create skills symlinks
    create_symlinks "$BEARPAWS_ROOT/skills" "$BEARPAWS_ROOT/.windsurf/skills"
    
    # Ensure rules directory exists and bootstrap rule is in place
    mkdir -p "$BEARPAWS_ROOT/.windsurf/rules"
    
    if [[ ! -f "$BEARPAWS_ROOT/.windsurf/rules/bearpaws.md" ]]; then
        log_error "Bootstrap rule missing: .windsurf/rules/bearpaws.md"
        return 1
    fi
    
    log_success "Windsurf bootstrap rule is in place"
}

# Main installation
main() {
    local platforms=()
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --devin)
                platforms+=("devin")
                shift
                ;;
            --windsurf)
                platforms+=("windsurf")
                shift
                ;;
            --all)
                platforms=("devin" "windsurf")
                shift
                ;;
            --global)
                export INSTALL_GLOBAL="true"
                shift
                ;;
            --help|-h)
                echo "Bearpaws installation script"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --devin     Install for Devin for Terminal"
                echo "  --windsurf  Install for Windsurf Cascade"
                echo "  --all       Install for both platforms (default)"
                echo "  --global    Also install globally (Devin only)"
                echo "  --help      Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0 --all                    # Install for both platforms"
                echo "  $0 --devin                  # Install only for Devin"
                echo "  $0 --windsurf               # Install only for Windsurf"
                echo "  $0 --devin --global         # Install for Devin globally too"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Default to all platforms if none specified
    if [[ ${#platforms[@]} -eq 0 ]]; then
        platforms=("devin" "windsurf")
    fi
    
    log_info "Installing for platforms: ${platforms[*]}"
    
    local failed=0
    
    for platform in "${platforms[@]}"; do
        case $platform in
            devin)
                if ! install_devin; then
                    ((failed++))
                fi
                ;;
            windsurf)
                if ! install_windsurf; then
                    ((failed++))
                fi
                ;;
            *)
                log_error "Unknown platform: $platform"
                ((failed++))
                ;;
        esac
    done
    
    echo ""
    if [[ $failed -eq 0 ]]; then
        log_success "Bearpaws installation completed successfully!"
        echo ""
        echo "Next steps:"
        if [[ " ${platforms[*]} " =~ " devin " ]]; then
            echo "  • Devin for Terminal: Skills are now available in .devin/skills/"
            if [[ "${INSTALL_GLOBAL:-}" == "true" ]]; then
                echo "  • Global Devin: Skills are also available in ~/.config/devin/skills/"
            fi
        fi
        if [[ " ${platforms[*]} " =~ " windsurf " ]]; then
            echo "  • Windsurf Cascade: Skills are now available in .windsurf/skills/"
            echo "  • Bootstrap rule: .windsurf/rules/bearpaws.md will auto-load at session start"
        fi
    else
        log_error "$failed platform installations failed"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"