cat > README.md << 'EOF'
# Système de Recouvrement Intelligent - Backend

## 🚀 Démarrage Rapide

### Lancement
```bash
# Démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f fastapi

# Arrêter
docker-compose down
```

### Services
- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs
- pgAdmin: http://localhost:5050

### Commandes Utiles
```bash
# Rebuild
docker-compose up -d --build

# Redémarrer un service
docker-compose restart fastapi

# Nettoyer
docker-compose down -v
```
EOF
