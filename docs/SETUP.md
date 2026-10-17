# Setup: FlyWire / CAVE Access

`superfly`'s `FlyWireDataSource` talks to the real FlyWire connectome via
[fafbseg](https://fafbseg-py.readthedocs.io/) and
[CAVEclient](https://caveclient.readthedocs.io/). This is a one-time, manual
setup step tied to your own FlyWire/CAVE account — it cannot be automated or
scripted on your behalf, and there is no project-level shared credential.

You do **not** need to do any of this to develop or test `superfly` itself:
`MockDataSource` provides fully offline synthetic fixture data for that. Only
do this when you're ready to query the real dataset.

## 1. Register for CAVE Framework access

1. Go to the CAVE Framework auth portal and sign in (Google login is
   supported).
2. Request/accept access to the FlyWire FAFB production dataset. Approval may
   not be instant — it can require manual review on CAVE's side.

## 2. Generate an auth token

Once you have an account with dataset access, generate a token through
`caveclient`'s built-in auth flow:

```python
from caveclient import CAVEclient

client = CAVEclient()
client.auth.get_new_token()  # opens a browser flow / prints a URL to visit
client.auth.save_token(token="<paste the token shown after authenticating>")
```

This only needs to be run once per machine. `CAVEclient` handles the rest of
the token lifecycle (refresh, reuse) automatically afterward.

## 3. Where the token is stored

`caveclient` writes the token to:

```
~/.cloudvolume/secrets/cave-secret.json
```

This file is created with standard user-only file permissions by
`caveclient` itself — `superfly` never reads, writes, or otherwise touches
it directly. `FlyWireDataSource` simply constructs a `CAVEclient()` instance,
which picks the token up from this file automatically.

## 4. Never commit your token

- This file lives outside the repo (under your home directory), so normal
  `git add`/`git commit` usage won't pick it up.
- As a safety net, double-check `.gitignore` excludes any `*cave-secret*` or
  `*.cloudvolume*` paths before committing if you ever copy credentials
  somewhere inside the project directory for local experimentation — but the
  default setup above never requires doing so.
- If a token is ever accidentally exposed (e.g. committed, logged, or
  pasted somewhere public), revoke it from the CAVE auth portal and generate
  a new one immediately.

## 5. Verify it works

```python
from superfly.datasources.flybywire import FlyWireDataSource

ds = FlyWireDataSource()
ds.client  # raises AuthenticationError with a hint back to this doc on failure
```

If authentication fails, `FlyWireDataSource` raises `AuthenticationError`
with a message pointing back to this document.
