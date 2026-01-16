# Claude Code Queue - Bash/Zsh Helper Functions
# Source this file in your ~/.bashrc or ~/.zshrc:
#   source /path/to/shell-helpers.bash

# Quick add a prompt to the queue
# Usage: cqa "your prompt here" [priority]
cqa() {
    local prompt="$1"
    local priority="${2:-0}"

    if [ -z "$prompt" ]; then
        echo "Usage: cqa \"prompt text\" [priority]"
        return 1
    fi

    claude-queue add "$prompt" --priority "$priority"
}

# Quick add with current directory context
# Usage: cqahere "your prompt here" [priority]
cqahere() {
    local prompt="$1"
    local priority="${2:-0}"

    if [ -z "$prompt" ]; then
        echo "Usage: cqahere \"prompt text\" [priority]"
        return 1
    fi

    claude-queue add "$prompt" --priority "$priority" --working-dir "$(pwd)"
}

# Show queue status
# Usage: cqs [--detailed] [--json]
cqs() {
    claude-queue status "$@"
}

# Show detailed queue status
# Usage: cqsd
cqsd() {
    claude-queue status --detailed
}

# Process next item in queue
# Usage: cqn [--verbose]
cqn() {
    claude-queue next "$@"
}

# Start the queue processor
# Usage: cqstart [--verbose]
cqstart() {
    claude-queue start "$@"
}

# List all prompts
# Usage: cql [--status STATUS] [--json]
cql() {
    claude-queue list "$@"
}

# List prompts by status
# Usage: cqlq (queued), cqlf (failed), cqlc (completed)
cqlq() {
    claude-queue list --status queued
}

cqlf() {
    claude-queue list --status failed
}

cqlc() {
    claude-queue list --status completed
}

# Cancel a prompt
# Usage: cqcancel <prompt_id>
cqcancel() {
    if [ -z "$1" ]; then
        echo "Usage: cqcancel <prompt_id>"
        return 1
    fi
    claude-queue cancel "$1"
}

# Delete a prompt permanently
# Usage: cqdel <prompt_id>
cqdel() {
    if [ -z "$1" ]; then
        echo "Usage: cqdel <prompt_id>"
        return 1
    fi
    claude-queue delete "$1"
}

# Retry a failed prompt
# Usage: cqretry <prompt_id>
cqretry() {
    if [ -z "$1" ]; then
        echo "Usage: cqretry <prompt_id>"
        return 1
    fi
    claude-queue retry "$1"
}

# Get path to a prompt file
# Usage: cqpath <prompt_id>
cqpath() {
    if [ -z "$1" ]; then
        echo "Usage: cqpath <prompt_id>"
        return 1
    fi
    claude-queue path "$1"
}

# Edit a prompt file directly
# Usage: cqedit <prompt_id>
cqedit() {
    if [ -z "$1" ]; then
        echo "Usage: cqedit <prompt_id>"
        return 1
    fi
    local path
    path=$(claude-queue path "$1")
    if [ $? -eq 0 ] && [ -n "$path" ]; then
        ${EDITOR:-vim} "$path"
    fi
}

# Create a template
# Usage: cqtemplate <filename> [priority]
cqtemplate() {
    local filename="$1"
    local priority="${2:-0}"

    if [ -z "$filename" ]; then
        echo "Usage: cqtemplate <filename> [priority]"
        return 1
    fi

    claude-queue template "$filename" --priority "$priority"
}

# Test Claude Code connection
# Usage: cqtest
cqtest() {
    claude-queue test
}

# Show help for all cq* functions
# Usage: cqhelp
cqhelp() {
    cat <<'EOF'
Claude Code Queue - Shell Helper Functions

Quick Commands:
  cqa "prompt" [priority]        - Add prompt to queue
  cqahere "prompt" [priority]    - Add prompt with current directory
  cqs [--detailed] [--json]      - Show queue status
  cqsd                           - Show detailed queue status
  cqn [--verbose]                - Process next item
  cqstart [--verbose]            - Start queue processor
  cql [--status] [--json]        - List all prompts
  cqlq                           - List queued prompts
  cqlf                           - List failed prompts
  cqlc                           - List completed prompts

Prompt Management:
  cqcancel <id>                  - Cancel a prompt
  cqdel <id>                     - Delete a prompt permanently
  cqretry <id>                   - Retry a failed prompt
  cqpath <id>                    - Get path to prompt file
  cqedit <id>                    - Edit prompt file

Template Management:
  cqtemplate <name> [priority]   - Create a template

Other:
  cqtest                         - Test Claude Code connection
  cqhelp                         - Show this help message

For full documentation, run: claude-queue --help
EOF
}

# Bash/Zsh completion for claude-queue
if [ -n "$BASH_VERSION" ]; then
    # Bash completion
    _claude_queue_completion() {
        local cur prev commands
        cur="${COMP_WORDS[COMP_CWORD]}"
        prev="${COMP_WORDS[COMP_CWORD-1]}"
        commands="start next add template status cancel delete retry path list test"

        case "${prev}" in
            claude-queue)
                COMPREPLY=($(compgen -W "${commands}" -- "${cur}"))
                return 0
                ;;
            --status)
                COMPREPLY=($(compgen -W "queued executing completed failed cancelled" -- "${cur}"))
                return 0
                ;;
            --permission-mode)
                COMPREPLY=($(compgen -W "acceptEdits bypassPermissions default delegate dontAsk plan" -- "${cur}"))
                return 0
                ;;
            --model|-m)
                COMPREPLY=($(compgen -W "sonnet opus haiku" -- "${cur}"))
                return 0
                ;;
        esac
    }

    complete -F _claude_queue_completion claude-queue
elif [ -n "$ZSH_VERSION" ]; then
    # Zsh completion
    _claude_queue_completion() {
        local -a commands
        commands=(
            'start:Start the queue processor'
            'next:Process only the next queue item and stop'
            'add:Add a prompt to the queue'
            'template:Create a prompt template file'
            'status:Show queue status'
            'cancel:Cancel a prompt'
            'delete:Permanently delete a prompt from storage'
            'retry:Retry a failed prompt'
            'path:Get the file path for a prompt'
            'list:List prompts'
            'test:Test Claude Code connection'
        )

        _describe 'command' commands
    }

    compdef _claude_queue_completion claude-queue
fi
