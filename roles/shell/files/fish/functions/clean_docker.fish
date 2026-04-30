function clean_docker
  echo '⏰ Deleting docker ...'
  begin;
    set containers (docker ps -aq)
    if test -n "$containers"
      docker stop $containers
    end
    docker system prune -a --volumes
    docker volume prune --all --force
  end
  echo '✨ Cleanup complete!'
end
