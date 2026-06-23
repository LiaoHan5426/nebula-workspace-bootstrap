{
  "workspace": {
    "name": "nebula-workspace",
    "folders": [
      {
        "name": "workspace",
        "path": "."
      },
      %FOLDER_ENTRIES%
    ],
    "settings": {
      "python.pythonPath": "%PYTHON_PATH%"
    }
  },
  "extensions": {
    "recommendations": [
      "rust-lang.rust-analyzer",
      "dbaeumer.vscode-eslint",
      "esbenp.prettier-vscode",
      "redhat.vscode-yaml"
    ]
  },
  "trae": {
    "rules": {
      "scanPaths": %RULES_SCAN_PATHS%
    },
    "skills": {
      "scanPaths": %SKILLS_SCAN_PATHS%
    },
    "hooks": {
      "enabled": true,
      "path": ".trae/hooks.json"
    },
    "mcp": {
      "enabled": true,
      "configPath": ".trae/mcp.json"
    }
  }
}