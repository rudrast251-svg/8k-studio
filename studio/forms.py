from django import forms


class UploadJobForm(forms.Form):
    file = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'field-file'}))
    library_asset_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    instruction = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'field-input field-textarea',
            'rows': 3,
            'placeholder': 'e.g. "Make this video 8K, cinematic, brighter, and smoother."',
        }),
        max_length=600,
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('file') and not cleaned.get('library_asset_id'):
            raise forms.ValidationError('Upload a file or choose one from your asset library.')
        return cleaned
