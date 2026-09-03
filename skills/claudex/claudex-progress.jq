select(.item) | .item as $i |
if   .type=="item.started"   and $i.type=="command_execution" then "  $ " + ($i.command | sub("^/bin/[a-z]+ -lc ";"") | ltrimstr("'") | rtrimstr("'"))
elif .type=="item.completed" and $i.type=="file_change"       then ($i.changes[] | "  [" + .kind + "] " + (.path | sub($root;"")))
elif .type=="item.completed" and $i.type=="agent_message"     then "  > " + ($i.text | split("\n")[0])
else empty end
