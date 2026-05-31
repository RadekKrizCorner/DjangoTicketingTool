# Release Strategy

## Branches

- `master` contains released code only.
- `release` is the integration branch for normal feature work.
- `feature/PROJECT-NNN-short-description` branches open merge requests to `release`.
- `review/PROJECT-NNN` branches are local review branches for this assignment.
- `hotfix/HOTFIX-short-description` branches may open emergency merge requests to `master`.
- After a hotfix is merged to `master`, merge or cherry-pick it back to `release`.

## Required Titles

Every commit title and merge request title must contain one of:

- `PROJECT-NNN`, for planned work.
- `HOTFIX-text`, for emergency production fixes.

Valid examples:

- `PROJECT-004 Add JWT user management and password reset`
- `Add auth API for PROJECT-004`
- `HOTFIX-login-token-expiry`

Invalid examples:

- `Add auth`
- `PROJECT-auth Add auth`
- `HOTFIX- Fix auth`

## GitHub Validation

The `Git Policy` workflow validates:

- merge request title
- commit titles included in the merge request
- target branch policy

Normal work must target `release`. `master` accepts only merge requests from
`release` or `hotfix/*`.

## Branch Protection

Repository code can validate metadata, but GitHub branch protection or rulesets
must block direct pushes.

Configure rules for `master`:

- Require a pull request before merging.
- Require status checks: `Git Policy` and `CI`.
- Restrict direct pushes.
- Require conversation resolution.
- Require linear history or squash merges that preserve the ticket token.

Configure rules for `release`:

- Require a pull request before merging.
- Require status checks: `Git Policy` and `CI`.
- Restrict direct pushes.

Local hooks are advisory. GitHub branch protection is the enforcement boundary.

## Local Hooks

Enable the local commit hook:

```bash
git config core.hooksPath .githooks
```

The hook rejects commit titles that do not contain `PROJECT-NNN` or `HOTFIX-text`.
