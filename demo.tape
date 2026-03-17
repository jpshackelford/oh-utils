# OHC CLI Demo - OpenHands Cloud Admin Tools
# Demonstrates installation via uv and basic usage against OpenHands SaaS

Output demo.mp4
Set FontSize 16
Set Width 1000
Set Height 550
Set Theme "Dracula"
Set TypingSpeed 35ms
Set Padding 12
Set Shell "bash"

# @voice eleven:adam

# Setup: navigate to the directory and clear prompt
Hide
Type "export PS1='$ ' && export PROMPT_COMMAND='' && unset -f precmd preexec 2>/dev/null; clear"
Enter
Sleep 300ms
Type "cd /Users/jpshack/code/all-hands/oh-utils"
Enter
Sleep 500ms
Show

# @narrate:before "Welcome to the OHC CLI demo. This tool provides administrative access to OpenHands Cloud."
Type "echo '# OHC CLI - OpenHands Cloud Administration'"
Enter
Sleep 1s

# @narrate:before "First, let's install the CLI using uv tool install."
Type "uv tool uninstall oh-utils 2>/dev/null || true"
Enter
Sleep 1s
Type "uv tool install ./packages/ohc-cli --force"
Enter
Sleep 5s

# @narrate:before "Now let's verify the installation by checking the version."
Type "ohc --version"
Enter
Sleep 1500ms

# @narrate:before "The help command shows all available commands and options."
Type "ohc --help"
Enter
Sleep 3s

# @narrate:before "We can list our configured servers. I have SaaS and a local dev environment set up."
Type "ohc server list"
Enter
Sleep 2500ms

# @narrate:before "Let's list recent conversations from OpenHands SaaS."
Type "ohc --server SaaS conv list -n 5"
Enter
Sleep 3s

# @narrate:before "We can also get detailed information about any conversation."
Type "ohc --server SaaS conv show 1"
Enter
Sleep 3s

# @narrate:before "And that's the OHC CLI. Install it with uv tool install ohc-cli to get started."
Type "echo '✓ ohc-cli demo complete!'"
Enter
Sleep 2s
