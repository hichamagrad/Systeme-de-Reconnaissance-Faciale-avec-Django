from django.db import models
from django.utils import timezone
import numpy as np
import json

class Face(models.Model):
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100, default='')
    identifier = models.CharField(max_length=100, unique=True, default='')
    email = models.EmailField(blank=True, null=True)
    image = models.ImageField(upload_to='faces/')
    encoding = models.TextField(blank=True, null=True)  # Encodage facial en JSON
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def save_encoding(self, encoding_array):
        self.encoding = json.dumps(encoding_array.tolist())
        self.save()

    def get_encoding(self):
        if self.encoding:
            return np.array(json.loads(self.encoding))
        return None

    def __str__(self):
        return f"{self.name} {self.surname}"

class UnknownFace(models.Model):
    image = models.ImageField(upload_to='unknown_faces/')
    detected_at = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)
    encoding = models.TextField(blank=True, null=True)

    def save_encoding(self, encoding_array):
        self.encoding = json.dumps(encoding_array.tolist())
        self.save()

    def get_encoding(self):
        if self.encoding:
            return np.array(json.loads(self.encoding))
        return None

    def __str__(self):
        return f"Unknown Face detected at {self.detected_at}"
