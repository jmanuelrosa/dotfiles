function _port_usage --description "Print port usage"
  echo "Usage: port [PORT] [options]"
  echo
  echo "With no argument, list every TCP port in LISTEN state and the process bound to it."
  echo "With PORT, show every TCP and UDP socket using that port, LISTEN and ESTABLISHED"
  echo "alike, so a client holding the port open shows up as readily as a server bound to it."
  echo
  echo "Options"
  echo "  -u, --udp    also list UDP sockets bound to a real port (listing mode only)"
  echo "  -h, --help   this text"
  echo
  echo "UDP has no LISTEN state, so --udp reports every bound socket instead: wildcard-port"
  echo "sockets (\"*:*\") and outbound conversations on an ephemeral port are skipped, since"
  echo "neither is what a caller means by \"which port\"."
end
