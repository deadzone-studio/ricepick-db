# ricepick-db

The list [ricepick](https://github.com/M4rtwy/ricepick) reads. One file:
`rices.json`.

## Add a rice

[Open an issue with the form.](https://github.com/M4rtwy/ricepick-db/issues/new/choose)
A bot checks every field, pins the current commit of the repository, reads the
star count and whether it has been archived, and adds it right away — marked
unverified. If something is wrong it says what, and nothing is written.

`verified` is flipped by hand, after someone looks at the rice. Both kinds show
up in the program:

```
[ok]  checked
[ ?]  added by someone, not checked yet
```

## What an entry looks like

```json
{
  "name": "Serpantinum",
  "author": "ilyamiro",
  "repo": "https://github.com/ilyamiro/serpantinum",
  "commit": "5d4451f7ab55ddaced9ba350b6dba5dd2932aeb1",
  "screenshots": ["https://raw.githubusercontent.com/ilyamiro/serpantinum/5d4451f7.../previews/screenshot1.png"],
  "description": "A whole Quickshell desktop that repaints itself from your wallpaper.",
  "distros": ["arch"],
  "verified": true,
  "archived": false,
  "last_update": "2026-08-08",
  "stars": 6280,
  "added": "2026-08-20"
}
```

`commit` is what ricepick clones. Without it, the author of a rice — or whoever
takes over their account — could change what a thousand people download, and the
catalog would still be recommending it.

`archived` and `last_update` are there because rices die quietly, and a
screenshot never stops looking good.

## Rules every entry has to pass

The bot uses the same checks the program does, so the two can never disagree —
it installs `ricepick` and calls `ricepick.validate`. The rules live
[there](https://github.com/M4rtwy/ricepick/blob/main/ricepick/validate.py), in
one file.

| field | rule |
|---|---|
| `repo` | starts with `https://github.com/` or `https://gitlab.com/` |
| `screenshots` | a known image host, and an actual image file |
| `name` `author` | letters, digits, space, hyphen, up to 40 |
| `description` | one line, up to 200 characters |
| `commit` | 7 to 40 hex characters |
| `distros` | from the fixed list |
| anything else | dropped, never written |
