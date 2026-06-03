from django import forms
from django.utils.translation import gettext_lazy as _


class PostPointAllocationForm(forms.Form):
    points = forms.IntegerField(
        min_value=0,
        label=_("Points"),
    )

    def __init__(self, *args, max_points=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["points"].max_value = max_points
        self.fields["points"].widget = forms.Select(
            choices=[(value, value) for value in range(0, max_points + 1)],
            attrs={"class": "form-select form-select-sm"},
        )
