from django.core.validators import RegexValidator
from django.db.models import TextChoices


class PhoneNumberValidator:
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                 message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")


class QuestionTypes(TextChoices):
    Long = 'long', "Long"
    Short = 'short', "Short"
    MultipleChoice = 'multi', "MultipleChoice"
    Email = 'email', "Email"
    Phone_Number = 'phone-no', "Phone No."
    Number = 'number', "Number"
    File = 'file', "File"
