from django.shortcuts import render, redirect
from .forms import FaceForm, IdentifyForm, UnknownFaceForm
from .models import Face, UnknownFace
import face_recognition
from django.contrib import messages
import os
from django.conf import settings
import cv2
import numpy as np
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
import base64
from datetime import datetime
import traceback
import gc
import threading
import time

# Variable globale pour le contrôle du flux vidéo
video_camera = None
video_thread = None
video_active = False

def get_camera():
    global video_camera
    if video_camera is None:
        try:
            video_camera = cv2.VideoCapture(0)
            if not video_camera.isOpened():
                print("Erreur: Impossible d'ouvrir la webcam")
                video_camera = None
        except Exception as e:
            print(f"Erreur lors de l'initialisation de la caméra: {e}")
            video_camera = None
    return video_camera

def release_camera():
    global video_camera
    if video_camera is not None:
        video_camera.release()
        video_camera = None
        gc.collect()  # Force garbage collection
        print("Caméra libérée")

def register_face(request):
    if request.method == 'POST':
        form = FaceForm(request.POST, request.FILES)
        if form.is_valid():
            face = form.save(commit=False)

            # Ensure the media directory exists
            media_dir = os.path.join(settings.BASE_DIR, 'media')
            if not os.path.exists(media_dir):
                os.makedirs(media_dir)

            # Save the uploaded image
            image_file = request.FILES['image']
            image_path = os.path.join(media_dir, image_file.name)

            with open(image_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)

            # Process the image
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)

            if len(encodings) > 0:
                face.save()  # Save the face object
                face.save_encoding(encodings[0])
                messages.success(request, "Visage enregistré avec succès.")
                return redirect('register_face')
            else:
                messages.error(request, "Aucun visage détecté dans l'image.")

    else:
        form = FaceForm()

    return render(request, 'facial_app/register.html', {'form': form})

def identify_face(request):
    name_result = None

    if request.method == 'POST':
        form = IdentifyForm(request.POST, request.FILES)
        if form.is_valid():
            image_file = request.FILES['image']
            image_path = f'media/{image_file.name}'

            with open(image_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)

            unknown_image = face_recognition.load_image_file(image_path)
            unknown_encodings = face_recognition.face_encodings(unknown_image)

            if len(unknown_encodings) == 0:
                messages.error(request, "Aucun visage détecté.")
            else:
                unknown_encoding = unknown_encodings[0]
                known_faces = Face.objects.all()

                names = []
                for face in known_faces:
                    known_encoding = face.get_encoding()
                    if known_encoding is not None:
                        result = face_recognition.compare_faces([known_encoding], unknown_encoding)
                        if result[0]:
                            names.append(face.name)

                if names:
                    name_result = ", ".join(set(names))
                else:
                    name_result = "Inconnu"

    else:
        form = IdentifyForm()

    return render(request, 'facial_app/identify.html', {
        'form': form,
        'result': name_result
    })

def gen_frames():
    global video_active
    video_active = True
    camera = get_camera()
    if camera is None:
        yield b'--frame\r\n'
        yield b'Content-Type: text/plain\r\n\r\n'
        yield b'Camera not available\r\n'
        return

    # Charger tous les visages connus
    try:
        known_faces = Face.objects.all()
        known_face_encodings = []
        known_face_names = []
        
        for face in known_faces:
            encoding = face.get_encoding()
            if encoding is not None:
                known_face_encodings.append(encoding)
                known_face_names.append(f"{face.name} {face.surname}")
    except Exception as e:
        print(f"Erreur lors du chargement des visages connus: {e}")
        known_face_encodings = []
        known_face_names = []

    process_this_frame = True
    frame_count = 0
    
    # Variables pour stocker les informations de visages détectés
    current_face_locations = []
    current_face_names = []
    
    # Compteur pour éliminer les faux positifs
    no_face_counter = 0
    face_detection_threshold = 3  # Nombre de frames sans visage avant de réinitialiser

    try:
        while video_active:
            success, frame = camera.read()
            if not success:
                print("Erreur: Impossible de lire une frame de la caméra")
                time.sleep(0.1)  # Petite pause pour éviter de saturer le CPU
                continue

            frame_count += 1
            
            # Ne détecter les visages qu'une frame sur 5 pour améliorer les performances
            if frame_count % 5 == 0:
                try:
                    # Réduire la taille du frame pour de meilleures performances
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                    
                    # Convertir l'image de BGR (OpenCV) à RGB (face_recognition)
                    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                    # Détecter les visages avec une plus grande confiance
                    face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
                    
                    if face_locations:  # Seulement si des visages sont détectés
                        # Réinitialiser le compteur quand un visage est détecté
                        no_face_counter = 0
                        
                        # Sauvegarder les localisations de visages pour toutes les frames
                        current_face_locations = []
                        current_face_names = []
                        
                        # Obtenir les encodages
                        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                        # Pour chaque visage détecté
                        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                            # Vérifier si c'est vraiment un visage (distance entre les yeux, etc.)
                            face_width = right - left
                            face_height = bottom - top
                            
                            # Filtrer les très petits visages (probablement des faux positifs)
                            if face_width < 20 or face_height < 20:
                                continue
                                
                            # Multiplier les coordonnées par 4 car on a réduit l'image
                            top *= 4
                            right *= 4
                            bottom *= 4
                            left *= 4
                            
                            # Sauvegarder la localisation ajustée
                            current_face_locations.append((top, right, bottom, left))

                            name = "Inconnu"
                            if known_face_encodings:  # Seulement si nous avons des visages connus
                                # Vérifier si le visage correspond à un visage connu
                                matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
                                
                                if True in matches:
                                    first_match_index = matches.index(True)
                                    name = known_face_names[first_match_index]
                            
                            # Sauvegarder le nom
                            current_face_names.append(name)
                    else:
                        # Incrémenter le compteur quand aucun visage n'est détecté
                        no_face_counter += 1
                        
                        # Réinitialiser après un certain nombre de frames sans visage
                        if no_face_counter >= face_detection_threshold:
                            current_face_locations = []
                            current_face_names = []
                            no_face_counter = 0
                except Exception as e:
                    print(f"Erreur lors du traitement de la frame: {e}")
                    traceback.print_exc()
            
            # Dessiner les rectangles pour tous les visages actuellement détectés
            # même sur les frames où on ne fait pas de nouvelle détection
            for (top, right, bottom, left), name in zip(current_face_locations, current_face_names):
                # Dessiner un rectangle autour du visage
                color = (0, 255, 0) if name != "Inconnu" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

                # Ajouter le nom sous le rectangle
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)

            # Encoder l'image en JPEG avec qualité réduite pour meilleures performances
            try:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            except Exception as e:
                print(f"Erreur lors de l'encodage de l'image: {e}")
                time.sleep(0.1)  # Éviter de saturer le CPU en cas d'erreur
                continue
    except Exception as e:
        print(f"Erreur dans gen_frames: {e}")
        traceback.print_exc()
    finally:
        # Ne pas libérer la caméra ici pour permettre son utilisation par d'autres fonctions
        pass

def video_feed(request):
    try:
        return StreamingHttpResponse(gen_frames(),
                    content_type='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print(f"Erreur dans video_feed: {e}")
        traceback.print_exc()
        return HttpResponse("Erreur de streaming vidéo", status=500)

def realtime_detection(request):
    return render(request, 'facial_app/realtime.html')

@csrf_exempt
def process_unknown_face(request):
    if request.method == 'POST':
        try:
            print("Début du traitement d'un visage inconnu")
            
            # Gérer à la fois les requêtes AJAX et les requêtes standard
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                image_data = data.get('image', '')
                
                # S'assurer que l'image est au format base64
                if 'data:image' in image_data:
                    image_data = image_data.split(',')[1]
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Format de requête non supporté'
                }, status=400)
                
            # Decoder l'image base64
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                print(f"Erreur de décodage base64: {e}")
                return JsonResponse({
                    'success': False,
                    'error': f'Erreur de décodage image: {str(e)}'
                }, status=400)
            
            # Créer un timestamp unique pour le nom de fichier
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'unknown_face_{timestamp}.jpg'
            
            # Créer le dossier media/unknown_faces/ s'il n'existe pas
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'unknown_faces')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            # Créer une nouvelle instance de UnknownFace
            unknown_face = UnknownFace()
            
            # Sauvegarder l'image
            try:
                unknown_face.image.save(filename, ContentFile(image_bytes), save=False)
            except Exception as e:
                print(f"Erreur lors de la sauvegarde de l'image: {e}")
                return JsonResponse({
                    'success': False,
                    'error': f'Erreur lors de la sauvegarde de l\'image: {str(e)}'
                }, status=500)
            
            # Charger l'image pour l'encodage facial
            try:
                image_array = np.frombuffer(image_bytes, np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Obtenir l'encodage facial
                face_locations = face_recognition.face_locations(rgb_image)
                if not face_locations:
                    return JsonResponse({
                        'success': False,
                        'error': 'Aucun visage détecté dans l\'image'
                    })
                
                face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
                if face_encodings:
                    unknown_face.save_encoding(face_encodings[0])
                else:
                    print("Face detected but no encoding generated")
            except Exception as e:
                print(f"Erreur lors de l'encodage du visage: {e}")
                traceback.print_exc()
                # Continue without encoding, it will be processed later
                
            # Sauvegarder l'instance dans la base de données
            try:
                unknown_face.save()
            except Exception as e:
                print(f"Erreur lors de la sauvegarde dans la base de données: {e}")
                return JsonResponse({
                    'success': False,
                    'error': f'Erreur de base de données: {str(e)}'
                }, status=500)
            
            print(f"Visage inconnu traité avec succès, ID: {unknown_face.id}")
            return JsonResponse({
                'success': True,
                'unknown_face_id': unknown_face.id
            })
        except Exception as e:
            print(f"Erreur inattendue: {e}")
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Erreur inattendue: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

def register_unknown_face(request, unknown_face_id):
    try:
        unknown_face = UnknownFace.objects.get(id=unknown_face_id)
        if request.method == 'POST':
            form = FaceForm(request.POST)
            if form.is_valid():
                new_face = form.save(commit=False)
                new_face.image = unknown_face.image  # Utiliser l'image déjà capturée
                if unknown_face.encoding:
                    new_face.encoding = unknown_face.encoding
                new_face.save()
                unknown_face.processed = True
                unknown_face.save()
                messages.success(request, "Nouveau visage enregistré avec succès!")
                return redirect('realtime_detection')
        else:
            # Créer une instance de formulaire sans le champ image
            form = FaceForm(initial={
                'name': '',
                'surname': '',
                'identifier': f'ID{unknown_face_id}',
                'email': ''
            })
            # Supprimer le champ image du formulaire car il est déjà fourni
            form.fields.pop('image')
        
        return render(request, 'facial_app/register_unknown.html', {
            'form': form,
            'unknown_face': unknown_face
        })
    except UnknownFace.DoesNotExist:
        messages.error(request, "Visage inconnu non trouvé.")
        return redirect('realtime_detection')
