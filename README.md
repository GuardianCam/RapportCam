#  Camera  Report

Un script Python qui t'envoie chaque matin sur **Telegram** l'état de ton système de vidéosurveillance :

-  caméras en ligne / hors ligne
-  espace disque (avec alerte au-dessus d'un seuil)
-  nombre d'événements enregistrés pendant la nuit, par caméra

Aucune dépendance : Python 3.8+ uniquement. Compatible avec n'importe quel NVR qui enregistre dans un dossier (Frigate, Synology, Hikvision via NAS, ZoneMinder, etc.).

## Exemple de message

```
 Rapport sécurité — 24/10/2026 07:30

 Caméras : 2/3 en ligne
   Garage HORS LIGNE

 Stockage
   Disque NVR : 91% utilisé (180 Go libres sur 2000 Go)

 Nuit (22:00 → 07:00)
  14 événement(s) enregistré(s)
  • entree : 9
  • jardin : 5

 2 point(s) à vérifier
```

## Installation

1. **Crée un bot Telegram** : parle à [@BotFather](https://t.me/BotFather), envoie `/newbot`, récupère le *token*.
2. **Trouve ton chat_id** : envoie un message à ton bot, puis ouvre
   `https://api.telegram.org/bot<TOKEN>/getUpdates` et cherche `"chat":{"id": ...}`.
3. **Configure** :
   ```bash
   cp config.example.json config.json
   nano config.json      # adresses des caméras, chemins des disques, etc.
   ```
4. **Teste sans envoyer** :
   ```bash
   python3 report.py --dry-run
   ```
5. **Teste l'envoi réel** :
   ```bash
   python3 report.py
   ```

## Automatiser chaque matin (Linux / Raspberry Pi / NAS)

```bash
crontab -e
```
Ajoute cette ligne (tous les jours à 7h30) :
```
30 7 * * * /usr/bin/python3 /chemin/vers/report.py >> /tmp/report.log 2>&1
```

Sur Windows : Planificateur de tâches → action « Démarrer un programme » → `python report.py`.

## Sécurité

- `config.json` est dans le `.gitignore` : **ne le publie jamais** (il contient ton token et tes IP).
- Tu peux aussi passer les identifiants par variables d'environnement : `TELEGRAM_TOKEN` et `TELEGRAM_CHAT_ID`.

## Comment ça détecte une caméra « en ligne » ?

Le script tente une connexion TCP sur le port de la caméra (554 = RTSP par défaut). Si le port répond, la caméra est considérée en ligne.

## Idées d'amélioration

- Envoyer aussi une capture d'écran de chaque caméra
- Ajouter Discord ou email comme canal
- Historique dans un fichier CSV + graphique d'espace disque
- Résumé des événements par IA
