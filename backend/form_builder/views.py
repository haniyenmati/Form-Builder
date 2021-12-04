from django.db.transaction import atomic
from django.urls import reverse
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, GenericAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from rest_framework.serializers import ValidationError
from rest_framework.response import Response as API_Response
from .models import Form, Question, Business, Choices, Response
from .serializers import FormSerializer, FormRUDSerializer, ResponseSerializer
from .permissions import IsFormOwnerOrReadonly


class FormListAPI(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FormSerializer

    def get_queryset(self):
        order_by = self.request.GET.get('order_by') or 'created_date'  # default: created_date
        return Form.objects.filter(business__user=self.request.user).order_by(order_by)

    def list(self, request, *args, **kwargs):
        forms = self.get_queryset()
        form_data = FormSerializer(forms, many=True).data

        for form in form_data:
            for question in form['questions']:
                if not question['choices']:
                    question.pop('choices')
            form['slug'] = forms.get(title=form['title']).slug
            form['id'] = forms.get(slug=form['slug']).id

        return API_Response(form_data)

    @atomic
    def create(self, request, *args, **kwargs):
        serializer = FormSerializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            business_id = Business.objects.get(user=request.user)
            questions = serializer.validated_data.pop('questions')
            form = Form(**serializer.validated_data, business_id=business_id)
            form.save()

            for question in questions:
                choices = None

                if question['answer_type'] == 'multi':
                    choices = question.pop('choices')

                elif question.get('choices') is not None:
                    raise ValidationError({'error': 'non multi questions do not contain choices'})

                created_question = Question.objects.create(**question, form_id=form.id)

                if choices:
                    for choice in choices:
                        Choices.objects.create(title=choice['title'], related_question=created_question)

            return API_Response({
                "form": form.id,
                "title": form.title,
                "slug": form.slug,
                "description": form.description,
                "business": form.business.label,
                "created_date": form.created_date,
                "questions": questions,
            })

        raise ValidationError(f'form is not valid due to {serializer.errors}')


class FormRUDAPI(RetrieveUpdateDestroyAPIView):
    permission_classes = (IsFormOwnerOrReadonly,)
    serializer_class = FormRUDSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return Form.objects.all()

    def __view_data(self):
        form = self.get_object()
        form_data = FormSerializer(form).data

        for question in form_data['questions']:
            if not question['choices']:
                question.pop('choices')

        return {"id": form.id, **form_data, "slug": form.slug, "is_closed": form.is_closed}

    def retrieve(self, request, *args, **kwargs):
        return API_Response(self.__view_data())

    def put(self, request, *args, **kwargs):
        return API_Response({"detail": "Method \"PUT\" not allowed."})

    def patch(self, request, *args, **kwargs):
        super().patch(request, *args, **kwargs)
        return API_Response(self.__view_data())


class ResponseListAPI(ListCreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ResponseSerializer

    def get_queryset(self):
        return Response.objects.all()

    @atomic
    def create(self, request, *args, **kwargs):
        try:
            serializer = ResponseSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                instance = serializer.save()
                return API_Response({
                    "id": instance.id,
                    "related_form": instance.related_form.id,
                    "owner_email": instance.owner_email,
                    "all_answers": instance.all_answers
                })
        except Exception as error:
            return API_Response({f"detail": f"data is not valid due to -> {error}"})

    def list(self, request, *args, **kwargs):
        specific_form_id = request.GET.get('form') or None
        if request.user.is_authenticated:
            responses = self.get_queryset().filter(related_form__business__user=request.user)
            if specific_form_id:
                responses = responses.filter(related_form_id=specific_form_id)
            responses_list = []

            for response in responses:
                responses_list.append({
                    "related_form": response.related_form.id,
                    "owner_email": response.owner_email,
                    "all_answers": response.all_answers
                })
            return API_Response(responses_list)

        return API_Response({"details": "permission denied"})


class ResponseAPIView(GenericAPIView):
    serializer_class = ResponseSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Response.objects.all()

    def post(self, request, slug):
        related_form = Form.objects.get(slug__exact=slug)
        return reverse('form_builder:responses', kwargs={"related_form": related_form, **request.data})

    def get(self, request, slug):
        related_form = Form.objects.get(slug__exact=slug)
        return reverse('form_builder:responses', kwargs={"related_form": related_form, **request.data})
