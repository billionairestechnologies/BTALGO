@echo off
setlocal

cd /d "%~dp0"

echo.
echo BillionairsHQ Whitelabel Setup
echo ------------------------------
echo Press Enter to keep the default shown in brackets.
echo.

set "PRODUCT_NAME="
set /p PRODUCT_NAME=Product name [BillionairsHQ]: 
if "%PRODUCT_NAME%"=="" set "PRODUCT_NAME=BillionairsHQ"

set "COMPANY_NAME="
set /p COMPANY_NAME=Company name [Billionaires Technologies]: 
if "%COMPANY_NAME%"=="" set "COMPANY_NAME=Billionaires Technologies"

set "WEBSITE_URL="
set /p WEBSITE_URL=Website URL [https://www.billionairestechnologies.com]: 
if "%WEBSITE_URL%"=="" set "WEBSITE_URL=https://www.billionairestechnologies.com"

set "DOCS_URL="
set /p DOCS_URL=Docs URL [https://docs.billionairestechnologies.com]: 
if "%DOCS_URL%"=="" set "DOCS_URL=https://docs.billionairestechnologies.com"

set "REPO_URL="
set /p REPO_URL=Repo URL [https://github.com/billionairestechnologies/QuantX]: 
if "%REPO_URL%"=="" set "REPO_URL=https://github.com/billionairestechnologies/QuantX"

echo.
python scripts\apply_whitelabel.py ^
  --product-name "%PRODUCT_NAME%" ^
  --company-name "%COMPANY_NAME%" ^
  --website-url "%WEBSITE_URL%" ^
  --docs-url "%DOCS_URL%" ^
  --repo-url "%REPO_URL%"

if errorlevel 1 (
  echo.
  echo Whitelabel setup failed.
  pause
  exit /b 1
)

echo.
echo Done. Review .sample.env and frontend\index.html, then restart the app.
pause
