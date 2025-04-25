from django import forms
from .models import Face

class FaceForm(forms.ModelForm):
    class Meta:
        model = Face
        fields = ['name', 'image']
class IdentifyForm(forms.Form):
    image = forms.ImageField(label='Image à identifier')
