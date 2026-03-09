function claude:skill --description "Manage Claude Code skills for the current project"
    set -l skills_source "$DOTFILES_DIR/roles/ai/files/claude/skills"
    set -l groups_source "$DOTFILES_DIR/roles/ai/files/claude/skill-groups"
    set -l skills_target ".claude/skills"

    if test (count $argv) -lt 1
        echo "Usage: claude:skill <list|add|remove> [--group] [name]"
        return 1
    end

    set -l cmd $argv[1]
    set -l use_group false
    set -l name ""

    # Parse --group flag and name from remaining args
    for arg in $argv[2..]
        if test "$arg" = "--group"
            set use_group true
        else
            set name "$arg"
        end
    end

    switch $cmd
        case list
            if test "$use_group" = true
                echo "Available groups:"
                for group in $groups_source/*/
                    set -l gname (basename $group)
                    echo "  $gname:"
                    for skill in $group/*/
                        set -l sname (basename $skill)
                        if test -L "$skills_target/$sname"
                            echo "    $sname (linked)"
                        else
                            echo "    $sname"
                        end
                    end
                end
            else
                echo "Available skills:"
                for skill in $skills_source/*/
                    set -l sname (basename $skill)
                    if test -L "$skills_target/$sname"
                        echo "  $sname (linked)"
                    else
                        echo "  $sname"
                    end
                end
            end

        case add
            if test -z "$name"
                echo "Usage: claude:skill add [--group] <name>"
                return 1
            end
            if test "$use_group" = true
                if not test -d "$groups_source/$name"
                    echo "Group '$name' not found. Run 'claude:skill list --group' to see available groups."
                    return 1
                end
                mkdir -p $skills_target
                set -l count 0
                for skill in $groups_source/$name/*/
                    set -l sname (basename $skill)
                    ln -sf "$groups_source/$name/$sname" "$skills_target/$sname"
                    set count (math $count + 1)
                end
                echo "Linked $count skills from group '$name' into $skills_target/"
            else
                if not test -d "$skills_source/$name"
                    echo "Skill '$name' not found. Run 'claude:skill list' to see available skills."
                    return 1
                end
                mkdir -p $skills_target
                ln -sf "$skills_source/$name" "$skills_target/$name"
                echo "Linked '$name' into $skills_target/"
            end

        case remove
            if test -z "$name"
                echo "Usage: claude:skill remove [--group] <name>"
                return 1
            end
            if test "$use_group" = true
                if not test -d "$groups_source/$name"
                    echo "Group '$name' not found. Run 'claude:skill list --group' to see available groups."
                    return 1
                end
                set -l count 0
                for skill in $groups_source/$name/*/
                    set -l sname (basename $skill)
                    if test -L "$skills_target/$sname"
                        rm "$skills_target/$sname"
                        set count (math $count + 1)
                    end
                end
                echo "Removed $count skills from group '$name'"
            else
                if not test -L "$skills_target/$name"
                    echo "Skill '$name' is not linked in this project."
                    return 1
                end
                rm "$skills_target/$name"
                echo "Removed '$name' from $skills_target/"
            end

        case '*'
            echo "Usage: claude:skill <list|add|remove> [--group] [name]"
            return 1
    end
end
