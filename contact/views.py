# contact/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext
from .forms import ContactForm

def contact_view(request):
    """
    Displays the contact form and handles form submission.
    """
    if request.method == 'POST':
        # If the form is submitted, bind the POST data to a form instance.
        form = ContactForm(request.POST)
        if form.is_valid():
            # If the data is valid, save it to the database.
            form.save()

            # Create a success message.
            success_message = gettext("Thank you for your message! We will get back to you shortly.")
            messages.success(request, success_message)

            # Redirect to the same page to prevent form resubmission (Post/Redirect/Get pattern).
            return redirect(reverse('contact:contact_form') + '#contact-form')
    else:
        # If it's a GET request, create a blank form instance.
        form = ContactForm()

    return render(request, 'contact/contact_form.html', {'form': form})

# Create your views here.
