from django.http import HttpResponse
from django.views import View


class Liveness(View):
    http_method_names = ["get"]

    def get(*args, **kwargs):
        return HttpResponse("ok")
