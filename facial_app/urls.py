from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

urlpatterns = [
    # Page racine redirige vers la détection en temps réel
    path('', RedirectView.as_view(url='realtime/', permanent=False), name='index'),
    
    path('register/', views.register_face, name='register_face'),
    path('identify/', views.identify_face, name='identify_face'),
    path('realtime/', views.realtime_detection, name='realtime_detection'),
    path('video_feed/', views.video_feed, name='video_feed'),
    path('process_unknown_face/', views.process_unknown_face, name='process_unknown_face'),
    path('register_unknown_face/<int:unknown_face_id>/', views.register_unknown_face, name='register_unknown_face'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
