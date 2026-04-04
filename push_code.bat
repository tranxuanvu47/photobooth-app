@echo off
set TOKEN=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
set REMOTE_URL=https://%TOKEN%@github.com/tranxuanvu47/photobooth-app.git
set BRANCH=teonui

echo --- Staging changes ---
git add .

echo --- Committing changes ---
git commit -m "Update Admin settings: Print control, Auto-Return toggle, and Gallery limit"

echo --- Setting remote URL with authentication ---
git remote set-url origin %REMOTE_URL%

echo --- Pushing to branch: %BRANCH% ---
git push origin %BRANCH%

echo --- Done ---
pause
