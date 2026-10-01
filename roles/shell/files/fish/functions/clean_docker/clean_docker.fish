function clean_docker --description "Stop every container, then prune images, build cache and volumes"
  _ui title "🐳 Cleaning Docker ..."
  begin
    set containers (docker ps -aq)
    if test -n "$containers"
      _ui step "Stopping "(count $containers)" container(s)"
      docker stop $containers
    end
    docker system prune -a --volumes
    docker volume prune --all --force
  end
  _ui done "Cleanup complete!"
end
