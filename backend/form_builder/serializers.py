from abc import ABC

from rest_framework import serializers
from .models import *
from django.db.transaction import atomic


class FormSerializer(serializers.ModelSerializer):
    class QuestionSerializer(serializers.ModelSerializer):
        class ChoiceSerializer(serializers.ModelSerializer):
            class Meta:
                model = Choices
                fields = '__all__'

        choices = ChoiceSerializer(many=True, required=False)

        class Meta:
            model = Question
            exclude = ['form']

    questions = QuestionSerializer(many=True)

    class Meta:
        model = Form
        fields = ['title', 'description', 'form_template', 'questions', 'owner_is_anonymous', 'created_date']


class FormRUDSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=128, required=False)
    description = serializers.CharField(required=False)
    is_closed = serializers.BooleanField(required=False)
    form_template = serializers.CharField(required=False)

    class QuestionRUDSerializer(serializers.ModelSerializer):
        class ChoiceRUDSerializer(serializers.ModelSerializer):
            delete_tag = serializers.BooleanField(required=False)

            class Meta:
                model = Choices
                fields = '__all__'

        choices = ChoiceRUDSerializer(many=True, required=False)
        q_id = serializers.IntegerField(required=False)

        class Meta:
            model = Question
            exclude = ['form']

        def update(self, instance: Question, validated_data):
            if instance.answer_type == 'multi':
                choices = validated_data.pop('choices')
                if choices is not None:
                    for choice in choices:
                        try:
                            delete_tag = choice.pop('delete_tag')
                        except:
                            raise serializers.ValidationError({'error': 'delete_tag is required'})

                        choice['related_question'] = choice['related_question'].pk
                        if delete_tag:
                            instance.choices.get(title__exact=choice['title']).delete()

                        else:
                            new_choice = self.ChoiceRUDSerializer(data=choice)
                            try:
                                if new_choice.is_valid(raise_exception=True):
                                    new_choice.save()
                            except Exception as error:
                                raise serializers.ValidationError({"error": error})
                            return super().update(instance, validated_data)

    questions = QuestionRUDSerializer(many=True, required=False)

    class Meta:
        model = Form
        fields = ['title', 'description', 'form_template', 'is_closed', 'questions', 'owner_is_anonymous']

    def update(self, instance: Form, validated_data):
        if 'questions' in validated_data:
            questions = validated_data.pop('questions')
            for question in questions:
                if not 'q_id' in question:
                    # create a new question and save it
                    instance.add_question(question)
                else:
                    # change the question
                    question_id = question.pop('q_id')
                    changing_question = instance.questions.get(id=question_id)
                    changing_question.change(**question)
        return super().update(instance, validated_data)


class ResponseSerializer(serializers.ModelSerializer):
    class AnswerSerializer(serializers.Serializer):
        related_question = serializers.IntegerField(required=True)
        answer_field = serializers.CharField(max_length=1024, required=False)
        answer_file = serializers.FileField(required=False)

    all_answers = AnswerSerializer(many=True)

    class Meta:
        model = Response
        fields = ('related_form', 'owner_email', 'all_answers')

    def validate(self, attrs):
        try:
            related_form: Form = attrs['related_form']
            required_questions = related_form.required_questions
            answered_question = attrs['all_answers']
            answered_question_ids = [answer['related_question'] for answer in answered_question]
            if all([question_id in answered_question_ids for question_id in
                    required_questions.values_list('id', flat=True)]):
                return attrs
            else:
                raise serializers.ValidationError('some required questions has not been answered in this response')
        except Exception as error:
            raise serializers.ValidationError(error)

    @atomic
    def save(self, **kwargs):
        """
        save method has been defined atomic, to avoid saving responses that do not contain valid answers.
        and in case an answers creation process raises an exception, the response and other answers do not create as well.
        """

        if self.is_valid(raise_exception=True):
            data = self.validated_data
            answers = data.pop('all_answers')
            related_response = Response.objects.create(**data)

            for answer in answers:
                try:
                    related_question = Question.objects.get(id=int(answer['related_question']))
                    if related_question.answer_type == QuestionTypes.MultipleChoice:
                        # in multi choice answers, the answer field has to be the choice id
                        if related_question.choices.filter(id=int(answer['answer_field'])):
                            MultipleChoiceAnswer.objects.create(related_response=related_response,
                                                                related_question=related_question,
                                                                answer_field_id=int(answer['answer_field']))
                        else:
                            raise ValidationError("selected choice does not exist in the specific question choices")

                    elif related_question.answer_type == QuestionTypes.Short:
                        ShortAnswer.objects.create(related_response=related_response,
                                                   related_question=related_question,
                                                   answer_field=answer['answer_field'])
                    elif related_question.answer_type == QuestionTypes.Long:
                        LongAnswer.objects.create(related_response=related_response,
                                                  related_question=related_question,
                                                  answer_field=answer['answer_field'])
                    elif related_question.answer_type == QuestionTypes.Email:
                        EmailFieldAnswer.objects.create(related_response=related_response,
                                                        related_question=related_question,
                                                        answer_field=answer['answer_field'])
                    elif related_question.answer_type == QuestionTypes.Number:
                        NumberFieldAnswer.objects.create(related_response=related_response,
                                                         related_question=related_question,
                                                         answer_field=int(answer['answer_field']))
                    elif related_question.answer_type == QuestionTypes.Phone_Number:
                        PhoneNumberFieldAnswer.objects.create(related_response=related_response,
                                                              related_question=related_question,
                                                              answer_field=answer['answer_field'])
                    elif related_question.answer_type == QuestionTypes.File:
                        FileFieldAnswer.objects.create(related_response=related_response,
                                                       related_question=related_question,
                                                       answer_field=answer['answer_file'])
                    else:
                        raise serializers.ValidationError("wrong question type. check the typo.")

                except Exception as err:
                    raise serializers.ValidationError({"error": f"{err} is required"})
            return related_response


class DownloadSerializer(serializers.Serializer):
    format = serializers.CharField(max_length=32)
