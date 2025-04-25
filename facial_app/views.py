from django.shortcuts import render, redirect
from .forms import FaceForm, IdentifyForm
from .models import Face
import face_recognition
from django.contrib import messages
import os
from django.conf import settings

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
                messages.error(request, "Aucun visage détecté dans l’image.")

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
