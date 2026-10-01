# create_gitconfig

Prompts for a company, name, and email, then writes a company-specific Git identity file under `~/developer/<company>`.
An existing file with that name is overwritten.

```fish
create_gitconfig
```

The function prints the resulting path but does not activate the identity.
Add a matching `includeIf` directive to your main Git configuration yourself.
