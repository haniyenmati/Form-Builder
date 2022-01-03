from django.core.validators import RegexValidator
from django.db.models import TextChoices
import pandas


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


class JSONConvertor:
    __exporting_files = "/home/haniye/Desktop/django-projects/Ayten/Form Builder Clone/Form-Builder/backend/media/exporting_files"

    @classmethod
    def convert(cls, json_input: str, saving_name, export_to):
        try:
            json_file = pandas.read_json(json_input)
            getattr(json_file, f'to_{export_to}')(f'{cls.__exporting_files}/{saving_name}')
        except Exception as err:
            raise ValueError({'error': f'converting failed due to {err} '})
        else:
            return f'{cls.__exporting_files}/{saving_name}'
