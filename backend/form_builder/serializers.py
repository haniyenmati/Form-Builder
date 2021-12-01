from rest_framework import serializers
from .models import Form, Question, Choices, Response


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choices
        fields = '__all__'


class FormSerializer(serializers.ModelSerializer):
    class QuestionSerializer(serializers.ModelSerializer):
        choices = ChoiceSerializer(many=True, required=False)

        class Meta:
            model = Question
            exclude = ['form']

    questions = QuestionSerializer(many=True)

    class Meta:
        model = Form
        fields = ['title', 'description', 'form_template', 'questions', 'owner_is_anonymous']


class FormRUDSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=128, required=False)
    description = serializers.CharField(required=False)
    is_closed = serializers.BooleanField(required=False)
    form_template = serializers.CharField(required=False)
    questions = FormSerializer.QuestionSerializer(many=True, required=False)

    class Meta:
        model = Form
        fields = ['title', 'description', 'form_template', 'is_closed', 'questions']

    def update(self, instance, validated_data):
        if 'questions' in validated_data:
            questions = validated_data.pop('questions')
            for question in questions:
                Question.objects.create(form=instance, **question)
        return super().update(instance, validated_data)


class ResponseSerializer(serializers.ModelSerializer):
    pass
