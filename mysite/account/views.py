from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login,logout
from django.contrib.auth.decorators import login_required

def registration(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save() 
            login(request, user)
            return redirect('home_page')
    else:
        form = UserCreationForm()
    return render(request, 'account/create_user.html', {'form': form})


def home_page(request):
    if request.user.is_authenticated:
        return render(request, 'account/home_page.html')
    return render(request, 'account/main_page.html')

def sign_in(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user() 
            login(request, user)
            return redirect('home_page')
    else:
        form = AuthenticationForm()
    return render(request, 'account/sign_in.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('home_page')



