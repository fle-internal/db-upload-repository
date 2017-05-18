import string
from django import forms

class UploadFileForm(forms.Form):
    project = forms.CharField()
    file = forms.FileField()

    def clean_project(self):

        data = self.cleaned_data['project'].lower()

        data = "".join([c for c in data if c in (string.ascii_lowercase + string.digits)])

        return data