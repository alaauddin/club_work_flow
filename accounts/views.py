from django.shortcuts import render
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.models import User

# Create your views here.
class UserUpdateView(UpdateView):
    model=User
    fields =('first_name','last_name', 'email',)
    template_name = 'read/my_account.html'
    success_url = reverse_lazy('my_account')

    

    def get_object(self):
        return self.request.user
    
    