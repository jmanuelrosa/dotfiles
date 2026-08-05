function port --description "List listening ports, or show which process is using a given port"
  argparse -n port h/help u/udp -- $argv
  or return 1

  if set -q _flag_help
    _port_usage
    return 0
  end

  if test (count $argv) -gt 1
    _port_usage
    return 1
  end

  if not command -q lsof
    _ui err "port needs lsof, which ships with macOS."
    return 1
  end

  if test (count $argv) -eq 1
    _port_lookup $argv[1]
    return $status
  end

  _port_listing (set -q _flag_udp; and echo 1)
end

# A specific port: every TCP socket touching it (LISTEN and ESTABLISHED alike, since
# "who's using it" covers a client holding it open as much as a server bound to it) plus
# any UDP socket bound to it. Two lsof calls rather than one -i:<port> pass, because only
# TCP carries a state to parse and mixing the two in one -F stream loses which is which.
function _port_lookup --argument-names target
  set -l tcp_rows (command lsof -nP -iTCP:$target -F pcTn 2>/dev/null)
  set -l udp_rows (command lsof -nP -iUDP:$target -F pcn 2>/dev/null)

  set -l pid ""
  set -l cmd ""
  set -l addr ""
  set -l count 0

  for line in $tcp_rows
    set -l tag (string sub -l 1 -- $line)
    set -l value (string sub -s 2 -- $line)
    switch $tag
      case p
        set pid $value
      case c
        set cmd $value
      case n
        set addr $value
      case T
        string match -q 'ST=*' -- $value; or continue
        set -l state (string replace 'ST=' '' -- $value)
        if test $count -eq 0
          _ui title "🔎 Port $target:"
        end
        set count (math $count + 1)
        _port_row $cmd $pid $addr $state
    end
  end

  for line in $udp_rows
    set -l tag (string sub -l 1 -- $line)
    set -l value (string sub -s 2 -- $line)
    switch $tag
      case p
        set pid $value
      case c
        set cmd $value
      case n
        if test $count -eq 0
          _ui title "🔎 Port $target:"
        end
        set count (math $count + 1)
        _port_row $cmd $pid $value UDP
    end
  end

  if test $count -eq 0
    _ui title "🤷 Nothing is using port $target."
    return 1
  end

  set -l label record
  test $count -ne 1; and set label records
  _ui done "$count $label using port $target."
end

# No port given: the servers, i.e. TCP sockets in LISTEN. UDP has no such state, so
# --udp lists every UDP socket with a real local port instead, skipping the "*:*"
# sockets that are not bound to anything a caller could mean by "which port".
function _port_listing --argument-names show_udp
  set -l tcp_rows (command lsof -nP -iTCP -sTCP:LISTEN -F pcn 2>/dev/null)

  set -l pid ""
  set -l cmd ""
  set -l ports
  set -l cmds
  set -l pids
  set -l addrs
  set -l protos

  for line in $tcp_rows
    set -l tag (string sub -l 1 -- $line)
    set -l value (string sub -s 2 -- $line)
    switch $tag
      case p
        set pid $value
      case c
        set cmd $value
      case n
        set -a ports (_port_number $value)
        set -a cmds $cmd
        set -a pids $pid
        set -a addrs $value
        set -a protos TCP
    end
  end

  if test -n "$show_udp"
    set pid ""
    set cmd ""
    for line in (command lsof -nP -iUDP -F pcn 2>/dev/null)
      set -l tag (string sub -l 1 -- $line)
      set -l value (string sub -s 2 -- $line)
      switch $tag
        case p
          set pid $value
        case c
          set cmd $value
        case n
          # Skip wildcard-port sockets ("*:*", nothing a caller could mean by "which
          # port") and connected ones ("local->remote", an outbound conversation on an
          # ephemeral port rather than a bound service).
          string match -q '*:\*' -- $value; and continue
          string match -q '*->*' -- $value; and continue
          set -a ports (_port_number $value)
          set -a cmds $cmd
          set -a pids $pid
          set -a addrs $value
          set -a protos UDP
      end
    end
  end

  if test (count $ports) -eq 0
    _ui title "🤷 No listening ports found."
    return 0
  end

  _ui title "🔎 Listening ports:"
  for i in (_port_sort_indices $ports)
    _port_row $cmds[$i] $pids[$i] $addrs[$i] $protos[$i]
  end

  set -l label listener
  test (count $ports) -ne 1; and set label listeners
  _ui done (count $ports)" $label."
end

function _port_row --argument-names cmd pid addr state
  set -l port (_port_number $addr)
  _ui item (_ui paint cyan "$port")"  "(_ui paint dim "$state")"  $cmd (pid $pid)  "(_ui paint dim "$addr")
end

# The NAME field is "addr:port" or "local:port->remote:port"; the port a caller means
# is always the local one, so take everything before "->" first, then split on the last
# colon (never the first, or an IPv6 "[::1]:5000" would split on the wrong one).
function _port_number --argument-names name
  set -l local (string split -m1 -- '->' $name)[1]
  string split -r -m1 -- ':' $local | tail -1
end

function _port_sort_indices
  set -l ports $argv
  set -l pairs
  for i in (seq (count $ports))
    set -a pairs "$ports[$i] $i"
  end
  for line in (printf '%s\n' $pairs | command sort -n -k1,1)
    echo (string split ' ' -- $line)[2]
  end
end
