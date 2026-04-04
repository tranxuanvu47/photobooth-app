@echo off
set TOKEN=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
set REMOTE_URL=https://%TOKEN%@github.com/tranxuanvu47/photobooth-app.git
set LOCAL_BRANCH=main
set REMOTE_BRANCH=teonui

echo --- Staging changes ---
git add .

echo --- Committing changes ---
git commit -m "Update Admin settings: Print control, Auto-Return toggle, and Gallery limit"

echo --- Setting remote URL with authentication ---
git remote set-url origin %REMOTE_URL%

echo --- FORCE Pushing current branch (%LOCAL_BRANCH%) to remote branch (%REMOTE_BRANCH%) ---
echo WARNING: This will overwrite any changes on the remote branch '%REMOTE_BRANCH%'!
git push origin %LOCAL_BRANCH%:%REMOTE_BRANCH% --force

echo --- Done ---
pause
