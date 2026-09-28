#!/usr/bin/env bash
# Bearpaws installation script
# Sets up experimental platform-specific symlinks for Codex, Devin for Terminal, and Windsurf Cascade,
# and the native Google Antigravity plugin

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

# Reconcile skill symlinks from source_dir into target_dir.
# Target dirs may be shared with the user's own skills (e.g. ~/.agents/skills),
# so only broken links that pointed into source_dir are pruned, and entries
# with a colliding name that are not links into source_dir are never replaced.
create_symlinks() {
    local source_dir="$1"
    local target_dir="$2"

    mkdir -p "$target_dir"

    local source_real
    source_real="$(cd "$source_dir" && pwd -P)"

    local pruned=0
    local link dest parent
    for link in "$target_dir"/*; do
        [[ -L "$link" && ! -e "$link" ]] || continue
        dest="$(readlink "$link")"
        [[ "$dest" == /* ]] || dest="$target_dir/$dest"
        parent="$(cd "$(dirname "$dest")" 2>/dev/null && pwd -P)" || continue
        if [[ "$parent" == "$source_real" ]]; then
            rm -f "$link"
            pruned=$((pruned + 1))
        fi
    done
    if [[ $pruned -gt 0 ]]; then
        log_warning "Removed $pruned stale Bearpaws symlinks from $target_dir"
    fi

    local skills_created=0
    local skill_dir skill_name
    for skill_dir in "$source_dir"/*/; do
        [[ -d "$skill_dir" ]] || continue
        skill_name="$(basename "$skill_dir")"
        link="$target_dir/$skill_name"
        if [[ -L "$link" ]]; then
            dest="$(readlink "$link")"
            [[ "$dest" == /* ]] || dest="$target_dir/$dest"
            parent="$(cd "$(dirname "$dest")" 2>/dev/null && pwd -P)" || parent=""
            if [[ "$parent" != "$source_real" ]]; then
                log_warning "Skipping $skill_name: $link links outside Bearpaws ($dest)"
                continue
            fi
        elif [[ -e "$link" ]]; then
            log_warning "Skipping $skill_name: $link exists and is not a symlink"
            continue
        fi
        ln -sfn "$skill_dir" "$target_dir/$skill_name"
        skills_created=$((skills_created + 1))
    done

    log_success "Linked $skills_created skills in $target_dir"
}

# Install for Devin for Terminal
install_devin() {
    log_info "Setting up experimental Devin for Terminal wiring..."
    
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
    log_info "Setting up experimental Windsurf Cascade wiring..."
    
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

# Install for Codex (Agent Skills discovered from .agents/skills)
install_codex() {
    log_info "Setting up experimental Codex wiring..."

    # Project-level installation
    create_symlinks "$BEARPAWS_ROOT/skills" "$BEARPAWS_ROOT/.agents/skills"

    # Global installation (optional)
    if [[ "${INSTALL_GLOBAL:-}" == "true" ]]; then
        log_info "Setting up global Codex installation..."
        create_symlinks "$BEARPAWS_ROOT/skills" "$HOME/.agents/skills"
    fi
}

# Install for Google Antigravity
install_antigravity() {
    log_info "Setting up Google Antigravity plugin..."
    if [[ "${INSTALL_GLOBAL:-}" != "true" ]]; then
        log_error "Antigravity installation currently requires --global"
        log_info "Use: ./install.sh --antigravity --global"
        return 1
    fi

    if [[ ! -f "$BEARPAWS_ROOT/.antigravity/plugin.json" ]]; then
        log_error "Plugin manifest missing: .antigravity/plugin.json"
        return 1
    fi

    if [[ ! -f "$BEARPAWS_ROOT/.antigravity/rules/bearpaws.md" ]]; then
        log_error "Plugin bootstrap rule missing: .antigravity/rules/bearpaws.md"
        return 1
    fi

    local plugin_root="$HOME/.gemini/config/plugins/bearpaws"
    local plugin_parent
    plugin_parent="$(dirname "$plugin_root")"

    mkdir -p "$plugin_parent"

    local staging
    staging="$(mktemp -d "$plugin_parent/.bearpaws-install.XXXXXX")" || {
        log_error "Failed to create staging directory in $plugin_parent"
        return 1
    }
    trap 'rm -rf "$staging"' EXIT

    mkdir -p "$staging/rules"
    mkdir -p "$staging/skills"
    mkdir -p "$staging/agents"

    cp "$BEARPAWS_ROOT/.antigravity/plugin.json" "$staging/plugin.json"
    cp -R "$BEARPAWS_ROOT/.antigravity/rules/." "$staging/rules/"
    cp -R "$BEARPAWS_ROOT/skills/." "$staging/skills/"
    cp -R "$BEARPAWS_ROOT/agents/." "$staging/agents/"

    local backup=""
    if [[ -d "$plugin_root" ]]; then
        backup="$(mktemp -d "$plugin_parent/.bearpaws-backup.XXXXXX")"
        rmdir "$backup"
        mv "$plugin_root" "$backup"
    fi

    if mv "$staging" "$plugin_root"; then
        [[ -n "$backup" ]] && rm -rf "$backup"
        trap - EXIT
        log_success "Installed BearPaws for Antigravity: $plugin_root"
    else
        log_error "Failed to move staged plugin to $plugin_root"
        [[ -n "$backup" ]] && mv "$backup" "$plugin_root"
        return 1
    fi
}

# Main installation
main() {
    local platforms=()
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --antigravity)
                platforms+=("antigravity")
                shift
                ;;
            --codex)
                platforms+=("codex")
                shift
                ;;
            --devin)
                platforms+=("devin")
                shift
                ;;
            --windsurf)
                platforms+=("windsurf")
                shift
                ;;
            --all)
                platforms=("codex" "devin" "windsurf")
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
                echo "  --antigravity Install BearPaws for Google Antigravity"
                echo "  --codex       Install experimental Codex wiring (.agents/skills)"
                echo "  --devin       Install experimental Devin for Terminal wiring"
                echo "  --windsurf    Install experimental Windsurf Cascade wiring"
                echo "  --all         Install experimental wiring for Codex, Devin, and Windsurf (default)"
                echo "  --global      Install globally where supported (required for Antigravity)"
                echo "  --help        Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0 --antigravity --global   # Install BearPaws plugin for Antigravity"
                echo "  $0 --all                    # Install experimental wiring for all three platforms"
                echo "  $0 --codex --global         # Install experimental Codex wiring into ~/.agents/skills too"
                echo "  $0 --devin                  # Install experimental Devin wiring only"
                echo "  $0 --windsurf               # Install experimental Windsurf wiring only"
                echo "  $0 --devin --global         # Install experimental Devin wiring globally too"
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
        platforms=("codex" "devin" "windsurf")
    fi
    
    log_info "Installing for platforms: ${platforms[*]}"
    
    local failed=0
    
    for platform in "${platforms[@]}"; do
        case $platform in
            antigravity)
                if ! install_antigravity; then
                    failed=$((failed + 1))
                fi
                ;;
            codex)
                if ! install_codex; then
                    failed=$((failed + 1))
                fi
                ;;
            devin)
                if ! install_devin; then
                    failed=$((failed + 1))
                fi
                ;;
            windsurf)
                if ! install_windsurf; then
                    failed=$((failed + 1))
                fi
                ;;
            *)
                log_error "Unknown platform: $platform"
                failed=$((failed + 1))
                ;;
        esac
    done
    
    echo ""
    if [[ $failed -eq 0 ]]; then
        log_success "Bearpaws installation completed successfully!"
        echo ""
        echo "Next steps:"
        if [[ " ${platforms[*]} " =~ " antigravity " ]]; then
            echo "  • Google Antigravity: Plugin installed in ~/.gemini/config/plugins/bearpaws/"
            echo "  • Restart Antigravity to discover skills and apply the bootstrap rule"
        fi
        if [[ " ${platforms[*]} " =~ " codex " ]]; then
            echo "  • Codex (experimental): Skills are now available in .agents/skills/"
            if [[ "${INSTALL_GLOBAL:-}" == "true" ]]; then
                echo "  • Global Codex (experimental): Skills are also available in ~/.agents/skills/"
            fi
        fi
        if [[ " ${platforms[*]} " =~ " devin " ]]; then
            echo "  • Devin for Terminal (experimental): Skills are now available in .devin/skills/"
            if [[ "${INSTALL_GLOBAL:-}" == "true" ]]; then
                echo "  • Global Devin (experimental): Skills are also available in ~/.config/devin/skills/"
            fi
        fi
        if [[ " ${platforms[*]} " =~ " windsurf " ]]; then
            echo "  • Windsurf Cascade (experimental): Skills are now available in .windsurf/skills/"
            echo "  • Bootstrap rule: .windsurf/rules/bearpaws.md is present; verify activation in Windsurf"
        fi
    else
        log_error "$failed platform installations failed"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
