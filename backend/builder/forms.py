from django import forms


class TemplateUploadForm(forms.Form):
    name = forms.CharField(max_length=120, help_text="Shown to customers when choosing a template.")
    zip_file = forms.FileField(label="Template zip (static HTML + assets)")
