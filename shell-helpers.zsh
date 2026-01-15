# Claude Code Queue - Zsh Helper Functions and Completions
# Source this file in your ~/.zshrc:
#   source /path/to/shell-helpers.zsh

# Source the bash-compatible functions
SCRIPT_DIR="${0:A:h}"
if [[ -f "${SCRIPT_DIR}/shell-helpers.bash" ]]; then
    source "${SCRIPT_DIR}/shell-helpers.bash"
fi

# Zsh-specific advanced completion
#compdef claude-queue

_claude_queue() {
    local -a commands
    local state line

    _arguments -C \
        '--storage-dir[Storage directory for queue data]:directory:_directories' \
        '--claude-command[Claude Code CLI command]:command:_command_names' \
        '--check-interval[Check interval in seconds]:seconds:' \
        '--timeout[Command timeout in seconds]:seconds:' \
        '1: :->command' \
        '*:: :->args'

    case $state in
        command)
            local -a subcommands
            subcommands=(
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
                'bank:Manage prompt templates bank'
            )
            _describe 'command' subcommands
            ;;
        args)
            case $line[1] in
                start|next)
                    _arguments \
                        '(-v --verbose)'{-v,--verbose}'[Verbose output]'
                    ;;
                add)
                    _arguments \
                        '1:prompt text:' \
                        '(-p --priority)'{-p,--priority}'[Priority (lower = higher priority)]:priority:' \
                        '(-d --working-dir)'{-d,--working-dir}'[Working directory]:directory:_directories' \
                        '(-f --context-files)'{-f,--context-files}'[Context files to include]:files:_files' \
                        '(-r --max-retries)'{-r,--max-retries}'[Maximum retry attempts]:retries:' \
                        '(-t --estimated-tokens)'{-t,--estimated-tokens}'[Estimated token usage]:tokens:' \
                        '--permission-mode[Permission mode]:mode:(acceptEdits bypassPermissions default delegate dontAsk plan)' \
                        '--allowed-tools[Allowed tools]:tools:' \
                        '--prompt-timeout[Timeout for this prompt]:seconds:' \
                        '(-m --model)'{-m,--model}'[Claude model to use]:model:(sonnet opus haiku)'
                    ;;
                template)
                    _arguments \
                        '1:filename:' \
                        '(-p --priority)'{-p,--priority}'[Default priority]:priority:'
                    ;;
                status)
                    _arguments \
                        '--json[Output as JSON]' \
                        '(-d --detailed)'{-d,--detailed}'[Show detailed prompt info]'
                    ;;
                cancel|delete|retry|path)
                    _arguments \
                        '1:prompt ID:'
                    ;;
                list)
                    _arguments \
                        '--status[Filter by status]:status:(queued executing completed failed cancelled)' \
                        '--json[Output as JSON]'
                    ;;
                bank)
                    local -a bank_commands
                    bank_commands=(
                        'save:Save a template to bank'
                        'list:List templates in bank'
                        'use:Use template from bank'
                        'delete:Delete template from bank'
                    )
                    _describe 'bank command' bank_commands
                    ;;
            esac
            ;;
    esac
}

compdef _claude_queue claude-queue

# Zsh-specific widget for quick prompt adding
# Bind to Ctrl-Q by adding to .zshrc: bindkey '^Q' _cq_quick_add
_cq_quick_add() {
    local prompt
    vared -p "Quick add prompt: " prompt
    if [[ -n "$prompt" ]]; then
        BUFFER="cqa \"$prompt\""
        zle accept-line
    fi
}
zle -N _cq_quick_add

# Optional: Auto-bind Ctrl-Q for quick prompt adding
# Uncomment the following line in your .zshrc to enable:
# bindkey '^Q' _cq_quick_add
