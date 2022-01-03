from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from django.db.transaction import atomic
from .models import Business, User
from .serializers import BusinessSerializer


class RegisterAPIView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = BusinessSerializer

    def get_queryset(self):
        return Business.objects.all()

    @atomic
    def post(self, request):
        serializer = BusinessSerializer(data=request.data)
        if serializer.is_valid():
            user_data = serializer.validated_data['user']
            new_user = User.objects.create_user(username=user_data['username'],
                                                password=user_data['password'],
                                                email=user_data['email'])

            new_business = Business(user=new_user, label=serializer.validated_data['label'], slug=' ')
            new_business.save()

        else:
            raise ValidationError({"error": serializer.errors})

        return Response(data={
            'pk': new_business.pk,
            'user': new_user.username,
            'label': new_business.label,
            'registeration_date': new_business.registeration_date
        })


class LogoutAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated, )

    def post(self, request):
        request.user.auth_token.delete()
        return Response(data={'message': f"Bye {request.user.username}!"})
