from django.db import models, IntegrityError
from django.utils.text import slugify
from django.db.models import F
from django.core.validators import ValidationError
from accounts.models import Business
from .utils import PhoneNumberValidator, QuestionTypes


class Form(models.Model):
    """
        a db table includes a business as foreignkey and some other details.
        title: [unique for other forms which belong to a business] a title.
        description: [not nullable] the form description, nothing much.
        business : [foreignkey] the form owner.
        slug : [unique, auto-generated] is being used for lookup_field to view each form and is auto generated.
        form_template: [restricted with defined choices] for specifying a form template and visuals.
        created_date: [auto-generated] is being set, whenever a form instance is created.
        owner_is_anonymous: [boolean] if true whoever fills this form, can do it anonymously; otherwise has to enter
        their email.
        is_closed: [boolean, default=false] if a form is closed, it will not accept any responses.
    """

    class FormTemplates(models.TextChoices):
        """
            a class for choosing form template from a set of defined templates.
        """
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

    def add_question(self, question):
        try:
            self.questions.add(question)
        except Exception as err:
            raise ValidationError({"error": f'{err}'})
        else:
            return self.questions.all()

    def save(self, *args, **kwargs):
        """
            auto generating slug.
            if the generated slug is not unique, it means there exists a form with title in the related business forms.
            so it raise exception.
        """
        try:
            self.slug = slugify(f'{self.business.pk}-{self.title}')
            return super().save(*args, **kwargs)
        except IntegrityError:
            raise ValidationError({"error": "a form with this title already exists in your forms list."})

    def __str__(self):
        return self.slug


class Question(models.Model):
    """
        a db table includes a form as foreignkey and some other details.
        answer_type: [restricted with defined choices] there are some defined types as QuestionTypes.
        form: [foreignkey] each question belongs to a form.
        question_body: the question text.
        related_image: [nullable] each question can have a attached image.
    """
    answer_type = models.CharField(max_length=20, choices=QuestionTypes.choices)
    is_required = models.BooleanField(default=False)
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='questions')
    question_body = models.CharField(max_length=256)
    related_image = models.ImageField(null=True, blank=True, upload_to='media/question_related_images')

    def __str__(self):
        return self.question_body

    @property
    def multi_choices_with_choices(self):
        """
            displays multi choice questions with their choices.
        """
        if self.answer_type == QuestionTypes.MultipleChoice:
            return self.objects.values(self.choices, question=F('question_body'))
        raise ValidationError({'error': 'non multi choice questions does not have this option'})


class Response(models.Model):
    related_form = models.ForeignKey(Form, on_delete=models.SET('deleted-form'), related_name='responses')
    owner_email = models.EmailField(null=True)

    @property
    def all_answers(self):
        longs = self.long_answers.values(question_id=F('related_question_id'),
                                         question=F('related_question__question_body'),
                                         answer_type=F('related_question__answer_type'),
                                         answer=F('answer_field'))
        shorts = self.short_answers.values(question_id=F('related_question_id'),
                                           question=F('related_question__question_body'),
                                           answer_type=F('related_question__answer_type'),
                                           answer=F('answer_field'))
        multi_choices = self.multichoice_answers.values(question_id=F('related_question_id'),
                                                        question=F('related_question__question_body'),
                                                        answer_type=F('related_question__answer_type'),
                                                        answer=F('answer_field__title'))
        emails = self.email_answers.values(question_id=F('related_question_id'),
                                           question=F('related_question__question_body'),
                                           answer_type=F('related_question__answer_type'),
                                           answer=F('answer_field'))
        phone_nums = self.phonenum_answers.values(question_id=F('related_question_id'),
                                                  question=F('related_question__question_body'),
                                                  answer_type=F('related_question__answer_type'),
                                                  answer=F('answer_field'))
        nums = self.number_answers.values(question_id=F('related_question_id'),
                                          question=F('related_question__question_body'),
                                          answer_type=F('related_question__answer_type'),
                                          answer=F('answer_field'))
        files = self.file_answers.values(question_id=F('related_question_id'),
                                         question=F('related_question__question_body'),
                                         answer_type=F('related_question__answer_type'),
                                         answer=F('answer_field'))
        return longs.union(shorts, multi_choices, emails, phone_nums, nums, files)

    @property
    def all_answered_questions_body(self):
        return self.all_answers.values_list('question', flat=True)

    def save(self, *args, **kwargs):
        if (not self.related_form.owner_is_anonymous) and (self.owner_email is None):
            raise ValidationError({'error': 'form is not accepting anonymous owner. email required'})
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.owner_email


class Answer(models.Model):

    def save(self, *args, **kwargs):
        if self.related_question.is_required and (self.answer_field is None):
            raise ValidationError({'error': 'answer is required'})
        return super().save(*args, **kwargs)

    def is_valid(self):
        if self.related_question.id in self.related_response.all_answered_questions_body:
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
                raise ValidationError(
                    {'error': f'answer type has to be {self.related_question.answer_type}, but Long Answer was given!'})
            return super().save(*args, **kwargs)
        raise ValidationError({'error': 'this question has been answered before in this response.'})

    def __str__(self):
        return self.answer_field


class ShortAnswer(Answer):
    related_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='short_answers')
    related_response = models.ForeignKey(Response, on_delete=models.CASCADE, related_name='short_answers')
    answer_field = models.CharField(max_length=256, null=True)

    def save(self, *args, **kwargs):
        if self.is_valid():
            if self.related_question.answer_type != QuestionTypes.Short:
                raise ValidationError(
                    {'error': f'answer type has to be {self.related_question.answer_type}, but Short Answer was given!'})
            return super().save(*args, **kwargs)
        raise ValidationError({'error': 'this question has been answered before in this response.'})

    def __str__(self):
        return f'{self.answer_field}'


class Choices(models.Model):
    title = models.CharField(max_length=128)
    related_question = models.ForeignKey(Question,
                                         on_delete=models.CASCADE,
                                         related_name='choices', null=True)

    def save(self, *args, **kwargs):
        if self.related_question.answer_type != QuestionTypes.MultipleChoice:
            raise ValidationError(
                {'error': f'related question has to be multiple choice but {self.related_question.answer_type} were given'})
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
                raise ValidationError({'error': 'selected choice is not related to this question'})

            if self.related_question.answer_type != QuestionTypes.MultipleChoice:
                raise ValidationError(
                    {'error': f'answer type has to be {self.related_question.answer_type}, but Multiple Choice was given!'})
            return super().save(*args, **kwargs)
        raise ValidationError({'error': 'this question has been answered before in this response.'})

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
                raise ValidationError(f'answer type has to be {self.related_question.answer_type}, but Email was given!')
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
                raise ValidationError(
                    f'answer type has to be {self.related_question.answer_type}, but Phone Number was given!')
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
                raise ValidationError(f'answer type has to be {self.related_question.answer_type}, but Number was given!')
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
                raise ValidationError(f'answer type has to be {self.related_question.answer_type}, but File was given!')
            return super().save(*args, **kwargs)
        raise ValidationError('this question has been answered before in this response.')

    def __str__(self):
        return self.answer_field.name
