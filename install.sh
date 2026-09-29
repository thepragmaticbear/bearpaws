#!/usr/bin/env bash
# Bearpaws installation script
# Installs Bearpaws for Antigravity, and experimental ~/.agents/skills wiring for other Agent Skills agents

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
        
        # Remove only broken symlinks belonging to Bearpaws; the target directory
        # may be shared with other skills packs whose links must be preserved even
        # when their targets are temporarily unavailable.
        local broken_symlinks=0
        for skill in "$target_dir"/*; do
            if [[ -L "$skill" && ! -e "$skill" ]]; then
                case "$(readlink "$skill" 2>/dev/null)" in
                    "$platform_dir"/*)
                        rm "$skill"
                        ((++broken_symlinks))
                        ;;
                    *)
                        ;;
                esac
            fi
        done
        
        if [[ $broken_symlinks -gt 0 ]]; then
            log_warning "Removed $broken_symlinks broken symlinks"
        fi
    fi
    
    mkdir -p "$target_dir"
    
    local skills_created=0
    for skill_dir in "$platform_dir"/*/; do
        if [[ -d "$skill_dir" ]]; then
            local skill_name="$(basename "$skill_dir")"
            local dest="$target_dir/$skill_name"
            # Never clobber entries we didn't create; refresh only our own links
            if [[ -e "$dest" || -L "$dest" ]]; then
                case "$(readlink "$dest" 2>/dev/null)" in
                    "$platform_dir/$skill_name"|"$platform_dir/$skill_name"/) ;;
                    *)
                        log_warning "Skipping $skill_name: $dest exists and is not a Bearpaws link"
                        continue
                        ;;
                esac
            fi
            ln -sfn "$skill_dir" "$dest"
            ((++skills_created))
        fi
    done
    
    log_success "Created $skills_created symlinks in $target_dir"
}

# Install for Agent Skills agents (Codex, Devin, OpenCode, Cursor, Copilot, ...) via ~/.agents/skills
install_agents() {
    log_info "Setting up experimental Agent Skills wiring..."
    if [[ "${INSTALL_GLOBAL:-}" != "true" ]]; then
        log_error "Agents installation currently requires --global"
        log_info "Use: ./install.sh --agents --global"
        return 1
    fi
    create_symlinks "$BEARPAWS_ROOT/skills" "$HOME/.agents/skills"
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
    trap "rm -rf $(printf %q "$staging")" EXIT

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
            --agents)
                platforms+=("agents")
                shift
                ;;
            --global)
                export INSTALL_GLOBAL="true"
                shift
                ;;
            --help|-h)
                echo "Bearpaws installation script"
                echo ""
                echo "Usage: $0 --antigravity --global | --agents --global"
                echo ""
                echo "Options:"
                echo "  --antigravity Install BearPaws plugin for Google Antigravity"
                echo "  --agents      Link skills into ~/.agents/skills (Codex, Devin, OpenCode, Cursor, Copilot, ...)"
                echo "  --global      Required for both targets"
                echo "  --help        Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    if [[ ${#platforms[@]} -eq 0 ]]; then
        log_error "No platform given"
        echo "Use --help for usage information"
        exit 1
    fi
    
    log_info "Installing for platforms: ${platforms[*]}"
    
    local failed=0
    
    for platform in "${platforms[@]}"; do
        case $platform in
            antigravity)
                if ! install_antigravity; then
                    ((++failed))
                fi
                ;;
            agents)
                if ! install_agents; then
                    ((++failed))
                fi
                ;;
            *)
                log_error "Unknown platform: $platform"
                ((++failed))
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
        if [[ " ${platforms[*]} " =~ " agents " ]]; then
            echo "  • Agent Skills (experimental): Skills are now available in ~/.agents/skills/"
            echo "  • Restart your agent; invoke using-bearpaws or let descriptions trigger skills"
            echo "  • OpenCode bootstrap: add to ~/.config/opencode/opencode.json:"
            echo '      "instructions": ["~/.agents/skills/using-bearpaws/SKILL.md"]'
        fi
    else
        log_error "$failed platform installations failed"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
