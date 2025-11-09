from django.shortcuts import render

def hello(request):
    context = {'name': 'Rishika'}
    return render(request, 'main/hello.html', context)
