{ inputs, ... }:
{
  perSystem = { config, pkgs, ... }:
    let
      # Mock claude command that creates files test01, test02, etc. with the prompt text
      mockClaude = pkgs.writeShellScriptBin "claude" ''
        # Handle --version and --help flags
        for arg in "$@"; do
          case "$arg" in
            --version) echo "mock-claude 1.0.0"; exit 0 ;;
            --help) echo "Mock claude for testing"; exit 0 ;;
          esac
        done

        # Get the last argument (the prompt text)
        PROMPT="''${@: -1}"

        # Counter file in home directory
        COUNTER_FILE="$HOME/.mock-claude-counter"
        if [ -f "$COUNTER_FILE" ]; then
          COUNT=$(cat "$COUNTER_FILE")
        else
          COUNT=0
        fi
        COUNT=$((COUNT + 1))
        echo "$COUNT" > "$COUNTER_FILE"

        # Create test file with 2-digit number
        FILENAME=$(printf "test%02d" "$COUNT")
        echo "$PROMPT" > "$FILENAME"
        echo "Mock claude executed successfully, created $FILENAME"
      '';

      # Initialize a git/jj repository for testing
      initTestRepo = pkgs.writeShellScriptBin "init-test-repo" ''
        set -e
        REPO_PATH="''${1:-$HOME/test-repo}"
        mkdir -p "$REPO_PATH"
        cd "$REPO_PATH"
        git init
        git config user.email "test@test.com"
        git config user.name "Test User"
        echo test > README.md
        git add README.md
        git commit -m "Initial commit"
        jj git init --colocate
        echo "Test repository initialized at $REPO_PATH"
      '';

      claude-code-queue = config.packages.claude-code-queue;
    in
    {
      checks.nixos-test = pkgs.testers.nixosTest {
        name = "claude-code-queue-test";

        nodes.machine = { config, pkgs, ... }: {
          environment.systemPackages = [
            claude-code-queue
            mockClaude
            initTestRepo
            pkgs.git
            pkgs.jujutsu
          ];

          # Create test user
          users.users.testuser = {
            isNormalUser = true;
            home = "/home/testuser";
          };
        };

        testScript = ''
          machine.start()
          machine.wait_for_unit("multi-user.target")

          # Initialize the test repository
          machine.succeed("su - testuser -c 'init-test-repo /home/testuser/test-repo'")

          # Add prompts to the queue
          machine.succeed("su - testuser -c 'cd /home/testuser/test-repo && claude-queue add \"first test prompt\"'")
          machine.succeed("su - testuser -c 'cd /home/testuser/test-repo && claude-queue add \"second test prompt\"'")

          # Verify the prompt was added by checking the queue
          machine.succeed("su - testuser -c 'claude-queue list | grep -q \"first test prompt\"'")
          machine.succeed("su - testuser -c 'claude-queue list | grep -q \"second test prompt\"'")

          # Run the next prompt in the queue
          machine.succeed("su - testuser -c 'cd /home/testuser/test-repo && claude-queue next'")

          # Verify test01 was created with the prompt content
          machine.succeed("test -f /home/testuser/test-repo/test01")
          machine.succeed("grep -q 'first test prompt' /home/testuser/test-repo/test01")
          # Verify test02 was not created yet
          machine.succeed("test ! -f /home/testuser/test-repo/test02")

          # Print success message
          print("SUCCESS: The mock claude command created 'test01' with the prompt content!")
        '';
      };
    };
}
