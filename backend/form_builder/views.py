import json, os, mimetypes
from django.db.transaction import atomic
from django.http import HttpResponse
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, GenericAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from rest_framework.serializers import ValidationError
from rest_framework.response import Response as API_Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from wsgiref.util import FileWrapper
from .models import Form, Question, Business, Choices, Response
from .serializers import FormSerializer, FormRUDSerializer, ResponseSerializer, DownloadSerializer
from .permissions import IsFormOwnerOrReadonly, IsFormOwner
from .utils import JSONConvertor


class FormListAPI(ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FormSerializer

    def get_queryset(self):
        order_by = self.request.GET.get('order_by') or 'created_date'  # default: created_date
        return Form.objects.filter(business__user=self.request.user).order_by(order_by)

    def __view_data(self, form_id):
        form = self.get_queryset().get(id=form_id)
        form_data = FormSerializer(form).data

        for question in form_data['questions']:
            if not question['choices']:
                question.pop('choices')

        return {"id": form.id, **form_data, "slug": form.slug, "is_closed": form.is_closed}

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
            try:
                business_id = Business.objects.get(user=request.user)
                questions = serializer.validated_data.pop('questions')
                form = Form(**serializer.validated_data, business_id=business_id)
                form.save()
            except Exception as error:
                error = list(error)[0]
                error_type, error_message = error[0], error[1][0]
                return API_Response({error_type: error_message})

            for question in questions:
                choices = None

                try:
                    if question['answer_type'] == 'multi':
                        choices = question.pop('choices')

                    elif question.get('choices') is not None:
                        raise ValidationError({'error': 'non multi questions do not contain choices'})

                    created_question = Question.objects.create(**question, form_id=form.id)

                    if choices:
                        for choice in choices:
                            Choices.objects.create(title=choice['title'], related_question=created_question)
                except Exception as error:
                    raise error

            return API_Response(self.__view_data(form.id))

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


class ResponseOfAFormAPIView(GenericAPIView):
    permission_classes = (AllowAny,)
    lookup_field = 'slug'

    def get_serializer_class(self):
        return ResponseSerializer

    def get_queryset(self):
        return Response.objects.all()

    def get(self, request, slug):
        related_form = Form.objects.get(slug__exact=slug)
        responses = self.get_queryset().filter(related_form_id=related_form.id)
        responses_list = []

        if request.user.is_authenticated and (related_form.business.user == request.user):
            for response in responses:
                responses_list.append({
                    "related_form": response.related_form.id,
                    "owner_email": response.owner_email,
                    "all_answers": response.all_answers
                })
            return API_Response(responses_list)
        return API_Response({"details": "permission denied"})

    def post(self, request, slug):
        related_form = Form.objects.get(slug__exact=slug)
        try:
            serializer = ResponseSerializer(data={**request.data, "related_form": related_form.pk})
            if serializer.is_valid(raise_exception=True):
                instance = serializer.save()
                return API_Response({
                    "id": instance.id,
                    "related_form": instance.related_form.id,
                    "owner_email": instance.owner_email,
                    "all_answers": instance.all_answers
                })

        except Exception as error:
            raise error


class DownloadAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    lookup_field = 'slug'
    serializer_class = DownloadSerializer

    def get_queryset(self):
        return Form.objects.filter(business__user=self.request.user)

    def post(self, request, slug):
        try:
            form = self.get_queryset().get(slug__exact=slug)
        except Exception as err:
            return API_Response({'error': f'this user({request.user}) does not have a form with this slug({slug}).'}, status=404)

        result = []
        export_to = request.data.get("format") or "excel"

        for response in form.responses.values():
            answers = Response.objects.get(id=response['id']).all_answers.values()
            answers_dict = {answer['question']: answer['answer'] for answer in answers}
            result.append({**response, **answers_dict})

        try:
            if export_to == "excel":
                file_name = JSONConvertor.convert(
                    json_input=json.dumps(result, indent=4, sort_keys=True, default=str),
                    saving_name=f'{form.slug}.xlsx',
                    export_to=export_to
                )

            elif export_to in ('csv', 'json', 'html'):
                file_name = JSONConvertor.convert(
                    json_input=json.dumps(result, indent=4, sort_keys=True, default=str),
                    saving_name=f'{form.slug}.{export_to}',
                    export_to=export_to
                )

            else:
                raise ValidationError(
                    'the <export_to> format is not supported. Supported formats = [csv, json, html, excel]')

        except Exception as error:
            return API_Response(error.args)

        else:
            file_handle = open(file_name, 'rb')
            mimetype, _ = mimetypes.guess_type(file_name)
            file_response = HttpResponse(FileWrapper(file_handle), content_type=mimetype)
            file_response['Content-Disposition'] = u'attachment; filename="%s"' % file_name
            return file_response
