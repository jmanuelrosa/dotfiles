function _tv_jira --description "Television jira cable: list / preview / transition tickets" --argument-names cmd arg
    set -l ROW_FILTER '
def col(c): "[" + c + "m";
def reset:  "[0m";
def pad(n): (. + (" " * n))[0:n];
def sc: .fields.status.statusCategory.colorName // "";
def sc_col:
    if sc == "green" then "32"
    elif sc == "yellow" then "33"
    elif sc == "blue-gray" or sc == "medium-gray" then "34"
    else "37" end;
def prio: .fields.priority.name // "—";
def prio_col:
    if prio == "Highest" or prio == "High" then "31"
    elif prio == "Medium" then "33"
    else "90" end;
def icon:
    .fields.issuetype.name as $t |
    if   $t == "Bug"                            then "🐛"
    elif $t == "Story"                          then "📗"
    elif $t == "Task"                           then "✅"
    elif $t == "Sub-task" or $t == "Subtask"    then "🔸"
    elif $t == "Epic"                           then "🌟"
    else "◆" end;
.[] | "\(.key | pad(10)) \(col(sc_col))●\(reset) \(.fields.status.name | pad(20))  \(col(prio_col))▲\(reset) \(prio | pad(7))  \(icon)  \(.fields.summary)"
'

    switch $cmd
        case list
            set -l preset $arg
            set -l jql
            switch $preset
                case all ""
                    set jql 'assignee = currentUser() ORDER BY updated DESC'
                case backlog
                    set jql 'assignee = currentUser() AND status = "Backlog" ORDER BY updated DESC'
                case selected
                    set jql 'assignee = currentUser() AND status = "Selected for Development" ORDER BY updated DESC'
                case in-progress
                    set jql 'assignee = currentUser() AND status = "In Progress" ORDER BY updated DESC'
                case ready
                    set jql 'assignee = currentUser() AND status = "Ready for production" ORDER BY updated DESC'
                case '*'
                    echo "_tv_jira list: preset must be all|backlog|selected|in-progress|ready" >&2
                    return 1
            end

            set -l json (acli jira workitem search --jql "$jql" --fields key,summary,status,priority,issuetype --json 2>/dev/null)
            test -z "$json"; and set json '[]'
            echo $json | jq -r "$ROW_FILTER" 2>/dev/null

        case preview
            set -l key $arg
            test -z "$key"; and return 0
            acli jira workitem view $key 2>/dev/null
            echo
            echo "── recent comments ──"
            acli jira workitem comment list --key $key --json 2>/dev/null \
                | jq -r '.comments[-5:][]? | "[\(.id)] \(.author): \(.body | split("\n") | join(" ") | .[0:280])"' 2>/dev/null

        case transition
            set -l key $arg
            test -z "$key"; and begin
                echo "_tv_jira transition: missing key" >&2
                return 1
            end
            set -l proj (string split -m 1 - $key)[1]
            set -l status (acli jira workitem search --jql "project = $proj" --fields status --json --limit 100 2>/dev/null \
                | jq -r '.[].fields.status.name' | sort -u \
                | fzf --prompt "Transition $key → " --height 40%)
            test -z "$status"; and return 0
            acli jira workitem transition --key $key --status "$status" --yes

        case '*'
            echo "_tv_jira: cmd must be 'list', 'preview', or 'transition'" >&2
            return 1
    end
end
