if not status is-interactive
  return
end

set -g GCLOUD_DIRECTORY_PROFILES \
  "$HOME/Developer/work/addingwell" didomi

function __gcloud_directory_profile --on-variable PWD
  set -l mappings $GCLOUD_DIRECTORY_PROFILES
  set -l selected ""
  set -l selected_root_length 0

  while set -q mappings[2]
    set -l root (path normalize -- "$mappings[1]")
    set -l root_length (string length -- "$root")
    set -l prefix "$root/"
    test "$root" = /; and set prefix /
    set -l prefix_length (string length -- "$prefix")
    set -l current_prefix (string sub --length "$prefix_length" -- "$PWD")

    if test "$PWD" = "$root"; or test "$current_prefix" = "$prefix"
      if test "$root_length" -gt "$selected_root_length"
        set selected "$mappings[2]"
        set selected_root_length "$root_length"
      end
    end
    set mappings $mappings[3..-1]
  end

  if test -n "$selected"
    if not set -q __gcloud_directory_had_config
      if set -q CLOUDSDK_ACTIVE_CONFIG_NAME
        set -g __gcloud_directory_had_config true
        set -g __gcloud_directory_previous_config $CLOUDSDK_ACTIVE_CONFIG_NAME
      else
        set -g __gcloud_directory_had_config false
      end
    end
    set -gx CLOUDSDK_ACTIVE_CONFIG_NAME "$selected"
  else if set -q __gcloud_directory_had_config
    if test "$__gcloud_directory_had_config" = true
      set -gx CLOUDSDK_ACTIVE_CONFIG_NAME $__gcloud_directory_previous_config
    else
      set -eg CLOUDSDK_ACTIVE_CONFIG_NAME
    end
    set -eg __gcloud_directory_had_config __gcloud_directory_previous_config
  end
end

__gcloud_directory_profile
