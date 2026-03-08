function claude-skill --description "Manage Claude Code skills for the current project"
  set -l skills_source "$DOTFILES_DIR/roles/ai/files/claude/skills"
  set -l skills_target ".claude/skills"

  if test (count $argv) -lt 1
    echo "Usage: claude-skill <list|add|remove> [skill-name]"
    return 1
  end

  switch $argv[1]
    case list
      echo "Available skills:"
      for skill in $skills_source/*/
        set -l name (basename $skill)
        if test -L "$skills_target/$name"
          echo "  $name (linked)"
        else
          echo "  $name"
        end
      end

    case add
      if test (count $argv) -lt 2
        echo "Usage: claude-skill add <skill-name>"
        return 1
      end
      set -l name $argv[2]
      if not test -d "$skills_source/$name"
        echo "Skill '$name' not found. Run 'claude-skill list' to see available skills."
        return 1
      end
      mkdir -p $skills_target
      ln -sf "$skills_source/$name" "$skills_target/$name"
      echo "Linked '$name' into $skills_target/"

    case remove
      if test (count $argv) -lt 2
        echo "Usage: claude-skill remove <skill-name>"
        return 1
      end
      set -l name $argv[2]
      if not test -L "$skills_target/$name"
        echo "Skill '$name' is not linked in this project."
        return 1
      end
      rm "$skills_target/$name"
        echo "Removed '$name' from $skills_target/"

    case '*'
        echo "Usage: claude-skill <list|add|remove> [skill-name]"
        return 1
  end
end
