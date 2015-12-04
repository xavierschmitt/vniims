from django import forms


class NamePIDForm(forms.Form):
    name = forms.CharField(label='Name', required=False)
    pid = forms.CharField(label='PID', required=False)
    

class DateForm(forms.Form):
    date = forms.DateField(label='Date', input_formats=['%Y-%m-%d'], widget=forms.DateInput(attrs={'placeholder': 'yyyy-mm-dd'}), required=False)
    role = forms.CharField(label='Role', required=False)