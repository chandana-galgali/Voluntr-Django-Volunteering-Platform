class PrivateResponseMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        if getattr(request,'user',None) and request.user.is_authenticated or request.path.startswith(('/community/verify/','/community/google/','/reset/','/password-reset/','/login/','/join/','/admin/')):
            response['Cache-Control']='private, no-store'
            response['X-Robots-Tag']='noindex, nofollow'
        return response
