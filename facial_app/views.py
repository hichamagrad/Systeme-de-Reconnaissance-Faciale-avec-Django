from django.shortcuts import render, redirect
from .forms import FaceForm, IdentifyForm, UnknownFaceForm
from .models import Face, UnknownFace
import face_recognition
from django.contrib import messages
import os
from django.conf import settings
import cv2
import numpy as np
from django.http import JsonResponse, StreamingHttpResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
import base64
from datetime import datetime

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
    camera = cv2.VideoCapture(0)
    # Charger tous les visages connus
    known_faces = Face.objects.all()
    known_face_encodings = []
    known_face_names = []
    
    for face in known_faces:
        encoding = face.get_encoding()
        if encoding is not None:
            known_face_encodings.append(encoding)
            known_face_names.append(f"{face.name} {face.surname}")

    process_this_frame = True

    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Ne traiter qu'une frame sur deux pour améliorer les performances
            if process_this_frame:
                # Réduire la taille du frame pour de meilleures performances
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                
                # Convertir l'image de BGR (OpenCV) à RGB (face_recognition)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                # Détecter les visages
                face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
                
                if face_locations:  # Seulement si des visages sont détectés
                    # Obtenir les encodages
                    try:
                        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                        # Pour chaque visage détecté
                        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                            # Multiplier les coordonnées par 4 car on a réduit l'image
                            top *= 4
                            right *= 4
                            bottom *= 4
                            left *= 4

                            name = "Inconnu"
                            if known_face_encodings:  # Seulement si nous avons des visages connus
                                # Vérifier si le visage correspond à un visage connu
                                matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
                                
                                if True in matches:
                                    first_match_index = matches.index(True)
                                    name = known_face_names[first_match_index]

                            # Dessiner un rectangle autour du visage
                            color = (0, 255, 0) if name != "Inconnu" else (0, 0, 255)
                            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

                            # Ajouter le nom sous le rectangle
                            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                            font = cv2.FONT_HERSHEY_DUPLEX
                            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)
                    except Exception as e:
                        print(f"Erreur lors de l'encodage du visage: {str(e)}")

            process_this_frame = not process_this_frame

            # Encoder l'image en JPEG
            try:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                print(f"Erreur lors de l'encodage de l'image: {str(e)}")
                continue

def video_feed(request):
    return StreamingHttpResponse(gen_frames(),
                    content_type='multipart/x-mixed-replace; boundary=frame')

def realtime_detection(request):
    return render(request, 'facial_app/realtime.html')

@csrf_exempt
def process_unknown_face(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image').split(',')[1]
            image_bytes = base64.b64decode(image_data)
            
            # Créer un fichier temporaire pour l'image
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'unknown_face_{timestamp}.jpg'
            
            # Créer une nouvelle instance de UnknownFace
            unknown_face = UnknownFace()
            unknown_face.image.save(filename, ContentFile(image_bytes), save=False)
            
            # Charger l'image pour l'encodage facial
            image_array = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Obtenir l'encodage facial
            face_encodings = face_recognition.face_encodings(rgb_image)
            if face_encodings:
                unknown_face.save_encoding(face_encodings[0])
            
            unknown_face.save()
            
            return JsonResponse({
                'success': True,
                'unknown_face_id': unknown_face.id
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

def register_unknown_face(request, unknown_face_id):
    try:
        unknown_face = UnknownFace.objects.get(id=unknown_face_id)
        if request.method == 'POST':
            form = FaceForm(request.POST)
            if form.is_valid():
                new_face = form.save(commit=False)
                new_face.image = unknown_face.image
                if unknown_face.encoding:
                    new_face.encoding = unknown_face.encoding
                new_face.save()
                unknown_face.processed = True
                unknown_face.save()
                messages.success(request, "Nouveau visage enregistré avec succès!")
                return redirect('realtime_detection')
        else:
            form = FaceForm()
        
        return render(request, 'facial_app/register_unknown.html', {
            'form': form,
            'unknown_face': unknown_face
        })
    except UnknownFace.DoesNotExist:
        messages.error(request, "Visage inconnu non trouvé.")
        return redirect('realtime_detection')
