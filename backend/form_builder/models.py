from django.db import models
from django.utils.text import slugify
from django.db.models import F
from django.core.validators import ValidationError
from accounts.models import Business
from .utils import PhoneNumberValidator, QuestionTypes
from .baseClasses import AbstractBaseQuestion


class Form(models.Model):
    class FormTemplates(models.TextChoices):
        BLANK = 'blank', "BLANK"
        CV = 'cv', "CV"
        QUIZ = 'quiz', "QUIZ"
        REGISTRATION = 'registration', "REGISTRATION"

    title = models.CharField(max_length=128, default='Untitled Form')
    description = models.TextField()
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='forms')
    slug = models.SlugField(max_length=256, unique=True)
    form_template = models.CharField(max_length=16, choices=FormTemplates.choices, default=FormTemplates.BLANK)
    created_date = models.DateTimeField(auto_now_add=True)
    owner_is_anonymous = models.BooleanField(default=True)
    is_closed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.slug = slugify(f'{self.id}-{self.title}')
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.slug


class Question(AbstractBaseQuestion):
    answer_type = models.CharField(max_length=20, choices=QuestionTypes.choices)
    is_required = models.BooleanField(default=False)
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='questions')

    def is_valid(self):
        """
        TODO checks out if all with same types questions in the related form has unique question body.
        """

    @property
    def multi_choices_with_choices(self):
        if self.answer_type == QuestionTypes.MultipleChoice:
            return self.objects.values(self.choices, question=F('question_body'))
        raise TypeError('non multi choice questions does not have this option')

    def __str__(self):
        return self.question_body


class Response(models.Model):
    related_form = models.ForeignKey(Form, on_delete=models.SET('deleted-form'), related_name='responses')
    owner_email = models.EmailField(null=True)

    def is_valid(self):
        """ TODO checks out if all required questions are answered"""

    def save(self, *args, **kwargs):
        if (not self.related_form.owner_is_anonymous) and (self.owner_email is None):
            raise ValueError('form is not accepting anonymous owner. email required')
        return super().save(*args, **kwargs)

    @property
    def all_answers(self):
        longs = self.long_answers.values(question_id=F('related_question_id'), question=F('related_question__question_body'),
                                         answer_type=F('related_question__answer_type'),
                                         answer=F('answer_field'))
        shorts = self.short_answers.values(question_id=F('related_question_id'), question=F('related_question__question_body'),
                                         answer_type=F('related_question__answer_type'),
                                         answer=F('answer_field'))
        multi_choices = self.multichoice_answers.values(question_id=F('related_question_id'),question=F('related_question__question_body'),
                                                        answer_type=F('related_question__answer_type'),
                                                        answer=F('answer_field__title'))
        emails = self.email_answers.values(question_id=F('related_question_id'),question=F('related_question__question_body'),
                                           answer_type=F('related_question__answer_type'),
                                           answer=F('answer_field'))
        phone_nums = self.phonenum_answers.values(question_id=F('related_question_id'),question=F('related_question__question_body'),
                                                  answer_type=F('related_question__answer_type'),
                                                  answer=F('answer_field'))
        nums = self.number_answers.values(question_id=F('related_question_id'),question=F('related_question__question_body'),
                                          answer_type=F('related_question__answer_type'),
                                          answer=F('answer_field'))
        files = self.file_answers.values(question_id=F('related_question_id'),question=F('related_question__question_body'),
                                         answer_type=F('related_question__answer_type'),
                                         answer=F('answer_field'))
        return longs.union(shorts, multi_choices, emails, phone_nums, nums, files)

    @property
    def all_answered_questions_body(self):
        return self.all_answers.values_list('question', flat=True)

    def __str__(self):
        return self.owner_email


class Answer(models.Model):

    def save(self, *args, **kwargs):
        if self.related_question.is_required and (self.answer_field is None):
            raise ValueError('answer is required')
        return super().save(*args, **kwargs)

    def is_valid(self):
        if self.related_question.question_body in self.related_response.all_answered_questions_body:
            return False  # it has been answered before in this response
        return True

    class Meta:
        abstract = True


class LongAnswer(Answer):
    related_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='long_answers')
    related_response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='long_answers')
    answer_field = models.TextField(null=True)

    def save(self, *args, **kwargs):
        if self.is_valid():
            if self.related_question.answer_type != QuestionTypes.Long:
                raise ValueError(
                    f'answer type has to be {self.related_question.answer_type}, but Long Answer was given!')
            return super().save(*args, **kwargs)
        raise ValidationError('this question has been answered before in this response.')

    def __str__(self):
        return self.answer_field


class ShortAnswer(Answer):
    related_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='short_answers')
    related_response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='short_answers')
    answer_field = models.CharField(max_length=256, null=True)

    def save(self, *args, **kwargs):
        if self.is_valid():
            if self.related_question.answer_type != QuestionTypes.Short:
                raise ValueError(f'answer type has to be {self.related_question.answer_type}, but Short Answer was given!')
            return super().save(*args, **kwargs)
        raise ValidationError('this question has been answered before in this response.')

    def __str__(self):
        return self.answer_field


class Choices(models.Model):
    title = models.CharField(max_length=128)
    related_question = models.ForeignKey(Question,
                                         on_delete=models.CASCADE,
                                         related_name='choices', null=True)

    def save(self, *args, **kwargs):
        if self.related_question.answer_type != QuestionTypes.MultipleChoice:
            raise ValueError(
                f'related question has to be multiple choice but {self.related_question.answer_type} were given')
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class MultipleChoiceAnswer(Answer):
    related_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='multichoice_answers')
    related_response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='multichoice_answers')
    answer_field = models.ForeignKey(Choices, on_delete=models.CASCADE, related_name='related_answers')

    def save(self, *args, **kwargs):
        if self.is_valid():
            if not self.related_question.choices.filter(title__exact=self.answer_field).exists():
                raise ValueError('selected choice is not related to this question')

            if self.related_question.answer_type != QuestionTypes.MultipleChoice:
                raise ValueError(
                    f'answer type has to be {self.related_question.answer_type}, but Multiple Choice was given!')
            return super().save(*args, **kwargs)
        raise ValidationError('this question has been answered before in this response.')

    @property
    def amount_of_choices(self):
        return self.choices.count()

    def __str__(self):
        return self.answer_field.title


class EmailFieldAnswer(Answer):
    related_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='email_answers')
    related_response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='email_answers')
    answer_field = models.EmailField(null=True)

    def save(self, *args, **kwargs):
        if self.is_valid():
            if self.related_question.answer_type != QuestionTypes.Email:
                raise ValueError(f'answer type has to be {self.related_question.answer_type}, but Email was given!')
            return super().save(*args, **kwargs)
        raise ValidationError('this question has been answered before in this response.')

    def __str__(self):
        return self.answer_field


class PhoneNumberFieldAnswer(Answer):
    related_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='phonenum_answers')
    related_response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='phonenum_answers')
    answer_field = models.CharField(validators=[PhoneNumberValidator.phone_regex], max_length=17, null=True)

    def save(self, *args, **kwargs):
        if self.is_valid():
            if self.related_question.answer_type != QuestionTypes.Phone_Number:
                raise ValueError(f'answer type has to be {self.related_question.answer_type}, but Phone Number was given!')
            return super().save(*args, **kwargs)
        raise ValidationError('this question has been answered before in this response.')

    def __str__(self):
        return self.answer_field


class NumberFieldAnswer(Answer):
    related_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='number_answers')
    related_response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='number_answers')
    answer_field = models.BigIntegerField(null=True)

    def save(self, *args, **kwargs):
        if self.is_valid():
            if self.related_question.answer_type != QuestionTypes.Number:
                raise ValueError(f'answer type has to be {self.related_question.answer_type}, but Number was given!')
            return super().save(*args, **kwargs)
        raise ValidationError('this question has been answered before in this response.')

    def __str__(self):
        return f'{self.answer_field}'


class FileFieldAnswer(Answer):
    related_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='file_answers')
    related_response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='file_answers')
    answer_field = models.FileField(upload_to='media/file_field_question_answers')

    def save(self, *args, **kwargs):
        if self.is_valid():
            if self.related_question.answer_type != QuestionTypes.File:
                raise ValueError(f'answer type has to be {self.related_question.answer_type}, but File was given!')
            return super().save(*args, **kwargs)
        raise ValidationError('this question has been answered before in this response.')

    def __str__(self):
        return self.answer_field.name
