from django.db import models
import numpy as np
import json

class Face(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='faces/')
    encoding = models.TextField(blank=True, null=True)  # Encodage facial en JSON

    def save_encoding(self, encoding_array):
        self.encoding = json.dumps(encoding_array.tolist())
        self.save()

    def get_encoding(self):
        if self.encoding:
            return np.array(json.loads(self.encoding))
        return None

    def __str__(self):
        return self.name
