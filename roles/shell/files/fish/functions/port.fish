function port --description "List listening ports, or show which process is using a given port"
  argparse -n port h/help u/udp l/long k/kill -- $argv
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

  if set -q _flag_kill
    if test (count $argv) -ne 1
      _ui err "--kill needs a port: port 3000 --kill"
      return 1
    end
    _port_kill $argv[1]
    return $status
  end

  # Assigned before the call rather than substituted into it: an unset flag yields an
  # empty *list*, which vanishes from the argument list rather than arriving as "", so
  # `port --long` handed _port_listing a single "1" and it landed on show_udp.
  set -l want_long ""
  set -q _flag_long; and set want_long 1

  if test (count $argv) -eq 1
    _port_lookup $argv[1] "$want_long"
    return $status
  end

  set -l want_udp ""
  set -q _flag_udp; and set want_udp 1

  _port_listing "$want_udp" "$want_long"
end

# A specific port: every TCP socket touching it (LISTEN and ESTABLISHED alike, since
# "who's using it" covers a client holding it open as much as a server bound to it) plus
# any UDP socket bound to it. Two lsof calls rather than one -i:<port> pass, because only
# TCP carries a state to parse and mixing the two in one -F stream loses which is which.
function _port_lookup --argument-names target long
  set -l tcp_rows (command lsof -nP +c 0 -iTCP:$target -F pcTn 2>/dev/null)
  set -l udp_rows (command lsof -nP +c 0 -iUDP:$target -F pcn 2>/dev/null)

  set -l pid ""
  set -l cmd ""
  set -l cmds
  set -l pids
  set -l addrs
  set -l states

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
        set -a cmds $cmd
        set -a pids $pid
        set -a addrs $addr
        set -a states (string replace 'ST=' '' -- $value)
    end
  end

  set pid ""
  set cmd ""
  for line in $udp_rows
    set -l tag (string sub -l 1 -- $line)
    set -l value (string sub -s 2 -- $line)
    switch $tag
      case p
        set pid $value
      case c
        set cmd $value
      case n
        set -a cmds $cmd
        set -a pids $pid
        set -a addrs $value
        set -a states UDP
    end
  end

  set -l count (count $cmds)
  if test $count -eq 0
    _ui title "🤷 Nothing is using port $target."
    return 1
  end

  set -l detail
  test -n "$long"; and set detail (_port_detail_fetch $pids)

  _ui title "🔎 Port $target:"
  set -l shown
  for i in (seq $count)
    # A scope badge answers "who can reach this", which only a bound socket has: an
    # ESTABLISHED row is one end of a conversation, and its local address says nothing
    # about reachability. So the badge rides on LISTEN and UDP rows and nothing else.
    set -l scope ""
    contains -- $states[$i] LISTEN UDP; and set scope (_port_scope (_port_host $addrs[$i]))
    _port_row (_port_number $addrs[$i]) $cmds[$i] $pids[$i] $addrs[$i] $states[$i] "$scope" (_port_detail_field $pids[$i] age $detail)
    # Once per pid here too: a dual-stack server is two rows and a busy one is a row per
    # connection, and the same cwd under each of them is the noise, not the information.
    if test -n "$long"; and not contains -- $pids[$i] $shown
      set -a shown $pids[$i]
      _port_notes $pids[$i] "$cmds[$i]" $target 1 $detail
    end
  end

  set -l label record
  test $count -ne 1; and set label records
  _ui done "$count $label using port $target."
end

# No port given: the servers, i.e. TCP sockets in LISTEN. UDP has no such state, so
# --udp lists every UDP socket with a real local port instead, skipping the "*:*"
# sockets that are not bound to anything a caller could mean by "which port".
function _port_listing --argument-names show_udp long
  set -l tcp_rows (command lsof -nP +c 0 -iTCP -sTCP:LISTEN -F pcn 2>/dev/null)

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
    for line in (command lsof -nP +c 0 -iUDP -F pcn 2>/dev/null)
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

  # One server bound on both address families is one listener, not two: the rows differ
  # only in the bind host, and printing "8788" twice invites the reader to go looking for
  # a conflict that is not there. Chrome's eight identical *:5353 sockets collapse here too.
  set -l keys
  set -l m_ports
  set -l m_cmds
  set -l m_pids
  set -l m_hosts
  set -l m_protos
  for i in (seq (count $ports))
    set -l host (_port_host $addrs[$i])
    set -l at (contains -i -- "$pids[$i]|$ports[$i]|$protos[$i]" $keys)
    if test -n "$at"
      contains -- $host (string split ', ' -- $m_hosts[$at]); or set m_hosts[$at] "$m_hosts[$at], $host"
      continue
    end
    set -a keys "$pids[$i]|$ports[$i]|$protos[$i]"
    set -a m_ports $ports[$i]
    set -a m_cmds $cmds[$i]
    set -a m_pids $pids[$i]
    set -a m_hosts $host
    set -a m_protos $protos[$i]
  end

  set -l detail
  set -l conn_ports
  set -l conn_counts
  if test -n "$long"
    set detail (_port_detail_fetch $m_pids)
    for pair in (_port_conn_tally)
      set -l parts (string split -m1 ' ' -- $pair)
      set -a conn_ports $parts[1]
      set -a conn_counts $parts[2]
    end
  end

  _ui title "🔎 Listening ports:"
  set -l shown
  for i in (_port_sort_indices $m_ports)
    set -l suffix (_port_detail_field $m_pids[$i] age $detail)
    if test -n "$long"
      set -l at (contains -i -- $m_ports[$i] $conn_ports)
      if test -n "$at"
        set -l label connected
        test "$conn_counts[$at]" = 1; and set label connection
        set suffix (string join '  ·  ' -- $suffix "$conn_counts[$at] $label" | string trim -l -c ' ·')
      end
    end
    _port_row $m_ports[$i] $m_cmds[$i] $m_pids[$i] $m_hosts[$i] $m_protos[$i] (_port_scope (string split ', ' -- $m_hosts[$i])) "$suffix"
    # A process holding three ports would otherwise repeat one identical cwd three times,
    # and the pid on every row is what lets a reader tie the later ones back to it.
    if test -n "$long"; and not contains -- $m_pids[$i] $shown
      set -a shown $m_pids[$i]
      _port_notes $m_pids[$i] "$m_cmds[$i]" $m_ports[$i] "" $detail
    end
  end

  set -l label listener
  test (count $m_ports) -ne 1; and set label listeners
  _ui done (count $m_ports)" $label."
end

# Free a port: signal what is *bound* to it, never a client that merely connected. A
# caller reaching for --kill wants the port back, and killing the browser that happened
# to open a tab against it would be the wrong process every time.
function _port_kill --argument-names target
  set -l pids
  set -l cmds
  set -l pid ""
  for line in (command lsof -nP +c 0 -iTCP:$target -sTCP:LISTEN -F pc 2>/dev/null) \
              (command lsof -nP +c 0 -iUDP:$target -F pc 2>/dev/null)
    set -l value (string sub -s 2 -- $line)
    switch (string sub -l 1 -- $line)
      case p
        set pid $value
      case c
        contains -- $pid $pids; and continue
        set -a pids $pid
        set -a cmds $value
    end
  end

  if test (count $pids) -eq 0
    _ui title "🤷 Nothing is bound to port $target."
    return 1
  end

  set -l detail (_port_detail_fetch $pids)

  _ui title "🔫 Port $target is held by:"
  for i in (seq (count $pids))
    _ui item (_ui paint cyan "$cmds[$i]")" (pid $pids[$i])"
    set -l args (_port_detail_field $pids[$i] args $detail)
    test -n "$args"; and _ui -i 6 note (_port_trim "$args")
  end

  read -l -P "  Send SIGTERM to "(count $pids)"? [y/N] " reply
  if not string match -qi 'y' -- "$reply"
    _ui done "Left alone."
    return 1
  end

  set -l killed 0
  for pid in $pids
    if command kill $pid 2>/dev/null
      set killed (math $killed + 1)
    else
      _ui warn "Could not signal pid $pid."
    end
  end

  set -l survivors (command lsof -nP -iTCP:$target -sTCP:LISTEN -t 2>/dev/null)
  set -a survivors (command lsof -nP -iUDP:$target -t 2>/dev/null)
  set survivors (printf '%s\n' $survivors | command sort -un)

  if test (count $survivors) -gt 0
    # Escalating on the caller's behalf is how a database gets a SIGKILL it was going
    # to survive TERM anyway, so hand over the command rather than running it.
    _ui warn "Still bound after SIGTERM: "(string join ' ' -- $survivors)
    _ui note "kill -9 "(string join ' ' -- $survivors)
    return 1
  end

  _ui done "Freed port $target ($killed signalled)."
end

# The port is passed rather than derived: the listing hands over a bare bind host, since
# repeating the port inside the address column costs width and says nothing new.
function _port_row --argument-names port cmd pid addr state scope suffix
  set -l line (_ui paint cyan "$port")"  "(_ui paint dim "$state")
  # An exposed listener is reachable from the LAN, which is the only security-relevant
  # fact on the row, so it is the one badge that is not dim.
  if test -n "$scope"
    if test "$scope" = exposed
      set line "$line  "(_ui paint yellow exposed)
    else
      set line "$line  "(_ui paint dim local)
    end
  end
  set line "$line  $cmd (pid $pid)  "(_ui paint dim "$addr")
  test -n "$suffix"; and set line "$line  "(_ui paint dim "$suffix")
  _ui item "$line"
end

# Loopback and nothing else is local; a wildcard bind and a specific LAN address are
# both reachable from the network, so both read as exposed. Takes every host a merged row
# was bound on, and one exposed host makes the whole row exposed.
function _port_scope
  for host in $argv
    switch $host
      case '127.*' '[::1]' localhost '[::ffff:127.*'
        continue
      case '*'
        echo exposed
        return 0
    end
  end
  echo local
end

# The bind host alone, since the port it is paired with already leads the row. "*:5353"
# is "*", "[::1]:8788" is "[::1]": split on the last colon, never the first.
function _port_host --argument-names addr
  set -l local (string split -m1 -- '->' $addr)[1]
  echo (string split -r -m1 -- ':' $local)[1]
end

# One ps call and one lsof call for every pid on the listing, rather than two per row:
# a machine with thirty listeners would otherwise pay sixty subprocess spawns to print
# one screen. Encoded as "<pid> <field> <value>" lines because fish has no map.
function _port_detail_fetch
  set -l pids (printf '%s\n' $argv | command sort -un)
  test (count $pids) -eq 0; and return 0
  set -l csv (string join ',' -- $pids)

  for line in (command ps -o pid=,etime=,args= -p $csv 2>/dev/null)
    set -l parts (string match -r '^\s*(\d+)\s+(\S+)\s+(.*)$' -- $line)
    test (count $parts) -eq 4; or continue
    # An etime shape _port_age does not model yields nothing, and "up" on its own reads
    # as a fact rather than as the missing measurement it is.
    set -l age (_port_age $parts[3])
    test -n "$age"; and echo "$parts[2] age up $age"
    echo "$parts[2] args $parts[4]"
  end

  set -l pid ""
  for line in (command lsof -a -d cwd -F pn -p $csv 2>/dev/null)
    set -l tag (string sub -l 1 -- $line)
    set -l value (string sub -s 2 -- $line)
    switch $tag
      case p
        set pid $value
      case n
        # A daemon's cwd is "/", which is true and tells the reader nothing. Twenty of
        # those under a long listing is the noise that teaches people to stop reading it.
        test "$value" = /; and continue
        echo "$pid cwd $value"
    end
  end
end

# The rows arrive as a trailing *list*, never as one quoted blob: a command substitution
# yields a list, quoting it joins every row with a space, and `string split -m2` then
# read the whole table as a single record whose third field was all the others. That
# printed one pid's entire detail on its row and silently dropped every other pid's.
function _port_detail_field
  set -l pid $argv[1]
  set -l field $argv[2]
  for line in $argv[3..-1]
    set -l parts (string split -m2 ' ' -- $line)
    test (count $parts) -eq 3; or continue
    test "$parts[1]" = "$pid" -a "$parts[2]" = "$field"; or continue
    echo $parts[3]
    return 0
  end
end

# want_args is off for the listing and on for a single-port lookup. An Electron helper's
# command line runs past 400 characters and says nothing a reader scanning twenty ports
# wants; once they have narrowed to one port, it is the whole reason they narrowed.
function _port_notes
  set -l pid $argv[1]
  set -l cmd $argv[2]
  set -l port $argv[3]
  set -l want_args $argv[4]
  set -l rows $argv[5..-1]

  set -l cwd (_port_detail_field $pid cwd $rows)
  test -n "$cwd"; and _ui -i 6 note (_ui path "$cwd")

  if test -n "$want_args"
    set -l args (_port_detail_field $pid args $rows)
    test -n "$args"; and _ui -i 6 note (_port_trim "$args")
  end

  # A docker-published port lists the proxy, never the container, so the row alone says
  # nothing useful. Only consulted for those rows: the daemon call is slow enough that
  # paying it for every listener would be felt.
  string match -q 'com.docker*' -- $cmd; or return 0
  set -l container (_port_container $port)
  test -n "$container"; and _ui -i 6 note "container: $container"
end

function _port_container --argument-names port
  command -q docker; or return 0
  for line in (command docker ps --format '{{.Names}}\t{{.Ports}}' 2>/dev/null)
    set -l parts (string split -m1 \t -- $line)
    test (count $parts) -eq 2; or continue
    # Published ports read "0.0.0.0:5432->5432/tcp, :::5432->5432/tcp"; the host port is
    # the one before the arrow, and it is the only one a caller could have looked up.
    # -g so the capture arrives alone: without it every match is followed by its own
    # group and half the list is ":5432->" rather than a port.
    for hit in (string match -rag ':(\d+)->' -- $parts[2])
      test "$hit" = "$port"; or continue
      echo $parts[1]
      return 0
    end
  end
end

# Every ESTABLISHED socket on the machine in one call, tallied by local port. An inbound
# connection to 8788 is "127.0.0.1:8788->127.0.0.1:53042" and the loopback client's own
# view of it carries local port 53042, so the pair counts once rather than twice.
function _port_conn_tally
  set -l ports
  for line in (command lsof -nP -iTCP -sTCP:ESTABLISHED -F n 2>/dev/null)
    string match -q 'n*' -- $line; or continue
    set -l name (string sub -s 2 -- $line)
    string match -q '*->*' -- $name; or continue
    set -a ports (_port_number $name)
  end
  test (count $ports) -eq 0; and return 0
  for line in (printf '%s\n' $ports | command sort | command uniq -c)
    set -l parts (string match -r '^\s*(\d+)\s+(\d+)$' -- $line)
    test (count $parts) -eq 3; or continue
    echo "$parts[3] $parts[2]"
  end
end

# ps reports elapsed time as [[dd-]hh:]mm:ss. Two units is what a reader wants: "3d1h"
# rather than "3d1h5m23s", and never a bare "0m" for a process that started this second.
function _port_age --argument-names etime
  set -l days 0
  set -l rest $etime
  set -l split (string split -m1 -- '-' $etime)
  if test (count $split) -eq 2
    set days $split[1]
    set rest $split[2]
  end

  set -l parts (string split -- ':' $rest)
  set -l hours 0
  set -l mins 0
  set -l secs 0
  switch (count $parts)
    case 3
      set hours $parts[1]
      set mins $parts[2]
      set secs $parts[3]
    case 2
      set mins $parts[1]
      set secs $parts[2]
    case '*'
      return 0
  end

  set days (string trim -l -c 0 -- $days); test -n "$days"; or set days 0
  set hours (string trim -l -c 0 -- $hours); test -n "$hours"; or set hours 0
  set mins (string trim -l -c 0 -- $mins); test -n "$mins"; or set mins 0
  set secs (string trim -l -c 0 -- $secs); test -n "$secs"; or set secs 0

  if test $days -gt 0
    test $hours -gt 0; and echo "$days"d"$hours"h; or echo "$days"d
  else if test $hours -gt 0
    test $mins -gt 0; and echo "$hours"h"$mins"m; or echo "$hours"h
  else if test $mins -gt 0
    echo "$mins"m
  else
    echo "$secs"s
  end
end

# A node command line can run to several hundred characters, which wraps the note over
# four lines and buries the row above it. The terminal decides how much survives.
function _port_trim --argument-names text
  set -l width 100
  test -n "$COLUMNS"; and set width (math "max(60, $COLUMNS - 8)")
  test (string length -- "$text") -le $width; and echo $text; and return 0
  echo (string sub -l (math $width - 1) -- "$text")…
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
