# =============================================================
# setup_dispatch.ps1 — Dispatch Engine · Banque Zitouna
# Lancer depuis la racine du projet (là où est main.py)
# Usage : .\setup_dispatch.ps1
# =============================================================

Write-Host "🚀 Setup Dispatch Engine — Banque Zitouna" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ─────────────────────────────────────────────
# 1. Dossiers
# ─────────────────────────────────────────────
Write-Host "`n📁 Création des dossiers..." -ForegroundColor Yellow

New-Item -ItemType Directory -Force -Path "app\agents\templates\sms"  | Out-Null
New-Item -ItemType Directory -Force -Path "app\agents\templates\email" | Out-Null

Write-Host "✅ Dossiers créés" -ForegroundColor Green

# ─────────────────────────────────────────────
# 2. Fichiers Python agents/
# ─────────────────────────────────────────────
Write-Host "`n🐍 Création des fichiers Python..." -ForegroundColor Yellow

$agentFiles = @(
    "app\agents\__init__.py",
    "app\agents\dispatch_engine.py",
    "app\agents\email_agent.py",
    "app\agents\sms_agent.py",
    "app\agents\whatsapp_agent.py",
    "app\agents\template_engine.py",
    "app\agents\scheduler.py",
    "app\agents\logs.py"
)

foreach ($f in $agentFiles) {
    if (-Not (Test-Path $f)) {
        New-Item -ItemType File -Force -Path $f | Out-Null
        Write-Host "  created : $f" -ForegroundColor DarkGray
    } else {
        Write-Host "  exists  : $f (skipped)" -ForegroundColor DarkGray
    }
}

Write-Host "✅ Fichiers agents créés" -ForegroundColor Green

# ─────────────────────────────────────────────
# 3. Router FastAPI
# ─────────────────────────────────────────────
Write-Host "`n🔌 Création du router dispatch..." -ForegroundColor Yellow

New-Item -ItemType File -Force -Path "app\api\v1\endpoints\dispatch.py" | Out-Null

Write-Host "✅ Router créé" -ForegroundColor Green

# ─────────────────────────────────────────────
# 4. Templates Jinja2
# ─────────────────────────────────────────────
Write-Host "`n📝 Création des templates Jinja2..." -ForegroundColor Yellow

$templates = @(
    # SMS
    "app\agents\templates\sms\J0.txt",
    "app\agents\templates\sms\J7.txt",
    "app\agents\templates\sms\J7_whatsapp.txt",
    "app\agents\templates\sms\J15.txt",
    "app\agents\templates\sms\J30.txt",
    "app\agents\templates\sms\J90.txt",
    # Email sujets
    "app\agents\templates\email\J15_subject.txt",
    "app\agents\templates\email\J30_subject.txt",
    "app\agents\templates\email\J60_subject.txt",
    "app\agents\templates\email\J90_subject.txt",
    "app\agents\templates\email\J180_subject.txt",
    # Email corps texte
    "app\agents\templates\email\J15.txt",
    "app\agents\templates\email\J30.txt",
    "app\agents\templates\email\J60.txt",
    "app\agents\templates\email\J90.txt",
    "app\agents\templates\email\J180_internal.txt",
    "app\agents\templates\email\J180_internal_subject.txt",
    # Email HTML
    "app\agents\templates\email\J15.html",
    "app\agents\templates\email\J30.html"
)

foreach ($t in $templates) {
    if (-Not (Test-Path $t)) {
        New-Item -ItemType File -Force -Path $t | Out-Null
        Write-Host "  created : $t" -ForegroundColor DarkGray
    } else {
        Write-Host "  exists  : $t (skipped)" -ForegroundColor DarkGray
    }
}

Write-Host "✅ Templates créés" -ForegroundColor Green

# ─────────────────────────────────────────────
# 5. Résumé final
# ─────────────────────────────────────────────
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "✅ Setup terminé !" -ForegroundColor Green
Write-Host ""
Write-Host "Prochaines étapes :" -ForegroundColor White
Write-Host "  1. Copier le contenu des .py dans app\agents\" -ForegroundColor White
Write-Host "  2. Ajouter les variables dans .env" -ForegroundColor White
Write-Host "  3. Lancer la migration Alembic (dans Docker) :" -ForegroundColor White
Write-Host "       docker exec recouvrement_api alembic revision --autogenerate -m 'add_dispatch_logs'" -ForegroundColor Yellow
Write-Host "       docker exec recouvrement_api alembic upgrade head" -ForegroundColor Yellow
Write-Host "  4. Modifier main.py (voir instructions)" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
