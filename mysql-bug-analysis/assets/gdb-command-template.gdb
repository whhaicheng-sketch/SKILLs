set pagination off
set confirm off
set print pretty on
set logging overwrite on
set logging enabled on
handle SIGPIPE nostop noprint pass
# Add bug-specific breakpoints and conditional commands below.
run
thread apply all bt full
info registers
set logging enabled off
quit
