from django.shortcuts import render

def hello(request):
    context = {'name': 'Rishika'}
    return render(request, 'welcome.html', context)
