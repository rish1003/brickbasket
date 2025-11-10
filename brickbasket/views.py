from django.shortcuts import render

def hello(request):
    context = {'name': 'Ravleen'}
    return render(request, 'welcome.html', context)
