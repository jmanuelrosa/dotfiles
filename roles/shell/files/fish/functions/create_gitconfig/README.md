# create_gitconfig

Prompts for a company, name, and email, then writes the company's Git identity to `~/Developer/work/.gitconfig.<company>`, the path `~/.gitconfig` includes for repositories under `~/Developer/work/<company>`.
An existing file with that name is overwritten.

```fish
create_gitconfig
```

The function prints the resulting path but does not activate the identity.
A company new to `~/.gitconfig` (`roles/apps/files/.gitconfig`) also needs a matching `includeIf` block there.
