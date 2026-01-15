# Claude Code Queue - Fish Shell Helper Functions and Completions
# Source this file in your ~/.config/fish/config.fish:
#   source /path/to/shell-helpers.fish

# Quick add a prompt to the queue
# Usage: cqa "your prompt here" [priority]
function cqa
    set -l prompt $argv[1]
    set -l priority (test (count $argv) -gt 1; and echo $argv[2]; or echo "0")

    if test -z "$prompt"
        echo "Usage: cqa \"prompt text\" [priority]"
        return 1
    end

    claude-queue add "$prompt" --priority $priority
end

# Quick add with current directory context
# Usage: cqahere "your prompt here" [priority]
function cqahere
    set -l prompt $argv[1]
    set -l priority (test (count $argv) -gt 1; and echo $argv[2]; or echo "0")

    if test -z "$prompt"
        echo "Usage: cqahere \"prompt text\" [priority]"
        return 1
    end

    claude-queue add "$prompt" --priority $priority --working-dir (pwd)
end

# Show queue status
# Usage: cqs [--detailed] [--json]
function cqs
    claude-queue status $argv
end

# Show detailed queue status
# Usage: cqsd
function cqsd
    claude-queue status --detailed
end

# Process next item in queue
# Usage: cqn [--verbose]
function cqn
    claude-queue next $argv
end

# Start the queue processor
# Usage: cqstart [--verbose]
function cqstart
    claude-queue start $argv
end

# List all prompts
# Usage: cql [--status STATUS] [--json]
function cql
    claude-queue list $argv
end

# List prompts by status
# Usage: cqlq (queued), cqlf (failed), cqlc (completed)
function cqlq
    claude-queue list --status queued
end

function cqlf
    claude-queue list --status failed
end

function cqlc
    claude-queue list --status completed
end

# Cancel a prompt
# Usage: cqcancel <prompt_id>
function cqcancel
    if test (count $argv) -eq 0
        echo "Usage: cqcancel <prompt_id>"
        return 1
    end
    claude-queue cancel $argv[1]
end

# Delete a prompt permanently
# Usage: cqdel <prompt_id>
function cqdel
    if test (count $argv) -eq 0
        echo "Usage: cqdel <prompt_id>"
        return 1
    end
    claude-queue delete $argv[1]
end

# Retry a failed prompt
# Usage: cqretry <prompt_id>
function cqretry
    if test (count $argv) -eq 0
        echo "Usage: cqretry <prompt_id>"
        return 1
    end
    claude-queue retry $argv[1]
end

# Get path to a prompt file
# Usage: cqpath <prompt_id>
function cqpath
    if test (count $argv) -eq 0
        echo "Usage: cqpath <prompt_id>"
        return 1
    end
    claude-queue path $argv[1]
end

# Edit a prompt file directly
# Usage: cqedit <prompt_id>
function cqedit
    if test (count $argv) -eq 0
        echo "Usage: cqedit <prompt_id>"
        return 1
    end
    set -l path (claude-queue path $argv[1])
    if test $status -eq 0 -a -n "$path"
        eval $EDITOR "$path"
    end
end

# Bank operations
# Usage: cqbank <command> [args...]
function cqbank
    claude-queue bank $argv
end

# Save template to bank
# Usage: cqbsave <template_name> [priority]
function cqbsave
    set -l template_name $argv[1]
    set -l priority (test (count $argv) -gt 1; and echo $argv[2]; or echo "0")

    if test -z "$template_name"
        echo "Usage: cqbsave <template_name> [priority]"
        return 1
    end

    claude-queue bank save $template_name --priority $priority
end

# List bank templates
# Usage: cqblist [--json]
function cqblist
    claude-queue bank list $argv
end

# Use a bank template
# Usage: cqbuse <template_name>
function cqbuse
    if test (count $argv) -eq 0
        echo "Usage: cqbuse <template_name>"
        return 1
    end
    claude-queue bank use $argv[1]
end

# Delete a bank template
# Usage: cqbdel <template_name>
function cqbdel
    if test (count $argv) -eq 0
        echo "Usage: cqbdel <template_name>"
        return 1
    end
    claude-queue bank delete $argv[1]
end

# Create a template
# Usage: cqtemplate <filename> [priority]
function cqtemplate
    set -l filename $argv[1]
    set -l priority (test (count $argv) -gt 1; and echo $argv[2]; or echo "0")

    if test -z "$filename"
        echo "Usage: cqtemplate <filename> [priority]"
        return 1
    end

    claude-queue template $filename --priority $priority
end

# Test Claude Code connection
# Usage: cqtest
function cqtest
    claude-queue test
end

# Show help for all cq* functions
# Usage: cqhelp
function cqhelp
    echo "Claude Code Queue - Shell Helper Functions

Quick Commands:
  cqa \"prompt\" [priority]        - Add prompt to queue
  cqahere \"prompt\" [priority]    - Add prompt with current directory
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
  cqbank <command> [args...]     - Bank operations

Bank Operations:
  cqbsave <name> [priority]      - Save template to bank
  cqblist [--json]               - List bank templates
  cqbuse <name>                  - Use a bank template
  cqbdel <name>                  - Delete a bank template

Other:
  cqtest                         - Test Claude Code connection
  cqhelp                         - Show this help message

For full documentation, run: claude-queue --help"
end

# Fish shell completions for claude-queue
complete -c claude-queue -f

# Global options
complete -c claude-queue -l storage-dir -d "Storage directory for queue data" -r
complete -c claude-queue -l claude-command -d "Claude Code CLI command" -r
complete -c claude-queue -l check-interval -d "Check interval in seconds" -r
complete -c claude-queue -l timeout -d "Command timeout in seconds" -r

# Commands
complete -c claude-queue -n "__fish_use_subcommand" -a start -d "Start the queue processor"
complete -c claude-queue -n "__fish_use_subcommand" -a next -d "Process only the next queue item and stop"
complete -c claude-queue -n "__fish_use_subcommand" -a add -d "Add a prompt to the queue"
complete -c claude-queue -n "__fish_use_subcommand" -a template -d "Create a prompt template file"
complete -c claude-queue -n "__fish_use_subcommand" -a status -d "Show queue status"
complete -c claude-queue -n "__fish_use_subcommand" -a cancel -d "Cancel a prompt"
complete -c claude-queue -n "__fish_use_subcommand" -a delete -d "Permanently delete a prompt"
complete -c claude-queue -n "__fish_use_subcommand" -a retry -d "Retry a failed prompt"
complete -c claude-queue -n "__fish_use_subcommand" -a path -d "Get the file path for a prompt"
complete -c claude-queue -n "__fish_use_subcommand" -a list -d "List prompts"
complete -c claude-queue -n "__fish_use_subcommand" -a test -d "Test Claude Code connection"
complete -c claude-queue -n "__fish_use_subcommand" -a bank -d "Manage prompt templates bank"

# start/next options
complete -c claude-queue -n "__fish_seen_subcommand_from start next" -s v -l verbose -d "Verbose output"

# add options
complete -c claude-queue -n "__fish_seen_subcommand_from add" -s p -l priority -d "Priority (lower = higher priority)" -r
complete -c claude-queue -n "__fish_seen_subcommand_from add" -s d -l working-dir -d "Working directory" -r -a "(__fish_complete_directories)"
complete -c claude-queue -n "__fish_seen_subcommand_from add" -s f -l context-files -d "Context files to include" -r -a "(__fish_complete_path)"
complete -c claude-queue -n "__fish_seen_subcommand_from add" -s r -l max-retries -d "Maximum retry attempts" -r
complete -c claude-queue -n "__fish_seen_subcommand_from add" -s t -l estimated-tokens -d "Estimated token usage" -r
complete -c claude-queue -n "__fish_seen_subcommand_from add" -l permission-mode -d "Permission mode" -r -a "acceptEdits bypassPermissions default delegate dontAsk plan"
complete -c claude-queue -n "__fish_seen_subcommand_from add" -l allowed-tools -d "Allowed tools" -r
complete -c claude-queue -n "__fish_seen_subcommand_from add" -l prompt-timeout -d "Timeout for this prompt" -r
complete -c claude-queue -n "__fish_seen_subcommand_from add" -s m -l model -d "Claude model to use" -r -a "sonnet opus haiku"

# template options
complete -c claude-queue -n "__fish_seen_subcommand_from template" -s p -l priority -d "Default priority" -r

# status options
complete -c claude-queue -n "__fish_seen_subcommand_from status" -l json -d "Output as JSON"
complete -c claude-queue -n "__fish_seen_subcommand_from status" -s d -l detailed -d "Show detailed prompt info"

# list options
complete -c claude-queue -n "__fish_seen_subcommand_from list" -l status -d "Filter by status" -r -a "queued executing completed failed cancelled rate_limited"
complete -c claude-queue -n "__fish_seen_subcommand_from list" -l json -d "Output as JSON"

# bank subcommands
complete -c claude-queue -n "__fish_seen_subcommand_from bank" -a "save list use delete" -f

# bank save options
complete -c claude-queue -n "__fish_seen_subcommand_from bank; and __fish_seen_subcommand_from save" -s p -l priority -d "Default priority" -r

# bank list options
complete -c claude-queue -n "__fish_seen_subcommand_from bank; and __fish_seen_subcommand_from list" -l json -d "Output as JSON"
