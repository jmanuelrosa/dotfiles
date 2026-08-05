function _port_usage --description "Print port usage"
  echo "Usage: port [PORT] [options]"
  echo
  echo "With no argument, list every TCP port in LISTEN state and the process bound to it."
  echo "With PORT, show every TCP and UDP socket using that port, LISTEN and ESTABLISHED"
  echo "alike, so a client holding the port open shows up as readily as a server bound to it."
  echo
  echo "Options"
  echo "  -l, --long   add the process working directory, its age, and how many clients are"
  echo "               connected; with PORT, its full command line too"
  echo "  -k, --kill   signal what is bound to PORT, after confirming (needs PORT)"
  echo "  -u, --udp    also list UDP sockets bound to a real port (listing mode only)"
  echo "  -h, --help   this text"
  echo
  echo "A listener is tagged local when it is bound to loopback and exposed when anything"
  echo "on the network can reach it. The tag rides on bound sockets only: an ESTABLISHED"
  echo "row is one end of a conversation and says nothing about reachability."
  echo
  echo "The listing is one row per listener, not per socket: a server bound on both address"
  echo "families is one row naming both hosts, and the closing count matches the rows. Ask"
  echo "for the port to see each socket separately."
  echo
  echo "--long reports the age of the *process*, not of the socket: macOS keeps no open"
  echo "time per socket, and no last-used time either, so a long-lived daemon that rebound"
  echo "its port reads older than the port is. The connected count is the live substitute."
  echo "Detail prints once per process, so a process holding three ports is annotated under"
  echo "the first of them. A cwd of \"/\" is dropped as noise, and a docker proxy row resolves"
  echo "to its container. The full command line is a lookup-only field: an Electron helper's"
  echo "runs past 400 characters and buries a listing, but it is why you asked about a port."
  echo
  echo "--kill targets what is *bound* to the port, never a client that merely connected,"
  echo "and stops at SIGTERM: anything still holding the port is reported with the kill -9"
  echo "to run by hand."
  echo
  echo "UDP has no LISTEN state, so --udp reports every bound socket instead: wildcard-port"
  echo "sockets (\"*:*\") and outbound conversations on an ephemeral port are skipped, since"
  echo "neither is what a caller means by \"which port\"."
end
