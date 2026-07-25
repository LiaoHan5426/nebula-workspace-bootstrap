# Nebula workspace guidance

This directory contains architecture and planning material that spans the
backend and frontend repositories.

## Repository boundaries

| Directory | Responsibility |
| --- | --- |
| `../nebula` | Backend source and backend-only documentation |
| `../nebula-studio` | Frontend source and frontend-only documentation |
| `../docs` | Cross-repository plans and integration documentation |
| `.` | Cross-repository architecture and decisions |

Do not commit files from `nebula/` or `nebula-studio/` through the workspace
meta repository. Each nested repository owns its own Git history.

## Portable commands

Run workspace maintenance from the workspace root:

```powershell
.\workspace.ps1 doctor
.\workspace.ps1 update
```

Do not record machine-specific absolute paths in tracked planning documents or
configuration. Use paths relative to the workspace root.
