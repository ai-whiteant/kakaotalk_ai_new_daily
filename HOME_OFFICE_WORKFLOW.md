# HOME_OFFICE_WORKFLOW — Kakao ai news

## Canonical path on both PCs
`C:\Vibe Coding\kakaotalk_ai_new_daily`

Use the same path at home and office whenever possible.

## Source of truth
- Project source and project history: GitHub
- Project-specific instructions: repository `AGENTS.md`
- Current work state: repository `SESSION_HANDOFF.md`
- Global Codex instructions: Google Drive-linked global `AGENTS.md`
- Secrets and runtime state: local PC only

## Start work
```powershell
cd "C:\Vibe Coding\kakaotalk_ai_new_daily"
git status -sb
git pull
git log -1 --oneline
```

Only pull when the local worktree is safe.

Then open this same folder in Codex and read:
1. `AGENTS.md`
2. `SESSION_HANDOFF.md`
3. the current phase instruction

## End work
Before leaving a PC:
1. Run relevant tests.
2. Update `SESSION_HANDOFF.md`.
3. Review `git status -sb`.
4. Stage only approved files.
5. Check for secrets.
6. Commit.
7. Push only after explicit approval when the project policy requires it.

## Never synchronize through Git
- `.env`
- API keys / tokens / client secrets
- encrypted/local credential state
- virtual environments
- runtime caches
- SQLite runtime state
- local result-package ZIP archives unless explicitly approved
- local session-transfer folders

## Home → Office
Home:
`commit → approved push`

Office:
`pull → read SESSION_HANDOFF.md → continue`

## Office → Home
Office:
`commit → approved push`

Home:
`pull → read SESSION_HANDOFF.md → continue`

## Phase gate rule
For major phase transitions:
`complete implementation → tests → independent review → PASS → next phase`

Do not treat the existence of an output file alone as a phase PASS.
