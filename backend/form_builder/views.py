from django.db.transaction import atomic
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.serializers import ValidationError
from rest_framework.response import Response
from .models import Form, Question, Business, Choices
from .serializers import FormSerializer, ChoiceSerializer, FormRUDSerializer
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

        return Response(form_data)

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

            return Response({
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

    def retrieve(self, request, *args, **kwargs):
        form = self.get_object()
        form_data = FormSerializer(form).data

        for question in form_data['questions']:
            if not question['choices']:
                question.pop('choices')

        return Response({**form_data, "slug": form.slug, "is_closed": form.is_closed})


