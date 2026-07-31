function _lns_target --description "The absolute path a symlink points at, one hop, without following the rest of the chain"
  set -l link $argv[1]
  set -l raw (command readlink -- "$link")

  # A real link always stores something, so an empty answer means readlink could not read
  # it (an unreadable parent, a sandbox). Returning nothing is the point: normalizing an
  # empty target would yield the link's own parent directory, and reporting that as "what
  # this points at" is worse than admitting the target is unknown.
  if test -z "$raw"
    return 1
  end

  # readlink returns whatever the link literally stores, which is often relative, so it
  # gets resolved against the link's own directory. `path resolve` would be shorter but
  # answers with the end of the whole chain, and on macOS that rewrites the path out from
  # under you: a link to /var/folders/x reads back as /private/var/folders/x, which no
  # longer contains the string --contains was given. `path normalize` follows nothing and
  # needs nothing on disk to exist, so a broken link still yields a comparable path.
  if string match -q '/*' -- $raw
    path normalize -- "$raw"
  else
    path normalize -- (path dirname -- "$link")/"$raw"
  end
end
