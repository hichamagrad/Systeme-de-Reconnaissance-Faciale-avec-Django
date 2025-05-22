from django import forms
from .models import Face, UnknownFace

class FaceForm(forms.ModelForm):
    class Meta:
        model = Face
        fields = ['name', 'surname', 'identifier', 'email', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'identifier': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre l'image optionnelle pour permettre l'enregistrement d'un visage déjà capturé
        self.fields['image'].required = False

class IdentifyForm(forms.Form):
    image = forms.ImageField(label='Image à identifier')

class UnknownFaceForm(forms.ModelForm):
    class Meta:
        model = UnknownFace
        fields = ['image']
        widgets = {
            'image': forms.HiddenInput()
        }
