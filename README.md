# AGRAD-Hicham-REDDAD-Yasser
# Système de Reconnaissance Faciale avec Django

## Description
-Un système de reconnaissance faciale complet avec Django, OpenCV et la bibliothèque face_recognition. Cette application permet non seulement d'identifier des visages à partir d'images téléchargées mais également d'effectuer une détection faciale en temps réel via webcam.

## Fonctionnalités
- **Détection en temps réel** : Reconnaissance faciale via webcam avec identification des personnes connues
- **Capture automatique** : Enregistrement des visages inconnus détectés
- **Interface conviviale** : Formulaire d'enregistrement pour les nouveaux visages détectés
- **Traitement d'images** : Identification à partir d'images téléchargées
- **Optimisation de performance** : Traitement vidéo optimisé pour une exécution fluide

## Technologies utilisées
- Django 4.2+ : Framework web Python
- OpenCV 4.8+ : Bibliothèque de vision par ordinateur
- face_recognition 1.3+ : API de reconnaissance faciale (basée sur dlib)
- Bootstrap : Pour l'interface utilisateur responsive
- SQLite : Base de données par défaut

## Installation

1. Clonez le dépôt :
```bash
git clone https://github.com/your-username/Systeme-de-Reconnaissance-Faciale-avec-Django.git
cd Systeme-de-Reconnaissance-Faciale-avec-Django
```

2. Créez et activez un environnement virtuel :
```bash
python -m venv env
# Sous Windows
env\Scripts\activate
# Sous Linux/Mac
source env/bin/activate
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

4. Effectuez les migrations :
```bash
python manage.py migrate
```

5. Lancez le serveur :
```bash
python manage.py runserver
```

6. Accédez à l'application dans votre navigateur à l'adresse `http://127.0.0.1:8000/`

## Utilisation
- **Page d'accueil** : Accès à la détection en temps réel
- **Détection en temps réel** : Visualisez la vidéo de votre webcam avec identification des visages connus
- **Enregistrement** : Remplissez le formulaire pour ajouter un nouveau visage
- **Identification** : Téléchargez une image pour identifier une personne

## Notes importantes
- Assurez-vous que votre webcam est correctement configurée et accessible
- La qualité de la reconnaissance dépend de l'éclairage et de la résolution de la caméra
- Pour une meilleure performance, exécutez l'application sur un ordinateur avec une puissance de calcul suffisante

## Contribuer
Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou à proposer une pull request.

