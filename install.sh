#!/usr/bin/env bash
# Bearpaws installation script
# Installs Bearpaws for Antigravity, and experimental ~/.agents/skills wiring for other Agent Skills agents
# (plus a Grok Build bootstrap rule, ~/.junie/skills links for Junie, and a git commit-msg risk gate for the current repository)

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

# Print the skills root a Bearpaws link $1 (named $2) points into, and succeed,
# only if that root is this checkout ($3) or one recorded in $4 by an earlier
# install (a moved or re-cloned checkout). Links this installer never made,
# including other packs' and hand-made links to another checkout, never match.
bearpaws_link_root() {
    local link="$1" name="$2" platform_dir="$3" roots_file="$4"
    local target
    target="$(readlink "$link" 2>/dev/null)" || return 1
    target="${target%/}"
    [[ "${target##*/}" == "$name" ]] || return 1
    local root="${target%/*}"
    if [[ "$root" == "$platform_dir" ]] \
       || { [[ -f "$roots_file" ]] && grep -qxF -- "$root" "$roots_file"; }; then
        printf '%s\n' "$root"
        return 0
    fi
    return 1
}

# Function to create symlinks for a platform
create_symlinks() {
    local platform_dir="$1"
    local target_dir="$2"
    # Skills roots this installer has linked from, one per line
    local roots_file="$target_dir/.bearpaws-roots"
    
    if [[ -d "$target_dir" ]]; then
        log_warning "$target_dir already exists, checking existing symlinks..."
        
        # Remove only broken symlinks belonging to Bearpaws; the target directory
        # may be shared with other skills packs whose links must be preserved even
        # when their targets are temporarily unavailable.
        local broken_symlinks=0
        for skill in "$target_dir"/*; do
            if [[ -L "$skill" && ! -e "$skill" ]] \
               && bearpaws_link_root "$skill" "$(basename "$skill")" "$platform_dir" "$roots_file" >/dev/null; then
                rm "$skill"
                ((++broken_symlinks))
            fi
        done
        
        if [[ $broken_symlinks -gt 0 ]]; then
            log_warning "Removed $broken_symlinks broken symlinks"
        fi
    fi
    
    mkdir -p "$target_dir"
    if [[ ! -f "$roots_file" ]] || ! grep -qxF -- "$platform_dir" "$roots_file"; then
        printf '%s\n' "$platform_dir" >> "$roots_file"
    fi
    
    local skills_created=0
    for skill_dir in "$platform_dir"/*/; do
        if [[ -d "$skill_dir" ]]; then
            local skill_name
            skill_name="$(basename "$skill_dir")"
            local dest="$target_dir/$skill_name"
            # Never clobber entries we didn't create; refresh only our own links
            if [[ -e "$dest" || -L "$dest" ]]; then
                local old_root
                if ! old_root="$(bearpaws_link_root "$dest" "$skill_name" "$platform_dir" "$roots_file")"; then
                    local hint=""
                    if [[ -L "$dest" && ! -e "$dest" && "$(readlink "$dest")" == */skills/"$skill_name"* ]]; then
                        hint=" (dangling; if it is from an earlier Bearpaws checkout, remove it and re-run)"
                    fi
                    log_warning "Skipping $skill_name: $dest exists and is not a Bearpaws link$hint"
                    continue
                fi
                if [[ "$old_root" != "$platform_dir" ]]; then
                    log_info "Repointing $skill_name from $old_root"
                fi
            fi
            ln -sfn "$skill_dir" "$dest"
            ((++skills_created))
        fi
    done
    
    # Keep only roots that this checkout is or that a link still points into
    local kept_roots
    kept_roots="$(
        while IFS= read -r root; do
            if [[ "$root" == "$platform_dir" ]]; then
                printf '%s\n' "$root"
                continue
            fi
            for link in "$target_dir"/*; do
                if [[ -L "$link" ]] \
                   && [[ "$(bearpaws_link_root "$link" "$(basename "$link")" "$platform_dir" "$roots_file" || true)" == "$root" ]]; then
                    printf '%s\n' "$root"
                    break
                fi
            done
        done < "$roots_file"
    )"
    printf '%s\n' "$kept_roots" > "$roots_file"
    
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

# Install for JetBrains Junie: skills linked into $JUNIE_HOME/skills (default
# ~/.junie). The bootstrap is a line the user adds to ~/.junie/AGENTS.md; the
# installer prints it and never edits that file.
install_junie() {
    log_info "Setting up experimental Junie wiring..."
    if [[ "${INSTALL_GLOBAL:-}" != "true" ]]; then
        log_error "Junie installation currently requires --global"
        log_info "Use: ./install.sh --junie --global"
        return 1
    fi
    create_symlinks "$BEARPAWS_ROOT/skills" "${JUNIE_HOME:-$HOME/.junie}/skills"
}

# Install for Grok Build: skills via ~/.agents/skills (scanned at Grok's user
# tier) and a bootstrap rule in $GROK_HOME/rules, which Grok loads in every
# project. Grok ignores SessionStart hook output, so a rule is the bootstrap.
GROK_RULE_MARKER="<!-- Managed by Bearpaws install.sh --grok. Delete this file to remove the bootstrap. -->"
install_grok() {
    log_info "Setting up experimental Grok Build wiring..."
    if [[ "${INSTALL_GLOBAL:-}" != "true" ]]; then
        log_error "Grok installation currently requires --global"
        log_info "Use: ./install.sh --grok --global"
        return 1
    fi

    local rules_dir="${GROK_HOME:-$HOME/.grok}/rules"
    local rule="$rules_dir/bearpaws.md"
    if [[ -e "$rule" || -L "$rule" ]] && ! grep -qF "$GROK_RULE_MARKER" "$rule" 2>/dev/null; then
        log_error "$rule exists and was not created by Bearpaws; leaving it untouched"
        return 1
    fi

    create_symlinks "$BEARPAWS_ROOT/skills" "$HOME/.agents/skills"

    mkdir -p "$rules_dir"
    local staged
    staged="$(mktemp "$rules_dir/.bearpaws.md.XXXXXX")"
    # Never leave the staged file behind in a directory Grok reads rules from
    if ! { printf '%s\n%s\n' "$GROK_RULE_MARKER" \
             'Before responding to any request, read `~/.agents/skills/using-bearpaws/SKILL.md` and follow it.' \
             > "$staged" && mv -f "$staged" "$rule"; }; then
        rm -f "$staged"
        log_error "Failed to write $rule"
        return 1
    fi
    log_success "Installed Grok bootstrap rule: $rule"
}

# Install the git gates in the current repository: a commit-msg hook (risk receipt) and a pre-push
# hook (commit identity check), each execing this checkout's script, so updating the checkout updates them.
GIT_HOOK_MARKER="# bearpaws-owned: written by install.sh --git. Delete this file to remove the gate."
install_git() {
    log_info "Setting up the git risk gate (commit-msg) and identity check (pre-push)..."
    local hooks_dir
    # --git-path follows core.hooksPath and shares hooks across worktrees, as git itself does
    # Git before 2.31 echoes the unknown --path-format flag back and exits 0, so require one absolute path
    if ! hooks_dir="$(git rev-parse --path-format=absolute --git-path hooks 2>/dev/null)" \
       || [[ "$hooks_dir" != /* || "$hooks_dir" == *$'\n'* ]]; then
        log_error "Not inside a git repository (or git is older than 2.31); run ./install.sh --git from the repository to gate"
        return 1
    fi
    local rc=0 pair name script hook gate staged q
    for pair in commit-msg:git-commit-msg pre-push:git-pre-push; do
        name="${pair%%:*}"; script="${pair#*:}"
        hook="$hooks_dir/$name"
        gate="$BEARPAWS_ROOT/hooks/$script"
        if [[ ! -f "$gate" ]]; then
            log_error "Gate script missing: hooks/$script"
            rc=1; continue
        fi
        if [[ -e "$hook" || -L "$hook" ]] && ! grep -qxF "$GIT_HOOK_MARKER" "$hook" 2>/dev/null; then
            log_error "$hook exists and was not created by Bearpaws; leaving it untouched"
            if [[ "$name" == commit-msg ]]; then
                log_info "To chain the gate, add this line to that hook: bash $(printf %q "$gate") \"\$1\" || exit 1"
            else
                log_info "To chain the gate, add this line to that hook: bash $(printf %q "$gate") \"\$@\" || exit 1 (it reads the refs on stdin)"
            fi
            rc=1; continue
        fi
        mkdir -p "$hooks_dir"
        staged="$(mktemp "$hooks_dir/.$name.XXXXXX")"
        q="$(printf %q "$gate")"
        if ! { printf '#!/usr/bin/env bash\n%s\n[ -f %s ] || { echo "bearpaws: git gate missing at "%s"; rerun install.sh --git, or bypass with --no-verify" >&2; exit 1; }\nexec bash %s "$@"\n' \
                   "$GIT_HOOK_MARKER" "$q" "$q" "$q" > "$staged" \
                 && chmod +x "$staged" && mv -f "$staged" "$hook"; }; then
            rm -f "$staged"
            log_error "Failed to write $hook"
            rc=1; continue
        fi
        log_success "Installed git $name gate: $hook"
    done
    return "$rc"
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
    # shellcheck disable=SC2064 # expand now: $staging is local and gone when the trap fires.
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
        log_success "Installed Bearpaws for Antigravity: $plugin_root"
    else
        log_error "Failed to move staged plugin to $plugin_root"
        [[ -n "$backup" ]] && mv "$backup" "$plugin_root"
        return 1
    fi
}

# Run a command with a timeout in seconds, portably across Linux, macOS, and Git Bash.
run_with_timeout() {
    local secs="$1"
    shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "$secs" "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$secs" "$@"
    elif command -v perl >/dev/null 2>&1; then
        perl -e '
            my ($s, @cmd) = @ARGV;
            my $pid = fork();
            exit 127 unless defined $pid;
            if ($pid == 0) {
                eval { setpgrp(0, 0) };
                exec @cmd or exit 127;
            }
            $SIG{ALRM} = sub { kill("TERM", -$pid); kill("TERM", $pid); exit 124; };
            alarm $s;
            waitpid($pid, 0);
            alarm 0;
            exit($? >> 8);
        ' "$secs" "$@"
    else
        "$@"
    fi
}

# Return 0 if semver $1 < $2 (major.minor.patch), 1 otherwise.
version_lt() {
    local a_maj a_min a_pat b_maj b_min b_pat
    IFS=. read -r a_maj a_min a_pat <<<"${1%%[^0-9.]*}"
    IFS=. read -r b_maj b_min b_pat <<<"${2%%[^0-9.]*}"
    a_maj=$((10#${a_maj:-0})); a_min=$((10#${a_min:-0})); a_pat=$((10#${a_pat:-0}))
    b_maj=$((10#${b_maj:-0})); b_min=$((10#${b_min:-0})); b_pat=$((10#${b_pat:-0}))
    if (( a_maj < b_maj )); then return 0; fi
    if (( a_maj > b_maj )); then return 1; fi
    if (( a_min < b_min )); then return 0; fi
    if (( a_min > b_min )); then return 1; fi
    if (( a_pat < b_pat )); then return 0; fi
    return 1
}

# Report whether an agent skills directory contains Bearpaws symlinks (read-only).
doctor_check_skill_links() {
    local label="$1" dir="$2"
    local roots_file="$dir/.bearpaws-roots"
    if [[ ! -d "$dir" ]]; then
        log_info "Agent skills ($label): no bearpaws links ($dir does not exist)"
        return 0
    fi
    local count=0 broken=0 entry target is_bp
    for entry in "$dir"/*; do
        [[ -L "$entry" ]] || continue
        target="$(readlink "$entry" 2>/dev/null || true)"
        target="${target%/}"
        is_bp=false
        if [[ -f "$roots_file" ]] && grep -qxF -- "${target%/*}" "$roots_file" 2>/dev/null; then
            is_bp=true
        elif [[ "$(basename "$entry")" == "using-bearpaws" && "$target" == */skills/using-bearpaws ]]; then
            is_bp=true
        fi
        if [[ "$is_bp" == "true" ]]; then
            if [[ -e "$entry" ]]; then
                ((++count))
            else
                ((++broken))
            fi
        fi
    done
    if (( count > 0 || broken > 0 )); then
        if (( broken > 0 )); then
            log_warning "Agent skills ($label): $count valid, $broken broken bearpaws link(s) in $dir"
        else
            log_success "Agent skills ($label): $count bearpaws link(s) in $dir"
        fi
    else
        log_info "Agent skills ($label): no bearpaws links in $dir"
    fi
}

# Read-only environment and installation diagnostic. Never edits anything.
# Exits 0 when enforcement can run, 1 when something blocks enforcement.
run_doctor() {
    local blocked=0

    # 1. jq presence and version (risk-gate is a no-op without jq)
    if command -v jq >/dev/null 2>&1; then
        local jq_ver
        jq_ver="$(jq --version 2>/dev/null || echo "unknown")"
        log_success "jq: $jq_ver ($(command -v jq))"
    else
        log_error "jq: not found on PATH (risk-gate is a no-op without jq)"
        blocked=1
    fi

    # 2. bash version
    log_info "bash: $BASH_VERSION"

    # 3. Claude Code version if claude is on PATH (short timeout; skip gracefully)
    if command -v claude >/dev/null 2>&1; then
        local claude_raw="" claude_ver=""
        if claude_raw="$(run_with_timeout 3 claude --version </dev/null 2>/dev/null)"; then
            claude_ver="$(printf '%s\n' "$claude_raw" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
        fi
        if [[ -n "$claude_ver" ]]; then
            if version_lt "$claude_ver" "2.1.163"; then
                log_error "Claude Code: $claude_ver (< 2.1.163 — risk-gate is a no-op on Claude Code < 2.1.163)"
                blocked=1
            else
                log_success "Claude Code: $claude_ver (>= 2.1.163)"
            fi
        else
            log_warning "Claude Code: on PATH at $(command -v claude), version check timed out or returned no version (skipped)"
        fi
    else
        log_info "Claude Code: claude not on PATH (skipped)"
    fi

    # 4. BEARPAWS_ENFORCE=0
    if [[ "${BEARPAWS_ENFORCE:-1}" == "0" ]]; then
        log_error "Enforcement: disabled (BEARPAWS_ENFORCE=0; risk-gate and git hooks are no-ops)"
        blocked=1
    else
        log_success "Enforcement: enabled (BEARPAWS_ENFORCE=${BEARPAWS_ENFORCE:-unset})"
    fi

    # 5. CLAUDE_PLUGIN_DATA (or TMPDIR fallback) writability without modifying disk
    local data_source data_root gate_dir check_dir
    if [[ -n "${CLAUDE_PLUGIN_DATA:-}" ]]; then
        data_source="CLAUDE_PLUGIN_DATA"
        data_root="$CLAUDE_PLUGIN_DATA"
    elif [[ -n "${TMPDIR:-}" ]]; then
        data_source="TMPDIR"
        data_root="$TMPDIR"
    else
        data_source="default /tmp"
        data_root="/tmp"
    fi
    [[ "$data_root" != "/" ]] && data_root="${data_root%/}"
    gate_dir="$data_root/risk-gate"

    local state_ok=true state_reason=""
    if [[ -L "$gate_dir" ]]; then
        state_ok=false
        state_reason="$gate_dir is a symlink (risk-gate refuses symlinked state dirs)"
    elif [[ -e "$gate_dir" ]]; then
        if [[ ! -d "$gate_dir" ]]; then
            state_ok=false
            state_reason="$gate_dir exists and is not a directory"
        elif [[ ! -w "$gate_dir" || ! -x "$gate_dir" ]]; then
            state_ok=false
            state_reason="$gate_dir is not writable"
        fi
    elif [[ -e "$data_root" ]]; then
        if [[ ! -d "$data_root" ]]; then
            state_ok=false
            state_reason="$data_root exists and is not a directory"
        elif [[ ! -w "$data_root" || ! -x "$data_root" ]]; then
            state_ok=false
            state_reason="$data_root is not writable"
        fi
    else
        check_dir="$data_root"
        while [[ ! -e "$check_dir" && "$check_dir" != "/" && "$check_dir" != "." ]]; do
            check_dir="$(dirname "$check_dir")"
        done
        if [[ ! -d "$check_dir" || ! -w "$check_dir" || ! -x "$check_dir" ]]; then
            state_ok=false
            state_reason="parent $check_dir for $data_root is not writable"
        fi
    fi

    if [[ "$state_ok" == "true" ]]; then
        log_success "State dir ($data_source): writable ($gate_dir)"
    else
        log_error "State dir ($data_source): not writable ($state_reason)"
        blocked=1
    fi

    # 6. Git commit-msg / pre-push hooks in the current repo (if in one)
    local hooks_dir=""
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1 || git rev-parse --git-dir >/dev/null 2>&1; then
        hooks_dir="$(git rev-parse --path-format=absolute --git-path hooks 2>/dev/null || true)"
        if [[ -z "$hooks_dir" || "$hooks_dir" == --path-format=* || "$hooks_dir" == *$'\n'* ]]; then
            hooks_dir="$(git rev-parse --git-path hooks 2>/dev/null || true)"
        fi
        if [[ -n "$hooks_dir" ]]; then
            local hook_name hook_path
            for hook_name in commit-msg pre-push; do
                hook_path="$hooks_dir/$hook_name"
                if [[ -f "$hook_path" && -x "$hook_path" ]] && grep -qxF "$GIT_HOOK_MARKER" "$hook_path" 2>/dev/null; then
                    log_success "Git hook ($hook_name): installed (bearpaws-owned at $hook_path)"
                elif [[ -e "$hook_path" || -L "$hook_path" ]]; then
                    log_warning "Git hook ($hook_name): present at $hook_path (not bearpaws-owned)"
                else
                    log_info "Git hook ($hook_name): missing at $hook_path (run ./install.sh --git to install)"
                fi
            done
        else
            log_info "Git hooks: unable to resolve hooks directory"
        fi
    else
        log_info "Git hooks: not inside a git repository (skipped)"
    fi

    # 7. Agent skill dirs and plugin/rule installations
    doctor_check_skill_links "agents" "$HOME/.agents/skills"
    doctor_check_skill_links "junie" "${JUNIE_HOME:-$HOME/.junie}/skills"

    local ag_dir="$HOME/.gemini/config/plugins/bearpaws"
    if [[ -f "$ag_dir/plugin.json" && -f "$ag_dir/skills/using-bearpaws/SKILL.md" ]]; then
        log_success "Antigravity plugin: installed at $ag_dir"
    elif [[ -d "$ag_dir" ]]; then
        log_warning "Antigravity plugin: partial directory at $ag_dir (missing plugin.json or using-bearpaws)"
    else
        log_info "Antigravity plugin: not installed ($ag_dir)"
    fi

    local grok_rule="${GROK_HOME:-$HOME/.grok}/rules/bearpaws.md"
    if [[ -f "$grok_rule" ]] && grep -qF "$GROK_RULE_MARKER" "$grok_rule" 2>/dev/null; then
        log_success "Grok bootstrap rule: installed at $grok_rule (bearpaws-owned)"
    elif [[ -e "$grok_rule" || -L "$grok_rule" ]]; then
        log_warning "Grok bootstrap rule: present at $grok_rule (not bearpaws-owned)"
    else
        log_info "Grok bootstrap rule: not installed ($grok_rule)"
    fi

    # 8. On Windows (Git Bash/MSYS), check whether bash is resolvable for run-hook.cmd
    case "$(uname -s 2>/dev/null || true)" in
        MINGW*|MSYS*|CYGWIN*)
            local win_bash="" pf64="/c/Program Files/Git/bin/bash.exe" pf86="/c/Program Files (x86)/Git/bin/bash.exe"
            if command -v cygpath >/dev/null 2>&1; then
                pf64="$(cygpath -u 'C:\Program Files\Git\bin\bash.exe' 2>/dev/null || printf '%s' "$pf64")"
                pf86="$(cygpath -u 'C:\Program Files (x86)\Git\bin\bash.exe' 2>/dev/null || printf '%s' "$pf86")"
            fi
            if [[ -x "$pf64" ]]; then
                win_bash="$pf64"
            elif [[ -x "$pf86" ]]; then
                win_bash="$pf86"
            elif command -v where.exe >/dev/null 2>&1 && where.exe bash >/dev/null 2>&1; then
                win_bash="$(where.exe bash 2>/dev/null | head -1 | tr -d '\r')"
            elif command -v bash >/dev/null 2>&1; then
                win_bash="$(command -v bash)"
            fi
            if [[ -n "$win_bash" ]]; then
                log_success "Windows run-hook.cmd bash: resolvable ($win_bash)"
            else
                log_error "Windows run-hook.cmd bash: not resolvable (install Git for Windows or put bash.exe on PATH)"
                blocked=1
            fi
            ;;
    esac

    echo ""
    if [[ $blocked -eq 0 ]]; then
        log_success "Doctor check passed: Bearpaws enforcement can run."
        return 0
    else
        log_error "Doctor check found issue(s) blocking Bearpaws enforcement."
        return 1
    fi
}

# Main installation
main() {
    local platforms=()
    local do_doctor=false
    
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
            --grok)
                platforms+=("grok")
                shift
                ;;
            --junie)
                platforms+=("junie")
                shift
                ;;
            --git)
                platforms+=("git")
                shift
                ;;
            --doctor)
                do_doctor=true
                shift
                ;;
            --global)
                export INSTALL_GLOBAL="true"
                shift
                ;;
            --help|-h)
                echo "Bearpaws installation script"
                echo ""
                echo "Usage: $0 --antigravity --global | --agents --global | --grok --global | --junie --global | --git | --doctor"
                echo ""
                echo "Options:"
                echo "  --antigravity Install Bearpaws plugin for Google Antigravity"
                echo "  --agents      Link skills into ~/.agents/skills (Codex, Devin, OpenCode, Cursor, Copilot, ...)"
                echo "  --grok        --agents plus a bootstrap rule in ~/.grok/rules/ for Grok Build"
                echo "  --junie       Link skills into ~/.junie/skills for JetBrains Junie (\$JUNIE_HOME honored)"
                echo "  --git         Risk-receipt commit-msg and identity-check pre-push hooks in the current git repository (bypass: --no-verify)"
                echo "  --doctor      Run read-only environment and installation diagnostics"
                echo "  --global      Required for --antigravity, --agents, --grok and --junie"
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
    
    if [[ "$do_doctor" == "true" ]]; then
        if [[ ${#platforms[@]} -gt 0 ]]; then
            log_error "--doctor cannot be combined with installation flags"
            exit 1
        fi
        set +e
        run_doctor
        local doc_rc=$?
        set -e
        exit "$doc_rc"
    fi

    if [[ ${#platforms[@]} -eq 0 ]]; then
        log_error "No platform given"
        echo "Use --help for usage information"
        exit 1
    fi
    
    log_info "Installing for platforms: ${platforms[*]}"
    
    local failed=0
    
    for platform in "${platforms[@]}"; do
        case $platform in
            antigravity|agents|grok|junie|git)
                # bash ignores set -e inside anything run as an if/&&/|| condition,
                # so run each installer as a plain subshell with errexit on: the
                # first failing step stops that installer and fails the install.
                set +e
                ( set -e; "install_$platform" )
                local status=$?
                set -e
                if [[ $status -ne 0 ]]; then
                    log_error "$platform installation failed"
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
            echo "  • Codex bootstrap: add this line to ~/.codex/AGENTS.md:"
            echo '      Before responding to any request, read `~/.agents/skills/using-bearpaws/SKILL.md` and follow it.'
            echo "  • Devin CLI: put the same line in your project's AGENTS.md"
        fi
        if [[ " ${platforms[*]} " =~ " grok " ]]; then
            echo "  • Grok Build (experimental): skills linked into ~/.agents/skills/; bootstrap rule in ${GROK_HOME:-~/.grok}/rules/bearpaws.md"
            echo "  • Run 'grok inspect' to confirm the rule and skills load"
        fi
        if [[ " ${platforms[*]} " =~ " junie " ]]; then
            local junie_home="${JUNIE_HOME:-~/.junie}"
            echo "  • Junie (experimental): skills linked into $junie_home/skills/"
            echo "  • Junie bootstrap: add this line to $junie_home/AGENTS.md:"
            echo "      Before responding to any request, read \`$junie_home/skills/using-bearpaws/SKILL.md\` and follow it."
        fi
        if [[ " ${platforms[*]} " =~ " git " ]]; then
            echo "  • Git: commits with staged changes now need a risk receipt in the message; pushes flag non-noreply commit emails once per remote, branch and commit set (bypass: --no-verify)"
        fi
    else
        log_error "$failed platform installations failed"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
